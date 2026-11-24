"""Make reportlab's built-in 'Helvetica' family draw ₹, − (U+2212), ≥, ≈ etc.: the standard PDF Helvetica has no glyphs
for them (they print as black boxes). Importing this module re-registers the Helvetica names with DejaVu Sans
(shipped with matplotlib), so every existing style keeps working. Import it before building any PDF."""
import os
import matplotlib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

_D = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for name, f in [("Helvetica", "DejaVuSans.ttf"), ("Helvetica-Bold", "DejaVuSans-Bold.ttf"),
                ("Helvetica-Oblique", "DejaVuSans-Oblique.ttf"), ("Helvetica-BoldOblique", "DejaVuSans-BoldOblique.ttf")]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(_D, f)))
addMapping("Helvetica", 0, 0, "Helvetica"); addMapping("Helvetica", 1, 0, "Helvetica-Bold")
addMapping("Helvetica", 0, 1, "Helvetica-Oblique"); addMapping("Helvetica", 1, 1, "Helvetica-BoldOblique")
