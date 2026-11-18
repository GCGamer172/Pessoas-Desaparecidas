import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from database.connection import get_session
from database.models import ImageAnalysis, MissingPerson, OCRAnalysis
from pages.records import records_dataframe
from services.geocoding import GeocodingError
from services.map_locations import STATE_CAPITALS, cached_city_coordinates
from services.map_visualization import render_brazil_map


def dashboard_page() -> None:
    st.title("Sistema de Busca de Pessoas Desaparecidas")
    st.caption("Projeto Milk Carton · protótipo acadêmico com IA e revisão humana")
    st.info(
        "Ferramenta de apoio à revisão humana: detecções e OCR não confirmam identidade nem localização. "
        "Utilize somente dados fictícios ou imagens autorizadas."
    )

    session = get_session()
    try:
        total = session.scalar(select(func.count()).select_from(MissingPerson)) or 0
        missing_count = session.scalar(
            select(func.count()).select_from(MissingPerson).where(
                MissingPerson.status.in_(("Desaparecida", "Em aberto"))
            )
        ) or 0
        located_count = session.scalar(
            select(func.count()).select_from(MissingPerson).where(MissingPerson.status == "Localizada")
        ) or 0
        yolo_count = session.scalar(select(func.count()).select_from(ImageAnalysis)) or 0
        ocr_count = session.scalar(select(func.count()).select_from(OCRAnalysis)) or 0
        pending_count = session.scalar(
            select(func.count()).select_from(ImageAnalysis).where(ImageAnalysis.reviewed.is_(False))
        ) or 0
        map_people = list(
            session.scalars(
                select(MissingPerson)
                .where(
                    MissingPerson.status.in_(("Desaparecida", "Em aberto")),
                    MissingPerson.public_map_consent.is_(True),
                )
                .order_by(MissingPerson.public_number)
            ).all()
        )
        hidden_map_count = session.scalar(
            select(func.count())
            .select_from(MissingPerson)
            .where(
                MissingPerson.status.in_(("Desaparecida", "Em aberto")),
                MissingPerson.public_map_consent.is_(False),
            )
        ) or 0
    finally:
        session.close()
    columns = st.columns(5)
    columns[0].metric("Cadastros", total)
    columns[1].metric("Desaparecidas", missing_count)
    columns[2].metric("Localizadas", located_count)
    columns[3].metric("Análises YOLO", yolo_count)
    columns[4].metric("Leituras OCR", ocr_count)
    if pending_count:
        st.info(f"🔎 {pending_count} nova(s) imagem(ns) aguardando revisão humana.")

    st.subheader("Mapa dos cadastros por cidade/UF")
    st.caption(
        "O mapa mostra somente cadastros com autorização de publicação. "
        "Os marcadores representam cidades, não endereços ou locais exatos."
    )
    if not map_people:
        render_brazil_map(
            pd.DataFrame(columns=["lat", "lon", "radius", "cidade", "quantidade"]),
            key="dashboard-brazil-map-v3",
        )
        st.info(
            f"Nenhum cadastro desaparecido está autorizado a aparecer no mapa. "
            f"{hidden_map_count} cadastro(s) permanecem ocultos até a autorização."
        )
    else:
        locations: dict[tuple[str, str], tuple[float, float] | None] = st.session_state.get(
            "map_city_locations", {}
        )
        cities = sorted({(person.city, person.state) for person in map_people})
        st.caption(
            "A busca opcional envia apenas cidade e UF ao OpenStreetMap/Nominatim, "
            "sem nome ou foto. © OpenStreetMap contributors."
        )
        if st.button("Localizar cidades para o mapa inicial"):
            updated_locations = dict(locations)
            try:
                with st.spinner("Localizando cidades..."):
                    for city, state in cities:
                        key = (city, state)
                        if key not in updated_locations:
                            updated_locations[key] = cached_city_coordinates(city, state)
                st.session_state["map_city_locations"] = updated_locations
                locations = updated_locations
            except GeocodingError as exc:
                st.error(str(exc))

        city_counts: dict[tuple[str, str], int] = {}
        map_rows = []
        for person in map_people:
            city_key = (person.city, person.state)
            city_counts[city_key] = city_counts.get(city_key, 0) + 1
            coordinates = locations.get(city_key) or STATE_CAPITALS[person.state]
            map_rows.append(
                {
                    "lat": coordinates[0],
                    "lon": coordinates[1],
                    "icon": f"person-{person.id}",
                    "photo_path": person.image_path,
                    "nome": person.full_name,
                    "cidade": f"{person.city}/{person.state}",
                    "quantidade": city_counts[city_key],
                }
            )
        render_brazil_map(pd.DataFrame(map_rows), key="dashboard-brazil-map-v3")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Cidade": city,
                        "UF": state,
                        "Pessoas desaparecidas autorizadas": count,
                    }
                    for (city, state), count in sorted(city_counts.items())
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Se uma cidade ainda não foi localizada, o marcador fica temporariamente "
            "na capital da UF. Clique no botão acima para buscar os centros das cidades."
        )

    st.subheader("Registros recentes")
    st.caption("ID numérico permanente atribuído aos cadastros, em ordem crescente.")
    dataframe = records_dataframe()
    if dataframe.empty:
        st.info("Ainda não há cadastros. Use o menu para adicionar um registro.")
    else:
        st.dataframe(dataframe.head(10), hide_index=True, width="stretch")
