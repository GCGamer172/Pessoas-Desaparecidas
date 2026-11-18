import base64
import json
from io import BytesIO

import pandas as pd
from PIL import Image

import services.map_visualization as map_visualization


def test_build_photo_atlas_creates_icon_mapping_and_png_data_uri(monkeypatch):
    monkeypatch.setattr(
        map_visualization,
        "load_image",
        lambda _path: Image.new("RGB", (30, 50), "navy"),
    )
    points = pd.DataFrame(
        [
            {"icon": "person-1", "photo_path": "uploads/one.jpg"},
            {"icon": "person-2", "photo_path": "uploads/two.jpg"},
        ]
    )

    atlas_uri, icon_mapping = map_visualization.build_photo_atlas(points)

    assert atlas_uri is not None
    assert atlas_uri.startswith("data:image/png;base64,")
    assert set(icon_mapping) == {"person-1", "person-2"}
    assert icon_mapping["person-1"]["y"] == 0
    assert icon_mapping["person-2"]["y"] == map_visualization.PHOTO_TILE_SIZE
    image = Image.open(BytesIO(base64.b64decode(atlas_uri.split(",", 1)[1])))
    assert image.size == (map_visualization.PHOTO_TILE_SIZE, 2 * map_visualization.PHOTO_TILE_SIZE)


def test_build_photo_atlas_is_empty_when_no_profiles():
    atlas_uri, icon_mapping = map_visualization.build_photo_atlas(
        pd.DataFrame(columns=["lat", "lon"])
    )

    assert atlas_uri is None
    assert icon_mapping == {}


def test_render_brazil_map_serializes_photo_atlas_as_literal(monkeypatch):
    monkeypatch.setattr(
        map_visualization,
        "load_image",
        lambda _path: Image.new("RGB", (30, 50), "navy"),
    )
    rendered = []
    monkeypatch.setattr(
        map_visualization.st,
        "pydeck_chart",
        lambda deck, **_kwargs: rendered.append(deck),
    )
    points = pd.DataFrame(
        [
            {
                "lat": -22.9,
                "lon": -43.2,
                "icon": "person-1",
                "photo_path": "uploads/one.jpg",
                "cidade": "Rio de Janeiro/RJ",
                "quantidade": 1,
            }
        ]
    )

    map_visualization.render_brazil_map(points, key="test-photo-map")

    serialized = json.loads(rendered[0].to_json())
    layer = serialized["layers"][0]
    assert rendered[0]._tooltip["text"] == "{nome}\n{cidade} · {quantidade} cadastro(s)"
    assert layer["iconAtlas"].startswith("data:image/png;base64,")
    assert not layer["iconAtlas"].startswith("@@=")
    assert layer["getSize"] == map_visualization.PHOTO_MARKER_SIZE
    assert layer["sizeUnits"] == "pixels"


def test_render_brazil_map_uses_red_dots_when_photos_are_disabled(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        map_visualization.st,
        "pydeck_chart",
        lambda deck, **_kwargs: rendered.append(deck),
    )
    points = pd.DataFrame(
        [{"lat": -22.9, "lon": -43.2, "cidade": "Rio de Janeiro/RJ", "quantidade": 1}]
    )

    map_visualization.render_brazil_map(
        points,
        key="test-dot-map",
        show_photos=False,
    )

    serialized = json.loads(rendered[0].to_json())
    layer = serialized["layers"][0]
    assert layer["@@type"] == "ScatterplotLayer"
    assert layer["getFillColor"] == [220, 38, 38]
    assert layer["getRadius"] == 5000
    assert layer["radiusUnits"] == "meters"
