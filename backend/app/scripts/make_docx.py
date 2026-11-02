import os
import zipfile
import html
import re

def build_docx(markdown_path: str, docx_output_path: str):
    with open(markdown_path, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()
    body_elements = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        
        # Clean markdown links [text](url) -> text (url)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", s)
        # Bold **text** -> text
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        # Inline code `text` -> text
        s = re.sub(r"`([^`]+)`", r"\1", s)
        escaped = html.escape(s)

        if s.startswith("# "):
            title = html.escape(s[2:].strip())
            body_elements.append(
                f'<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="003366"/></w:rPr>'
                f'<w:t>{title}</w:t></w:r></w:p>'
            )
        elif s.startswith("## "):
            h2 = html.escape(s[3:].strip())
            body_elements.append(
                f'<w:p><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="30"/><w:color w:val="006699"/></w:rPr>'
                f'<w:t>{h2}</w:t></w:r></w:p>'
            )
        elif s.startswith("### "):
            h3 = html.escape(s[4:].strip())
            body_elements.append(
                f'<w:p><w:pPr><w:spacing w:before="160" w:after="80"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:sz w:val="24"/><w:color w:val="333333"/></w:rPr>'
                f'<w:t>{h3}</w:t></w:r></w:p>'
            )
        elif s.startswith("- ") or s.startswith("* "):
            bullet = html.escape(s[2:].strip())
            body_elements.append(
                f'<w:p><w:pPr><w:ind w:left="360"/></w:pPr>'
                f'<w:r><w:t>• {bullet}</w:t></w:r></w:p>'
            )
        elif s.startswith("|") and s.endswith("|"):
            # Markdown table rows
            cols = [html.escape(c.strip()) for c in s.strip("|").split("|")]
            if any("---" in c for c in cols):
                continue
            row_text = " | ".join(cols)
            body_elements.append(
                f'<w:p><w:r><w:rPr><w:rFonts w:ascii="Consolas"/><w:sz w:val="18"/></w:rPr>'
                f'<w:t>{row_text}</w:t></w:r></w:p>'
            )
        else:
            body_elements.append(
                f'<w:p><w:r><w:t>{escaped}</w:t></w:r></w:p>'
            )

    body_xml = f'<w:body xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{"".join(body_elements)}</w:body>'

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        '</Types>'
    )

    package_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n'
        '</Relationships>'
    )

    os.makedirs(os.path.dirname(docx_output_path), exist_ok=True)
    with zipfile.ZipFile(docx_output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", package_rels)
        z.writestr("word/document.xml", body_xml)

    print(f"Created DOCX: {docx_output_path} ({os.path.getsize(docx_output_path)} bytes)")

if __name__ == "__main__":
    src_md = r"c:\Users\viven\Desktop\ascend_week1\README.md"
    dst_docx = r"c:\Users\viven\Desktop\ascend_week1\docs\CampusVoice_Complete_Documentation.docx"
    build_docx(src_md, dst_docx)
