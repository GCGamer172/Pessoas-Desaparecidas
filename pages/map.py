import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.connection import get_session
from database.models import MissingPerson
from services.geocoding import GeocodingError
from services.images import load_image
from services.map_locations import STATE_CAPITALS, cached_city_coordinates
from services.map_visualization import render_brazil_map


def map_page() -> None:
    st.title("Mapa de pessoas desaparecidas")
    st.caption("Últimos locais por cidade · protótipo com cadastros autorizados")
    st.info(
        "Este mapa não é uma base oficial e não importa casos reais automaticamente. "
        "Mostra somente pessoas desaparecidas com autorização de publicação marcada. "
        "Os marcadores representam o centro aproximado da cidade, nunca o endereço "
        "ou o local exato onde a pessoa foi vista."
    )

    session = get_session()
    try:
        people = list(
            session.scalars(
                select(MissingPerson)
                .where(
                    MissingPerson.public_map_consent.is_(True),
                    MissingPerson.status == "Desaparecida",
                )
                .order_by(MissingPerson.disappearance_date.desc())
            ).all()
        )
    finally:
        session.close()

    if not people:
        st.metric("Pessoas desaparecidas no mapa", 0)
        render_brazil_map(
            pd.DataFrame(columns=["lat", "lon", "radius", "cidade", "quantidade"]),
            key="missing-people-brazil-map-v3",
        )
        st.info(
            "Nenhuma pessoa cadastrada está autorizada para aparecer no mapa. "
            "Na Galeria Milk Carton, edite cada cadastro e marque a autorização "
            "de publicação para incluí-lo."
        )
        return

    metric_col, state_col = st.columns(2)
    metric_col.metric("Pessoas desaparecidas no mapa", len(people))
    state_col.metric("Cidades informadas", len({(person.city, person.state) for person in people}))

    states = ["Todos os estados", *sorted({person.state for person in people})]
    selected_state = st.selectbox("Filtrar por estado", states)
    filtered_people = (
        people
        if selected_state == "Todos os estados"
        else [person for person in people if person.state == selected_state]
    )

    city_locations: dict[tuple[str, str], tuple[float, float] | None] = st.session_state.get(
        "map_city_locations", {}
    )
    unique_cities = sorted({(person.city, person.state) for person in filtered_people})
    st.caption(
        "Para posicionar os marcadores no centro aproximado de cada cidade, a busca "
        "envia somente o nome da cidade e a UF ao OpenStreetMap/Nominatim. "
        "Não envia nomes, fotos nem outros dados pessoais. Dados geográficos "
        "fornecidos por © OpenStreetMap contributors. A consulta é limitada a "
        "uma solicitação por segundo e segue a "
        "[política do Nominatim](https://operations.osmfoundation.org/policies/nominatim/)."
    )
    if st.button("Localizar cidades no mapa"):
        updated_locations = dict(city_locations)
        try:
            with st.spinner("Localizando cidades..."):
                for city, state in unique_cities:
                    key = (city, state)
                    if key not in updated_locations:
                        updated_locations[key] = cached_city_coordinates(city, state)
            st.session_state["map_city_locations"] = updated_locations
            city_locations = updated_locations
        except GeocodingError as exc:
            st.error(str(exc))

    map_rows = []
    for person in filtered_people:
        coordinates = city_locations.get((person.city, person.state))
        if coordinates is None:
            coordinates = STATE_CAPITALS[person.state]
        map_rows.append(
            {
                "lat": coordinates[0],
                "lon": coordinates[1],
                "icon": f"person-{person.id}",
                "photo_path": person.image_path,
                "nome": person.full_name,
                "cidade": f"{person.city}/{person.state}",
                "quantidade": 1,
            }
        )
    render_brazil_map(pd.DataFrame(map_rows), key="missing-people-brazil-map-v3")
    st.caption(
        "O mapa geral usa miniaturas menores para os perfis autorizados; no mapa "
        "individual de cada registro, a localização aparece como um ponto vermelho. "
        "Se uma cidade ainda não foi localizada, o marcador provisório fica na capital da UF."
    )

    st.subheader(f"Registros autorizados ({len(filtered_people)})")
    for person in filtered_people:
        with st.container(border=True):
            photo_col, detail_col = st.columns([1, 2], vertical_alignment="center")
            with photo_col:
                st.image(load_image(person.image_path), width=150)
            with detail_col:
                st.subheader(person.full_name)
                st.markdown(
                    f"**{person.age} anos** · {person.city}/{person.state} · "
                    f"desaparecida em {person.disappearance_date.strftime('%d/%m/%Y')}"
                )
                st.markdown(f"**Cidade/UF aproximada do desaparecimento:** {person.city}/{person.state}")
                if person.description:
                    st.caption(person.description)
            coordinates = city_locations.get((person.city, person.state))
            if coordinates is None:
                coordinates = STATE_CAPITALS[person.state]
                st.warning(
                    f"A cidade {person.city}/{person.state} ainda não foi localizada; "
                    "o marcador do mapa principal está temporariamente na capital da UF."
                )
            else:
                st.caption(f"Marcador aproximado do município: {person.city}/{person.state}.")
            render_brazil_map(
                pd.DataFrame(
                    [
                        {
                            "lat": coordinates[0],
                            "lon": coordinates[1],
                            "nome": person.full_name,
                            "cidade": f"{person.city}/{person.state}",
                            "quantidade": 1,
                        }
                    ]
                ),
                key=f"person-brazil-map-v3-{person.id}",
                center={
                    "latitude": coordinates[0],
                    "longitude": coordinates[1],
                    "zoom": 8,
                },
                show_photos=False,
            )
