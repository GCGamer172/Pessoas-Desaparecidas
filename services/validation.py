from datetime import date
from pathlib import Path

from PIL import Image, UnidentifiedImageError


ALLOWED_STATES = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}
ALLOWED_STATUSES = {"Desaparecida", "Localizada"}
LEGACY_STATUSES = {"Em aberto"}
ALLOWED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class ValidationError(ValueError):
    """Raised when user-provided data does not meet application rules."""


def validate_person_fields(
    full_name: str,
    age: int,
    city: str,
    state: str,
    last_seen_location: str,
    disappearance_date: date,
    status: str,
    description: str = "",
    last_seen_latitude: float | None = None,
    last_seen_longitude: float | None = None,
) -> dict[str, object]:
    cleaned_name = full_name.strip()
    cleaned_city = city.strip()
    cleaned_location = last_seen_location.strip()
    cleaned_state = state.strip().upper()
    cleaned_description = description.strip()

    if not cleaned_name or len(cleaned_name) > 160:
        raise ValidationError("Informe o nome completo (máximo de 160 caracteres).")
    if isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 120:
        raise ValidationError("A idade deve ser um número inteiro entre 0 e 120.")
    if not cleaned_city or len(cleaned_city) > 100:
        raise ValidationError("Informe a cidade (máximo de 100 caracteres).")
    if cleaned_state not in ALLOWED_STATES:
        raise ValidationError("Selecione uma sigla válida de estado brasileiro.")
    if not cleaned_location or len(cleaned_location) > 300:
        raise ValidationError("Informe a última localização (máximo de 300 caracteres).")
    if not isinstance(disappearance_date, date) or disappearance_date > date.today():
        raise ValidationError("A data do desaparecimento deve ser válida e não futura.")
    if status not in ALLOWED_STATUSES | LEGACY_STATUSES:
        raise ValidationError("Selecione um status válido.")
    if len(cleaned_description) > 2000:
        raise ValidationError("A descrição deve ter no máximo 2.000 caracteres.")
    if (last_seen_latitude is None) != (last_seen_longitude is None):
        raise ValidationError("Informe latitude e longitude juntas, ou deixe ambas vazias.")
    if last_seen_latitude is not None and last_seen_longitude is not None:
        if not -35 <= last_seen_latitude <= 6 or not -75 <= last_seen_longitude <= -34:
            raise ValidationError("As coordenadas devem estar dentro dos limites aproximados do Brasil.")

    return {
        "full_name": cleaned_name,
        "age": age,
        "city": cleaned_city,
        "state": cleaned_state,
        "last_seen_location": cleaned_location,
        "description": cleaned_description,
        "disappearance_date": disappearance_date,
        "status": status,
        "last_seen_latitude": last_seen_latitude,
        "last_seen_longitude": last_seen_longitude,
    }


def validate_status_change(
    previous_status: str | None,
    new_status: str,
    authorized: bool,
) -> None:
    if (previous_status is None or new_status != previous_status) and not authorized:
        raise ValidationError("Confirme que tem autorização para registrar ou alterar o status.")


def validate_image(content: bytes, filename: str) -> str:
    if not content:
        raise ValidationError("O arquivo enviado está vazio.")
    if len(content) > MAX_IMAGE_BYTES:
        raise ValidationError("A imagem excede o limite de 5 MB.")

    suffix = Path(filename).suffix.lower()
    expected_format = ALLOWED_IMAGE_FORMATS.get(suffix)
    if expected_format is None:
        raise ValidationError("Formato não permitido. Envie JPG, JPEG ou PNG.")

    try:
        from io import BytesIO

        with Image.open(BytesIO(content)) as image:
            if image.format != expected_format:
                raise ValidationError("A extensão do arquivo não corresponde ao conteúdo da imagem.")
            if image.width * image.height > 25_000_000:
                raise ValidationError("A imagem excede o limite de 25 megapixels.")
            image.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, EOFError, OSError, SyntaxError, UnidentifiedImageError) as exc:
        raise ValidationError("O arquivo não é uma imagem válida.") from exc
    return suffix
