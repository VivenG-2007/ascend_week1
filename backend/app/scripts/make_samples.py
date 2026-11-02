"""Generate the FICTIONAL sample circulars in data/sample_circulars/ (text PDFs, a scanned PDF, a scanned PNG,
and a Telugu PDF when a Telugu font is available).   python -m app.scripts.make_samples"""
from __future__ import annotations

import os
from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[3] / "data" / "sample_circulars"
BANNER = "SAMPLE DOCUMENT - FICTIONAL, FOR DEMONSTRATION ONLY"
TELUGU_FONTS = [os.environ.get("TELUGU_FONT_PATH", ""), "/usr/share/fonts/truetype/lohit-telugu/Lohit-Telugu.ttf",
                r"C:\Windows\Fonts\Nirmala.ttf", "/Library/Fonts/Arial Unicode.ttf"]

CIRCULARS = {
    "fee_circular_2026-08-10.pdf": ("Fee Payment Circular - Odd Semester 2026-27", "Date: 10 August 2026", [
        "To: All students and parents.",
        "The last date to pay the semester tuition fee is 15 September 2026.",
        "Fees can be paid on the college online portal or at the Accounts counter between 10:00 AM and 3:00 PM on working days.",
        "A late fee of Rs 100 per day applies after the last date.",
        "Scholarship students must submit their scholarship sanction letter to the Accounts section before the last date.",
        "Fee receipts are issued on the same day. Keep the receipt safe."]),
    "fee_circular_revised_2026-10-12.pdf": ("Revised Fee Payment Circular - Odd Semester 2026-27", "Date: 12 October 2026", [
        "This circular replaces the Fee Payment Circular dated 10 August 2026.",
        "The last date to pay the semester tuition fee is now extended to 10 November 2026.",
        "A late fee of Rs 200 per day applies after 10 November 2026.",
        "All other payment instructions in the earlier circular remain the same.",
        "Queries may be sent to the Accounts section."]),
    "exam_circular_2026-09-20.pdf": ("Mid-Term 1 Examination Circular", "Date: 20 September 2026", [
        "Mid-Term 1 examinations begin on 16 November 2026 and end on 20 November 2026.",
        "Hall tickets will be available on the student portal from 10 November 2026.",
        "Students must carry their college ID card to the examination hall.",
        "Students need at least 75 percent attendance to be eligible for the examinations.",
        "Mobile phones are not allowed inside the examination hall.",
        "The detailed timetable is displayed on the Exam Cell notice board."]),
    "hostel_rules_2026-07-15.pdf": ("Hostel Rules and Timings", "Date: 15 July 2026", [
        "The hostel gate closes at 9:30 PM every day. Late entry needs written permission from the warden.",
        "Visitors are allowed only in the visitors lobby between 4:00 PM and 6:00 PM on Sundays.",
        "Mess timings: breakfast 7:30 AM to 9:00 AM, lunch 12:30 PM to 2:00 PM, dinner 7:30 PM to 9:00 PM.",
        "Electric heaters, induction stoves and other heavy appliances are not allowed in rooms.",
        "Students must keep rooms clean. Room inspection happens every month.",
        "Complaints can be given to the hostel warden office on the ground floor."]),
}
BUS_IMAGE = ("Bus Routes 2026-27", "Date: 20 July 2026", [
    "Route R1: North Gate, Lakeview, Market Square. Departs 7:15 AM.",
    "Route R2: Station Road, Green Park, Tech Park. Departs 7:30 AM.",
    "Route R3: Old Town, River Bridge, Hill Circle. Departs 7:00 AM.",
    "Evening buses leave the college at 4:45 PM and 5:30 PM.",
    "Bus pass can be collected from the Transport office."])
HOLIDAYS_SCAN = ("Holiday List 2026-27", "Date: 1 August 2026", [
    "2 October 2026: Gandhi Jayanti, holiday.",
    "8 November 2026 to 9 November 2026: festival break, holiday.",
    "25 December 2026: Christmas, holiday.",
    "26 January 2027: Republic Day, holiday.",
    "Classes resume on the next working day after every holiday."])
TELUGU_LIBRARY = ("గ్రంథాలయ సమయాలు", "తేదీ: 5 సెప్టెంబర్ 2026", [
    "గ్రంథాలయం సోమవారం నుండి శనివారం వరకు ఉదయం 9 గంటల నుండి సాయంత్రం 6 గంటల వరకు తెరిచి ఉంటుంది.",
    "ఆదివారం గ్రంథాలయం మూసివేయబడుతుంది.",
    "విద్యార్థులు ఒకేసారి గరిష్టంగా మూడు పుస్తకాలను 14 రోజుల వరకు తీసుకోవచ్చు.",
    "ఆలస్యంగా తిరిగి ఇస్తే రోజుకు ఒక రూపాయి జరిమానా విధించబడుతుంది."])


def _write_page(page: pymupdf.Page, title: str, date_line: str, lines: list[str], font: str | None = None) -> None:
    kw = {"fontname": "tel", "fontfile": font} if font else {"fontname": "helv"}
    if font:
        page.insert_font(fontname="tel", fontfile=font)
    page.insert_text((50, 60), BANNER if not font else "SAMPLE - FICTIONAL", fontsize=8, **{**kw, "fontname": kw["fontname"]})
    page.insert_text((50, 100), title, fontsize=18, **kw)
    page.insert_text((50, 130), date_line, fontsize=12, **kw)
    y = 170
    for ln in lines:
        rect = pymupdf.Rect(50, y, 545, y + 60)
        page.insert_textbox(rect, ln, fontsize=13, **kw)
        y += 52 if len(ln) > 90 else 34


def _pdf(path: Path, title, date_line, lines, font=None) -> None:
    doc = pymupdf.open()
    _write_page(doc.new_page(), title, date_line, lines, font)
    doc.save(path)


def _png_from(title, date_line, lines) -> bytes:
    doc = pymupdf.open()
    _write_page(doc.new_page(), title, date_line, lines)
    return doc[0].get_pixmap(dpi=200).tobytes("png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (title, d, lines) in CIRCULARS.items():
        _pdf(OUT / name, title, d, lines)
    (OUT / "scanned_bus_routes_2026-07-20.png").write_bytes(_png_from(*BUS_IMAGE))
    png = _png_from(*HOLIDAYS_SCAN)  # image-only PDF: no text layer, forces the OCR path
    scan = pymupdf.open()
    page = scan.new_page()
    page.insert_image(page.rect, stream=png)
    scan.save(OUT / "scanned_holiday_list_2026-08-01.pdf")
    font = next((f for f in TELUGU_FONTS if f and Path(f).exists()), None)
    if font:
        _pdf(OUT / "library_timings_telugu_2026-09-05.pdf", *TELUGU_LIBRARY, font=font)
    else:
        print("No Telugu font found; skipped the Telugu sample. Set TELUGU_FONT_PATH to a .ttf file.")
    print("Wrote", len(list(OUT.iterdir())), "files to", OUT)


if __name__ == "__main__":
    main()
