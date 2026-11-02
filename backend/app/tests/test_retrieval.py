from datetime import date

from app.services.retrieval import RetrievalService
from app.tests.conftest import BUS_TEXT, FEE_REVISED, FEE_TEXT, HOSTEL_TEXT, ingest


def svc(db, deps, th=0.4):
    return RetrievalService(db, deps.embedder, deps.vectors, th)


def test_score_semantics_identical_text_is_near_one_and_unrelated_is_low(db, deps):
    ingest(db, deps, [HOSTEL_TEXT], title="Hostel", department="Hostel")
    same = svc(db, deps).search(HOSTEL_TEXT)
    other = svc(db, deps).search("how to bake a chocolate cake")
    assert same.hits[0].score > 0.95 and abs(same.hits[0].distance - (1 - same.hits[0].score)) < 1e-9
    assert other.hits[0].score < 0.3
    assert same.metrics.metric == "cosine_similarity" and same.metrics.top_score > 0.95


def test_hits_carry_title_department_date_page_and_document_id(db, deps):
    r = ingest(db, deps, ["Intro page.", HOSTEL_TEXT], title="Hostel Rules", department="Hostel", source_date=date(2026, 7, 15))
    hit = svc(db, deps).search("what time does the hostel gate close")[0] if False else svc(db, deps).search("hostel gate closes at 9:30 PM").hits[0]
    assert (hit.title, hit.department, hit.source_date, hit.page_number, hit.document_id) == ("Hostel Rules", "Hostel", date(2026, 7, 15), 2, r.document_id)
    src = hit.to_source()
    assert src.page_number == 2 and src.source_date == date(2026, 7, 15)


def test_returns_at_most_top_five_sorted_by_score(db, deps):
    for i in range(8):
        ingest(db, deps, [f"Notice {i} about library timings and books {i} " * 3], title=f"N{i}")
    res = svc(db, deps).search("library timings and books")
    assert len(res.hits) <= 5 and [h.score for h in res.hits] == sorted((h.score for h in res.hits), reverse=True)


def test_department_filter(db, deps):
    ingest(db, deps, [HOSTEL_TEXT], title="Hostel", department="Hostel")
    ingest(db, deps, [BUS_TEXT], title="Bus", department="Transport")
    res = svc(db, deps).search("departs at 7:15 AM gate", department="Transport")
    assert res.hits and all(h.department == "Transport" for h in res.hits)


def test_adjacent_chunks_from_same_page_are_deduplicated(db, deps):
    long_text = " ".join(f"Rule {i}: students must follow hostel policy number {i} strictly." for i in range(120))
    ingest(db, deps, [long_text], title="Long")
    res = svc(db, deps).search("hostel policy number 5")
    keys = [(h.document_id, h.page_number, h.chunk_index) for h in res.hits]
    assert all(abs(a[2] - b[2]) > 1 for i, a in enumerate(keys) for b in keys[i + 1:] if a[:2] == b[:2])


def test_revised_circular_supersedes_the_old_one(db, deps):
    old = ingest(db, deps, [FEE_TEXT], title="Fee Circular", department="Accounts", source_date=date(2026, 8, 10))
    new = ingest(db, deps, [FEE_REVISED], title="Revised Fee Circular", department="Accounts", source_date=date(2026, 10, 12), supersedes_id=old.document_id)
    res = svc(db, deps).search("last date to pay the semester tuition fee")
    ids = [h.document_id for h in res.hits]
    assert ids[0] == new.document_id and old.document_id not in ids
    assert "replaces" in res.hits[0].superseded_note and "Fee Circular" in res.hits[0].superseded_note


def test_old_circular_is_replaced_even_when_only_it_matches_the_query(db, deps):
    old = ingest(db, deps, [FEE_TEXT + " Scholarship forms are due with the sanction letter."], title="Fee Circular", source_date=date(2026, 8, 10))
    new = ingest(db, deps, ["Revised notice. Completely different wording about extension."], title="Revised", source_date=date(2026, 10, 12), supersedes_id=old.document_id)
    res = svc(db, deps).search("scholarship sanction letter forms")
    assert res.hits and all(h.document_id == new.document_id for h in res.hits)


def test_unrelated_documents_do_not_get_supersession_notes(db, deps):
    ingest(db, deps, [BUS_TEXT], title="Bus")
    assert svc(db, deps).search("bus route R1").hits[0].superseded_note is None


def test_adequate_filters_by_threshold(db, deps):
    ingest(db, deps, [HOSTEL_TEXT])
    s = svc(db, deps, th=0.4)
    assert s.adequate(s.search(HOSTEL_TEXT)) and not s.adequate(s.search("quantum chromodynamics lecture"))


def test_empty_index_and_blank_query_are_safe(db, deps):
    assert svc(db, deps).search("anything").hits == []
    assert svc(db, deps).search("   ").hits == []
