from PIL import Image

import services.detection as detection
from services.detection import PersonDetection, detect_people, image_to_jpeg_bytes
from services.ocr import suggest_fields


def test_detection_image_output_is_valid_jpeg():
    output = image_to_jpeg_bytes(Image.new("RGB", (10, 10), "white"))
    assert output[:2] == b"\xff\xd8"


def test_person_detection_filters_and_draws_person_boxes(monkeypatch):
    class FakeBox:
        def __init__(self, class_id, coordinates, confidence):
            self.cls = [type("Value", (), {"item": lambda self: class_id})()]
            self.xyxy = [type("Coordinates", (), {"tolist": lambda self: coordinates})()]
            self.conf = [type("Value", (), {"item": lambda self: confidence})()]

    class FakeModel:
        def predict(self, _image, verbose=False):
            assert verbose is False
            return [
                type(
                    "Result",
                    (),
                    {"boxes": [FakeBox(0, [1, 1, 8, 8], 0.91), FakeBox(2, [0, 0, 4, 4], 0.8)]},
                )()
            ]

    monkeypatch.setattr(detection, "_load_model", lambda: FakeModel())
    annotated, detections = detect_people(Image.new("RGB", (10, 10), "white"))

    assert detections == [PersonDetection(1, 1, 8, 8, 0.91)]
    assert annotated.size == (10, 10)


def test_ocr_field_suggestions_extract_labeled_text():
    result = suggest_fields(
        [
            {"text": "Nome: Maria de Teste", "confidence": 0.9},
            {"text": "Idade: 32 anos", "confidence": 0.9},
            {"text": "Cidade: Belém", "confidence": 0.9},
            {"text": "Estado: PA", "confidence": 0.9},
            {"text": "Última localização: Praça fictícia", "confidence": 0.8},
            {"text": "Descrição: blusa vermelha", "confidence": 0.9},
            {"text": "Desaparecimento: 10/05/2024", "confidence": 0.9},
        ]
    )
    assert result == {
        "full_name": "Maria de Teste",
        "age": 32,
        "city": "Belém",
        "state": "PA",
        "last_seen_location": "Praça fictícia",
        "description": "blusa vermelha",
        "disappearance_date": "10/05/2024",
    }
