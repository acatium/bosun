"""Render data/deals/atlas/cim.md to a PDF for the demo mailbox. Usage: python tools/make_cim.py <out.pdf>

Handles only the Markdown this file uses: headings, paragraphs, bullet and numbered lists, and one table.
"""
import pathlib
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import ListFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "data" / "deals" / "atlas" / "cim.md"


def inline(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text.replace("&", "&amp;"))


def build(out: pathlib.Path) -> None:
    styles = getSampleStyleSheet()
    story, bullets, numbered, table, para = [], [], [], [], []

    def flush():
        nonlocal bullets, numbered, table, para
        if para:
            story.append(Paragraph(inline(" ".join(para)), styles["BodyText"]))
        if bullets:
            story.append(ListFlowable([Paragraph(inline(b), styles["BodyText"]) for b in bullets], bulletType="bullet"))
        if numbered:
            story.append(ListFlowable([Paragraph(inline(n), styles["BodyText"]) for n in numbered], bulletType="1"))
        if table:
            grid = Table(table)
            grid.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                                      ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                                      ("FONTSIZE", (0, 0), (-1, -1), 9)]))
            story.append(grid)
        bullets, numbered, table, para = [], [], [], []

    for line in SOURCE.read_text().splitlines():
        if line.startswith("|"):
            if set(line.replace("|", "").strip()) <= {"-", " "}:
                continue
            table.append([cell.strip() for cell in line.strip("|").split("|")])
            continue
        if re.match(r"^- ", line):
            bullets.append(line[2:]); continue
        if re.match(r"^\d+\. ", line):
            numbered.append(re.sub(r"^\d+\. ", "", line)); continue
        if line.startswith("  ") and (bullets or numbered):
            target = bullets if bullets else numbered
            target[-1] += " " + line.strip(); continue
        if line.strip() and not line.startswith("#"):
            if bullets or numbered or table:
                flush()
            para.append(line.strip()); continue
        flush()
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), styles["Title"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), styles["Heading2"]))
        else:
            story.append(Spacer(1, 4))
    flush()
    SimpleDocTemplate(str(out), pagesize=LETTER, title="Project Atlas CIM").build(story)


if __name__ == "__main__":
    build(pathlib.Path(sys.argv[1]))
