import uuid
import os
from pathlib import Path

from PIL import Image

from services.validation import validate_image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_DIR = Path(os.getenv("MISSING_PERSONS_UPLOAD_DIR", PROJECT_ROOT / "uploads")).expanduser().resolve()


def _stored_path(destination: Path) -> str:
    try:
        return destination.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(destination.resolve())


def store_image(content: bytes, original_filename: str) -> str:
    suffix = validate_image(content, original_filename)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{suffix}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(content)
    return _stored_path(destination)


def resolve_image_path(relative_path: str) -> Path:
    stored_path = Path(relative_path)
    path = (stored_path if stored_path.is_absolute() else PROJECT_ROOT / stored_path).resolve()
    if path.parent != UPLOAD_DIR.resolve():
        raise ValueError("O caminho da imagem está fora do diretório de uploads.")
    return path


def load_image(relative_path: str) -> Image.Image:
    with Image.open(resolve_image_path(relative_path)) as image:
        return image.convert("RGB")


def delete_image(relative_path: str) -> None:
    path = resolve_image_path(relative_path)
    if path.exists():
        path.unlink()


def store_generated_image(content: bytes, suffix: str = ".jpg") -> str:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{suffix}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(content)
    return _stored_path(destination)
