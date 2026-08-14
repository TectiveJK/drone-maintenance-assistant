from pathlib import Path
from datetime import datetime


def export_text_report(title, lines, output_dir="reports"):
    directory = Path(output_dir); directory.mkdir(exist_ok=True)
    filename = directory / f"{datetime.now():%Y%m%d_%H%M%S}_{title.lower().replace(' ', '_')}.txt"
    filename.write_text(title + "\n" + "=" * len(title) + "\n\n" + "\n".join(lines), encoding="utf-8")
    return filename
