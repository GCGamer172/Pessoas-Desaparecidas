from datetime import date, timedelta
from io import BytesIO

import pytest
from PIL import Image

from services.validation import (
    ValidationError,
    validate_image,
    validate_person_fields,
    validate_status_change,
)


def valid_fields(**overrides):
    fields = {
        "full_name": "Pessoa Fictícia",
        "age": 20,
        "city": "Belém",
        "state": "PA",
        "last_seen_location": "Local fictício",
        "disappearance_date": date.today(),
        "status": "Em aberto",
    }
    fields.update(overrides)
    return fields


def test_person_validation_normalizes_and_accepts_valid_record():
    result = validate_person_fields(
        **valid_fields(
            full_name="  Pessoa Fictícia  ",
            state="pa",
            status="Desaparecida",
            description="  Blusa azul  ",
        )
    )
    assert result["full_name"] == "Pessoa Fictícia"
    assert result["state"] == "PA"
    assert result["description"] == "Blusa azul"


def test_person_validation_accepts_brazil_coordinates():
    result = validate_person_fields(
        **valid_fields(),
        last_seen_latitude=-1.4558,
        last_seen_longitude=-48.4902,
    )
    assert result["last_seen_latitude"] == -1.4558
    assert result["last_seen_longitude"] == -48.4902


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(-1.0, None), (None, -48.0), (10.0, -48.0), (-1.0, -80.0)],
)
def test_person_validation_rejects_incomplete_or_out_of_brazil_coordinates(latitude, longitude):
    with pytest.raises(ValidationError, match="coordenadas|latitude|longitude"):
        validate_person_fields(
            **valid_fields(),
            last_seen_latitude=latitude,
            last_seen_longitude=longitude,
        )


@pytest.mark.parametrize(
    "override",
    [
        {"full_name": " "},
        {"age": -1},
        {"age": 121},
        {"city": ""},
        {"state": "XX"},
        {"last_seen_location": ""},
        {"disappearance_date": date.today() + timedelta(days=1)},
        {"status": "Outro"},
        {"description": "d" * 2001},
    ],
)
def test_person_validation_rejects_invalid_record(override):
    with pytest.raises(ValidationError):
        validate_person_fields(**valid_fields(**override))


def test_status_change_requires_authorization():
    with pytest.raises(ValidationError, match="autorização"):
        validate_status_change(None, "Desaparecida", authorized=False)
    with pytest.raises(ValidationError, match="autorização"):
        validate_status_change("Desaparecida", "Localizada", authorized=False)

    validate_status_change("Desaparecida", "Desaparecida", authorized=False)
    validate_status_change("Desaparecida", "Localizada", authorized=True)


def image_bytes(image_format="JPEG"):
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format=image_format)
    return buffer.getvalue()


def test_image_validation_accepts_real_jpeg():
    assert validate_image(image_bytes(), "foto.jpg") == ".jpg"


@pytest.mark.parametrize(
    ("content", "filename"),
    [
        (b"not an image", "foto.jpg"),
        (image_bytes("PNG"), "foto.jpg"),
        (image_bytes(), "foto.gif"),
    ],
)
def test_image_validation_rejects_invalid_or_oversized_upload(content, filename):
    with pytest.raises(ValidationError):
        validate_image(content, filename)


def test_image_validation_rejects_oversized_upload():
    with pytest.raises(ValidationError, match="5 MB"):
        validate_image(b"x" * (5 * 1024 * 1024 + 1), "foto.jpg")
