"""
PDF generation via Chrome headless (HTML → PDF).
Also keeps legacy ReportLab generate_pdf() for backwards compatibility.

Public API:
    html_to_pdf(html_path, pdf_path) -> str    # convert HTML file to PDF
    pdf_path(report_type, date_str)  -> str    # build output path
"""
from __future__ import annotations
import os
import subprocess
import tempfile

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "data", "reports")

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
]


def _chrome_bin() -> str:
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    raise RuntimeError(
        "Chrome/Chromium nao encontrado. Instale o Google Chrome ou ajuste CHROME_PATHS."
    )


def pdf_path(report_type: str, date_str: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    return os.path.join(REPORTS_DIR, f"{report_type}_{date_str}.pdf")


def html_to_pdf(html_source: str, output_pdf: str) -> str:
    """
    Converts an HTML file (or HTML string) to PDF using Chrome headless.

    Args:
        html_source: path to an existing .html file, OR a raw HTML string.
        output_pdf:  destination .pdf path.

    Returns:
        output_pdf path on success.
    """
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    chrome = _chrome_bin()

    # If html_source is a raw HTML string, write to a temp file first
    _tmp = None
    if not os.path.exists(html_source):
        _tmp = tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        )
        _tmp.write(html_source)
        _tmp.close()
        html_file = _tmp.name
    else:
        html_file = html_source

    try:
        result = subprocess.run(
            [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
                "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={output_pdf}",
                "--print-to-pdf-no-header",
                f"file://{os.path.abspath(html_file)}",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Chrome retornou codigo {result.returncode}:\n{result.stderr}"
            )
    finally:
        if _tmp:
            os.unlink(_tmp.name)

    return output_pdf


# ── Legacy stub (kept so old imports don't break) ─────────────────────────────

def generate_pdf(analysis, output_path: str) -> str:  # noqa: ANN001
    """Legacy shim — converts ReportData to HTML then to PDF."""
    from src.html_generator import generate_html
    import tempfile, os

    tmp_html = tempfile.mktemp(suffix=".html")
    generate_html(analysis, tmp_html)
    try:
        html_to_pdf(tmp_html, output_path)
    finally:
        if os.path.exists(tmp_html):
            os.unlink(tmp_html)
    return output_path
