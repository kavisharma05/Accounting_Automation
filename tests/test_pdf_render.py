from reportlab.pdfgen import canvas

from app.integrations.document_understanding.render import looks_like_pdf, prepare_vision_input


def _tiny_pdf() -> bytes:
    from io import BytesIO

    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, "TAX INVOICE NP/TEST/1")
    c.drawString(72, 700, "Vendor: Nimbus Stationery")
    c.save()
    return buf.getvalue()


def test_pdf_magic_and_jpeg_render():
    pdf = _tiny_pdf()
    assert looks_like_pdf(pdf, "application/octet-stream")
    image, mime = prepare_vision_input(pdf, "application/pdf")
    assert mime == "image/jpeg"
    assert image[:2] == b"\xff\xd8"


def test_image_passthrough():
    jpeg = b"\xff\xd8\xff" + b"x" * 20
    out, mime = prepare_vision_input(jpeg, "image/jpeg")
    assert out == jpeg
    assert mime == "image/jpeg"
