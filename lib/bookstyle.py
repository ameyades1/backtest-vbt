"""Shared 'textbook' look for the reader-facing notes (concepts book, trading guide, sizing note):
12 pt serif body, large sans headings, amber accents, coloured call-out boxes, page header rule and page numbers.

    from lib import bookstyle as bs
    story = [bs.title("Name", "subtitle"), bs.Paragraph("text", bs.P), bs.box("rule", "..."), bs.table(rows, widths)]
    bs.build(path, story, "Running title")
"""
import os
import matplotlib
from . import pdffont  # noqa: F401  (Helvetica -> DejaVu Sans, for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether)  # noqa: F401

_DV = "/usr/share/fonts/truetype/dejavu/"
_MPL = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for _n, _f in [("Serif", "DejaVuSerif.ttf"), ("Serif-Bold", "DejaVuSerif-Bold.ttf"), ("Mono", "DejaVuSansMono.ttf")]:
    pdfmetrics.registerFont(TTFont(_n, _DV + _f if os.path.exists(_DV + _f) else os.path.join(_MPL, _f)))
addMapping("Serif", 0, 0, "Serif"); addMapping("Serif", 1, 0, "Serif-Bold")
addMapping("Serif", 0, 1, "Serif"); addMapping("Serif", 1, 1, "Serif-Bold")

INK, GREY, AMBER = "#0f172a", "#64748b", "#b45309"
MARGIN = 20 * mm
W = A4[0] - 2 * MARGIN
P = ParagraphStyle("bsP", fontName="Serif", fontSize=12, leading=17.5, spaceAfter=7, textColor=colors.HexColor(INK))
PI = ParagraphStyle("bsPI", parent=P, spaceAfter=3)
N = ParagraphStyle("bsN", parent=P, leftIndent=16, bulletIndent=3, spaceAfter=4)
H1 = ParagraphStyle("bsH1", fontName="Helvetica-Bold", fontSize=26, leading=31, textColor=colors.HexColor(AMBER), spaceAfter=8)
SUB = ParagraphStyle("bsSUB", fontName="Serif", fontSize=13, leading=19, textColor=colors.HexColor(GREY), spaceAfter=12)
H2 = ParagraphStyle("bsH2", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor(INK),
                    spaceBefore=14, spaceAfter=6, keepWithNext=1)
H3 = ParagraphStyle("bsH3", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor(AMBER),
                    spaceBefore=9, spaceAfter=4, keepWithNext=1)
SM = ParagraphStyle("bsSM", fontName="Helvetica", fontSize=9.5, leading=12.5, textColor=colors.HexColor(GREY), spaceAfter=4)
FM = ParagraphStyle("bsFM", fontName="Mono", fontSize=11, leading=16, textColor=colors.HexColor(INK))
TC = ParagraphStyle("bsTC", fontName="Helvetica", fontSize=10, leading=13.5)
TH = ParagraphStyle("bsTH", parent=TC, fontName="Helvetica-Bold", textColor=colors.white)
LAB = ParagraphStyle("bsLAB", fontName="Helvetica-Bold", fontSize=10, leading=13, spaceAfter=2)
BOX = {"plain": ("#eff6ff", "#2563eb", "In plain words"), "rule": ("#fffbeb", AMBER, "Our rule"),
       "ex": ("#f0fdf4", "#16a34a", "Example"), "warn": ("#fef2f2", "#dc2626", "Watch out"),
       "why": ("#f5f3ff", "#7c3aed", "Why"), "formula": ("#f8fafc", "#334155", "Formula"),
       "key": ("#fffbeb", AMBER, "In short")}


def bl(xs):
    return [Paragraph(x, N, bulletText="•") for x in xs]


def num(xs):
    return [Paragraph(x, N, bulletText=f"{i}.") for i, x in enumerate(xs, 1)]


def title(t, sub=None):
    return [Paragraph(t, H1)] + ([Paragraph(sub, SUB)] if sub else [])


def box(kind, *items, label=None):
    bg, edge, lab = BOX[kind]
    inner = [Paragraph((label or lab).upper(), ParagraphStyle("l", parent=LAB, textColor=colors.HexColor(edge)))]
    for it in items:
        if isinstance(it, str):
            inner.append(Paragraph(it, FM if kind == "formula" else PI))
        elif isinstance(it, list):
            inner += [Paragraph(x, N, bulletText="•") for x in it]
        else:
            inner.append(it)
    t = Table([[inner]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                           ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor(edge)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return KeepTogether([t, Spacer(1, 7)])


def table(rows, widths=None, hl=None, header=INK):
    """rows: first row is the header; strings become wrapped paragraphs. Widths are rescaled to the text width."""
    widths = widths or [W / len(rows[0])] * len(rows[0])
    k = W / sum(widths) if sum(widths) > W else 1
    widths = [w * k for w in widths]
    cell = lambda c, st: Paragraph(c, st) if isinstance(c, str) else c
    data = [[cell(c, TH) for c in rows[0]]] + [[cell(c, TC) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if hl:
        st.append(("BACKGROUND", (0, hl), (-1, hl), colors.HexColor("#fef3c7")))
    t.setStyle(TableStyle(st))
    return t


def _page(running):
    def f(cv, d):
        cv.saveState()
        cv.setStrokeColor(colors.HexColor(AMBER)); cv.setLineWidth(1.2)
        cv.line(MARGIN, A4[1] - 13 * mm, A4[0] - MARGIN, A4[1] - 13 * mm)
        cv.setFont("Helvetica", 8.5); cv.setFillColor(colors.HexColor(GREY))
        cv.drawString(MARGIN, 12 * mm, running)
        cv.drawRightString(A4[0] - MARGIN, 12 * mm, f"{d.page}")
        cv.restoreState()
    return f


def build(path, story, running):
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=running).build(story, onFirstPage=_page(running), onLaterPages=_page(running))
    return path
