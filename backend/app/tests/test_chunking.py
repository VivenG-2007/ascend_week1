from app.services.chunking import chunk_pages, estimate_tokens
from app.services.text_clean import clean_text


def test_short_page_is_one_chunk_with_page_number():
    out = chunk_pages([(3, "Last date is 15 September 2026. Fee Rs 12,500.")])
    assert len(out) == 1 and out[0].page_number == 3 and out[0].chunk_index == 0
    assert "15 September 2026" in out[0].content and "12,500" in out[0].content


def test_long_text_is_split_near_500_tokens_with_overlap():
    sentences = [f"Sentence number {i} says something about hostel rule {i}." for i in range(300)]
    out = chunk_pages([(1, " ".join(sentences))])
    assert len(out) > 2
    assert all(c.token_count <= 560 for c in out)
    assert [c.chunk_index for c in out] == list(range(len(out)))
    tail = out[0].content.split("\n")[-1]
    assert tail in out[1].content  # overlap carries the last sentence(s) forward


def test_chunks_never_cross_pages():
    out = chunk_pages([(1, "Alpha page one."), (2, "Beta page two.")])
    assert [(c.page_number, "Alpha" in c.content, "Beta" in c.content) for c in out] == [(1, True, False), (2, False, True)]


def test_telugu_text_is_chunked_and_estimated():
    text = "గ్రంథాలయం ఉదయం తొమ్మిది గంటలకు తెరుస్తారు. " * 80
    out = chunk_pages([(1, text)])
    assert len(out) >= 2 and estimate_tokens(text) > estimate_tokens("a" * len(text))


def test_oversize_sentence_is_hard_split():
    out = chunk_pages([(1, "word " * 3000)])
    assert len(out) > 1 and all(c.token_count <= 560 for c in out)


def test_clean_text_keeps_dates_amounts_names_and_lines():
    raw = "Dr.\u00a0Asha  Verma\r\n\r\n\r\n\r\nDate:   12/10/2026\x00\nFee: Rs. 12,500.00   due\u200b"
    cleaned = clean_text(raw)
    assert "Dr. Asha Verma" in cleaned and "12/10/2026" in cleaned and "Rs. 12,500.00 due" in cleaned
    assert "\n\n\n" not in cleaned and "\x00" not in cleaned
