"""Turn a Markdown research report into an A4 PDF next to it (headings, paragraphs, lists, tables, bold,
italics, inline code and links).

    .venv/bin/python research/md_to_pdf.py "reports/Regime filters and trailing exits.md"
"""
import html, os, re, sys
from pathlib import Path
import matplotlib
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, ListFlowable, ListItem

_F = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for _n, _f in [("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
               ("DV-BI", "DejaVuSans-BoldOblique.ttf"), ("DVM", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(_n, os.path.join(_F, _f)))
addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DV-B"); addMapping("DV", 0, 1, "DV-I"); addMapping("DV", 1, 1, "DV-BI")

ss = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontName="DV", fontSize=9.5, leading=13.5, spaceAfter=5)
CELL = ParagraphStyle("c", parent=BODY, fontSize=8, leading=10, spaceAfter=0)
HEAD = {1: ParagraphStyle("h1", parent=BODY, fontName="DV-B", fontSize=17, leading=21, spaceAfter=8),
        2: ParagraphStyle("h2", parent=BODY, fontName="DV-B", fontSize=13, leading=16, spaceBefore=10, spaceAfter=5),
        3: ParagraphStyle("h3", parent=BODY, fontName="DV-B", fontSize=11, leading=14, spaceBefore=7, spaceAfter=4)}


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r'<font name="DVM">\1</font>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#1f5fa8">\1</link>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    return s


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
    data = [[Paragraph(("<b>%s</b>" if i == 0 else "%s") % inline(c), CELL) for c in r] for i, r in enumerate(cells)]
    t = Table(data, repeatRows=1, colWidths=[(A4[0] - 36 * mm) / len(cells[0])] * len(cells[0]))
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def build(md_path):
    lines = Path(md_path).read_text().splitlines()
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append(Paragraph(inline(" ".join(para)), BODY)); para.clear()
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            flush(); i += 1; continue
        m = re.match(r"(#{1,4})\s+(.*)", ln)
        if m:
            flush(); out.append(Paragraph(inline(m.group(2)), HEAD[min(len(m.group(1)), 3)])); i += 1; continue
        if ln.lstrip().startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i]); i += 1
            out += [table(rows), Spacer(1, 6)]; continue
        m = re.match(r"\s*(?:[-*]|(\d+)\.)\s+(.*)", ln)
        if m:
            flush(); items, numbered = [], bool(m.group(1))
            while i < len(lines):
                mm_ = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", lines[i])
                if mm_:
                    items.append(mm_.group(1))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            out.append(ListFlowable([ListItem(Paragraph(inline(t), BODY)) for t in items],
                                    bulletType="1" if numbered else "bullet", leftIndent=14, bulletFontName="DV"))
            continue
        para.append(ln.strip().lstrip("> ")); i += 1
    flush()
    pdf = Path(md_path).with_suffix(".pdf")
    SimpleDocTemplate(str(pdf), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title=Path(md_path).stem).build(out)
    return pdf


if __name__ == "__main__":
    print(build(sys.argv[1]))
