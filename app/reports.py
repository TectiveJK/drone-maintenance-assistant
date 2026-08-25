from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument


def export_text_report(title, lines, output_dir="reports"):
    directory = Path(output_dir); directory.mkdir(exist_ok=True)
    filename = directory / f"{datetime.now():%Y%m%d_%H%M%S}_{title.lower().replace(' ', '_')}.txt"
    filename.write_text(title + "\n" + "=" * len(title) + "\n\n" + "\n".join(lines), encoding="utf-8")
    return filename


def export_pdf_report(text, path, font_size=8):
    destination = Path(path)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")
    writer = QPdfWriter(str(destination))
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
    writer.setTitle("Drone Maintenance Report")
    document = QTextDocument()
    font = QFont("Sans Serif", font_size)
    font.setStyleStrategy(QFont.PreferDefault)
    document.setDefaultFont(font)
    document.setDocumentMargin(4)
    document.setPlainText(text)
    document.print_(writer)
    return destination
