from functools import lru_cache
from io import BytesIO
import re

from PIL import Image


@lru_cache(maxsize=1)
def _load_reader():
    try:
        import easyocr

        return easyocr.Reader(["pt", "en"], gpu=False)
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível iniciar o EasyOCR. Verifique a instalação das dependências "
            "e o download inicial dos modelos."
        ) from exc


def read_poster(content: bytes) -> list[dict[str, str | float]]:
    try:
        import numpy as np

        image = Image.open(BytesIO(content)).convert("RGB")
        results = _load_reader().readtext(np.array(image), detail=1, paragraph=False)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Falha ao processar o cartaz com OCR: {exc}") from exc

    return [
        {"text": str(text).strip(), "confidence": float(confidence)}
        for _box, text, confidence in results
        if str(text).strip()
    ]


def _capture(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip(" \t:;,-")
    return ""


def suggest_fields(lines: list[dict[str, str | float]]) -> dict[str, str | int]:
    text = "\n".join(str(line["text"]) for line in lines)
    name = _capture(text, [r"(?:nome(?: completo)?|desaparecid[oa])\s*[:\-]\s*([^\n]+)"])
    age_text = _capture(text, [r"(?:idade)\s*[:\-]?\s*(\d{1,3})\s*(?:anos?)?"])
    city = _capture(text, [r"(?:cidade|munic[ií]pio)\s*[:\-]\s*([^\n,]+)"])
    state = _capture(text, [r"(?:estado|uf)\s*[:\-]\s*([A-Za-z]{2})"])
    location = _capture(
        text,
        [
            r"(?:[uú]ltima localiza[cç][aã]o|[uú]ltimo local visto|visto[oa] pela [uú]ltima vez|local)\s*[:\-]\s*([^\n]+)"
        ],
    )
    description = _capture(text, [r"(?:descri[cç][aã]o|caracter[ií]sticas)\s*[:\-]\s*([^\n]+)"])
    date_text = _capture(
        text,
        [r"(?:desapareciment[oa]|desapareceu em|data)\s*[:\-]\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"],
    )
    return {
        "full_name": name[:160],
        "age": int(age_text) if age_text.isdigit() and int(age_text) <= 120 else 0,
        "city": city[:100],
        "state": state.upper()[:2],
        "last_seen_location": location[:300],
        "description": description[:2000],
        "disappearance_date": date_text,
    }
