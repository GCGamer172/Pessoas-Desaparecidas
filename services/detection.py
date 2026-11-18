from dataclasses import asdict, dataclass
from functools import lru_cache
from io import BytesIO
import os

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class PersonDetection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float


@lru_cache(maxsize=1)
def _load_model():
    try:
        from ultralytics import YOLO

        return YOLO(os.getenv("YOLO_MODEL", "yolov8n.pt"))
    except Exception as exc:
        raise RuntimeError(
            "Não foi possível carregar o modelo YOLO. Verifique a instalação do Ultralytics "
            "e a disponibilidade do arquivo de pesos (a primeira execução pode baixá-lo)."
        ) from exc


def detect_people(image: Image.Image) -> tuple[Image.Image, list[PersonDetection]]:
    model = _load_model()
    try:
        results = model.predict(image, verbose=False)
    except Exception as exc:
        raise RuntimeError(f"Falha ao executar a detecção YOLO: {exc}") from exc

    detections: list[PersonDetection] = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            if int(box.cls[0].item()) != 0:
                continue
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            detections.append(
                PersonDetection(x1, y1, x2, y2, float(box.conf[0].item()))
            )

    annotated = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    for detection in detections:
        cv2.rectangle(
            annotated,
            (detection.x1, detection.y1),
            (detection.x2, detection.y2),
            (48, 180, 90),
            2,
        )
        label = f"Pessoa: {detection.confidence:.0%}"
        cv2.putText(
            annotated,
            label,
            (detection.x1, max(detection.y1 - 8, 18)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (48, 180, 90),
            2,
            cv2.LINE_AA,
        )
    output = Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
    return output, detections


def image_to_jpeg_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def detections_as_dicts(detections: list[PersonDetection]) -> list[dict[str, int | float]]:
    return [asdict(item) for item in detections]
