"""Compatibility exports for the YOLO person detector."""

from services.detection import (
    PersonDetection,
    detect_people,
    detections_as_dicts,
    image_to_jpeg_bytes,
)

__all__ = [
    "PersonDetection",
    "detect_people",
    "detections_as_dicts",
    "image_to_jpeg_bytes",
]
