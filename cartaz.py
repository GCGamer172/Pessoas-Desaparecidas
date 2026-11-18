from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps


POSTER_SIZE = (900, 1400)
RED = "#b4232f"
INK = "#263238"
MUTED = "#58636b"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\Arial.ttf"]
        if bold
        else [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\Arial.ttf"]
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.ImageFont,
    max_width: int,
    fill: str,
    line_height: int,
) -> int:
    x, y = xy
    words = text.split()
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if line and draw.textlength(candidate, font=font) > max_width:
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height
            line = word
        else:
            line = candidate
    if line:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y


def generate_poster(
    photo: Image.Image,
    *,
    full_name: str,
    age: int,
    city: str,
    state: str,
    disappearance_date: date,
    last_seen_location: str,
    description: str = "",
    status: str = "Desaparecida",
) -> Image.Image:
    """Create a printable milk-carton-inspired poster without identifying anyone."""
    poster = Image.new("RGB", POSTER_SIZE, "white")
    draw = ImageDraw.Draw(poster)
    draw.rectangle((0, 0, POSTER_SIZE[0], 150), fill=RED)

    title_font = _font(55, bold=True)
    title = "PESSOA DESAPARECIDA" if status != "Localizada" else "PESSOA LOCALIZADA"
    draw.text((50, 37), title, font=title_font, fill="white")

    photo_box = (80, 190, 820, 800)
    draw.rounded_rectangle(photo_box, radius=18, fill="#f1f3f5", outline="#d5dadd", width=3)
    fitted_photo = ImageOps.fit(photo.convert("RGB"), (700, 560), method=Image.Resampling.LANCZOS)
    poster.paste(fitted_photo, (100, 210))

    name_font = _font(45, bold=True)
    name_bottom = _draw_wrapped(draw, f"NOME: {full_name}", (70, 835), name_font, 760, INK, 54)
    divider_y = max(900, name_bottom + 10)
    draw.rectangle((70, divider_y, 830, divider_y + 6), fill=RED)

    value_font = _font(28)
    y = divider_y + 24
    facts = [
        ("IDADE", f"{age} anos"),
        ("CIDADE", city),
        ("ESTADO", state),
        ("DESAPARECIMENTO", disappearance_date.strftime("%d/%m/%Y")),
        ("ÚLTIMO LOCAL VISTO", last_seen_location),
    ]
    for label, value in facts:
        y = _draw_wrapped(draw, f"{label}: {value}", (75, y), value_font, 750, INK, 36) + 8

    if description.strip():
        y = _draw_wrapped(
            draw, f"DESCRIÇÃO: {description.strip()}", (75, y), _font(23), 750, MUTED, 31
        )

    footer_y = max(1350, y + 30)
    if footer_y + 50 > poster.height:
        extended = Image.new("RGB", (poster.width, footer_y + 50), "white")
        extended.paste(poster, (0, 0))
        poster = extended
        draw = ImageDraw.Draw(poster)
    draw.rectangle((0, footer_y, POSTER_SIZE[0], footer_y + 50), fill=RED)
    footer = "COMPARTILHE COM RESPONSABILIDADE"
    footer_font = _font(22, bold=True)
    draw.text(
        ((POSTER_SIZE[0] - draw.textlength(footer, font=footer_font)) / 2, footer_y + 13),
        footer,
        font=footer_font,
        fill="white",
    )
    return poster


def poster_png_bytes(poster: Image.Image) -> bytes:
    output = BytesIO()
    poster.save(output, format="PNG", optimize=True)
    return output.getvalue()


def poster_pdf_bytes(poster: Image.Image) -> bytes:
    output = BytesIO()
    poster.convert("RGB").save(output, format="PDF", resolution=150.0)
    return output.getvalue()


def safe_poster_filename(full_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", full_name.strip()).strip("-_").lower()
    return f"cartaz-{slug or 'pessoa-desaparecida'}"
