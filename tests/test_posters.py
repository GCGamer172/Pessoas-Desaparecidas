from datetime import date
from io import BytesIO

from PIL import Image

from cartaz import generate_poster, poster_pdf_bytes, poster_png_bytes, safe_poster_filename


def test_poster_generates_png_and_pdf_with_expected_content_size():
    poster = generate_poster(
        Image.new("RGB", (240, 320), "white"),
        full_name="Pessoa Fictícia",
        age=24,
        city="Belém",
        state="PA",
        disappearance_date=date(2025, 1, 10),
        last_seen_location="Praça fictícia",
        description="Blusa vermelha",
    )

    png = Image.open(BytesIO(poster_png_bytes(poster)))
    pdf = poster_pdf_bytes(poster)
    assert png.size == (900, 1400)
    assert pdf.startswith(b"%PDF")


def test_poster_expands_to_fit_long_description_and_marks_located_status():
    poster = generate_poster(
        Image.new("RGB", (100, 100), "white"),
        full_name="Pessoa de Teste",
        age=30,
        city="Belém",
        state="PA",
        disappearance_date=date(2025, 1, 10),
        last_seen_location="Local de teste",
        description="Descrição longa " * 120,
        status="Localizada",
    )
    assert poster.width == 900
    assert poster.height > 1400


def test_safe_filename_removes_unsafe_characters():
    assert safe_poster_filename("Maria de Teste") == "cartaz-maria-de-teste"
    assert safe_poster_filename("../") == "cartaz-pessoa-desaparecida"
