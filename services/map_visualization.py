import base64
from io import BytesIO

import pandas as pd
import pydeck as pdk
import streamlit as st
from PIL import Image, ImageDraw, ImageOps

from services.images import load_image


BRAZIL_CENTER = {"latitude": -14.2, "longitude": -52.0, "zoom": 1.6}
PHOTO_TILE_SIZE = 64
PHOTO_SIZE = 48
PHOTO_MARKER_SIZE = 14


def build_photo_atlas(points: pd.DataFrame) -> tuple[str | None, dict[str, dict[str, object]]]:
    if "photo_path" not in points or points.empty:
        return None, {}

    atlas = Image.new("RGBA", (PHOTO_TILE_SIZE, PHOTO_TILE_SIZE * len(points)), (0, 0, 0, 0))
    icon_mapping = {}
    for index, row in enumerate(points.itertuples(index=False)):
        icon = str(row.icon)
        avatar = ImageOps.fit(
            load_image(row.photo_path).convert("RGBA"),
            (PHOTO_SIZE, PHOTO_SIZE),
            centering=(0.5, 0.35),
        )
        mask = Image.new("L", (PHOTO_SIZE, PHOTO_SIZE), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, PHOTO_SIZE - 1, PHOTO_SIZE - 1), fill=255)
        avatar.putalpha(mask)

        top = index * PHOTO_TILE_SIZE
        tile = Image.new("RGBA", (PHOTO_TILE_SIZE, PHOTO_TILE_SIZE), (0, 0, 0, 0))
        ImageDraw.Draw(tile).ellipse((3, 3, 61, 61), fill="white")
        tile.alpha_composite(avatar, ((PHOTO_TILE_SIZE - PHOTO_SIZE) // 2,) * 2)
        atlas.alpha_composite(tile, (0, top))
        icon_mapping[icon] = {
            "x": 0,
            "y": top,
            "width": PHOTO_TILE_SIZE,
            "height": PHOTO_TILE_SIZE,
            "mask": False,
        }

    buffer = BytesIO()
    atlas.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}", icon_mapping


def render_brazil_map(
    points: pd.DataFrame,
    key: str,
    center: dict[str, float] | None = None,
    show_photos: bool = True,
) -> None:
    layers = []
    if show_photos:
        icon_atlas, icon_mapping = build_photo_atlas(points)
    else:
        icon_atlas, icon_mapping = None, {}

    if icon_atlas is not None:
        layers.append(
            pdk.Layer(
                "IconLayer",
                data=points,
                get_position="[lon, lat]",
                get_icon="icon",
                get_size=PHOTO_MARKER_SIZE,
                size_units='"pixels"',
                size_scale=1,
                icon_atlas=f'"{icon_atlas}"',
                icon_mapping=icon_mapping,
                pickable=True,
                alpha_cutoff=0.05,
            )
        )
    elif not points.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=points,
                get_position="[lon, lat]",
                get_radius=5000,
                radius_units='"meters"',
                radius_min_pixels=3,
                radius_max_pixels=5,
                get_fill_color=[220, 38, 38],
                get_line_color=[153, 27, 27],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
            )
        )
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(**(center or BRAZIL_CENTER), pitch=0, bearing=0),
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={"text": "{nome}\n{cidade} · {quantidade} cadastro(s)"},
    )
    st.pydeck_chart(deck, height=520, width="stretch", key=key)
