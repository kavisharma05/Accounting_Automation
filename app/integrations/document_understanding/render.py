"""Normalize uploads so vision models always receive an image."""

from io import BytesIO


def looks_like_pdf(content: bytes, mime_type: str | None) -> bool:
    if content[:4] == b"%PDF":
        return True
    return (mime_type or "").lower() in {"application/pdf", "application/x-pdf"}


def prepare_vision_input(content: bytes, mime_type: str | None) -> tuple[bytes, str]:
    """Return (bytes, mime) suitable for a vision API. PDFs become a JPEG of page 1."""
    mime = (mime_type or "").lower() or "application/octet-stream"
    if mime.startswith("image/"):
        return content, mime
    if looks_like_pdf(content, mime):
        return _pdf_first_page_jpeg(content), "image/jpeg"
    raise ValueError(
        "This bill must be a photo (JPG/PNG/WebP) or a PDF. "
        f"Got {mime or 'unknown type'}."
    )


def _pdf_first_page_jpeg(content: bytes) -> bytes:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(content)
    if len(pdf) < 1:
        raise ValueError("That PDF has no pages.")
    page = pdf[0]
    pil = page.render(scale=2.0).to_pil().convert("RGB")
    buf = BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return buf.getvalue()
