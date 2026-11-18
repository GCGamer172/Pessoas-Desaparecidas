from datetime import date, datetime
import pandas as pd
import streamlit as st

from cartaz import generate_poster, poster_pdf_bytes, poster_png_bytes, safe_poster_filename
from database.connection import get_session
from database.models import MissingPerson
from services.images import delete_image, load_image, store_image
from services.records import create_person, delete_person, search_people, update_person
from services.validation import (
    ALLOWED_STATES,
    ALLOWED_STATUSES,
    ValidationError,
    validate_person_fields,
    validate_status_change,
)


def _person_form(key: str, person: MissingPerson | None = None, defaults: dict | None = None) -> None:
    defaults = defaults or {}
    with st.form(key, clear_on_submit=person is None):
        full_name = st.text_input("Nome completo *", value=person.full_name if person else defaults.get("full_name", ""))
        age = st.number_input("Idade *", min_value=0, max_value=120, value=person.age if person else int(defaults.get("age", 0)), step=1)
        city = st.text_input("Cidade *", value=person.city if person else defaults.get("city", ""))
        state_choices = ["Selecione o estado"] + sorted(ALLOWED_STATES)
        current_state = person.state if person else defaults.get("state", "")
        state_index = state_choices.index(current_state) if current_state in state_choices else 0
        state = st.selectbox("Estado (UF) *", state_choices, index=state_index)
        location = st.text_input(
            "Última localização conhecida *",
            value=person.last_seen_location if person else defaults.get("last_seen_location", ""),
        )
        st.caption("Para marcar o ponto exato no mapa, informe as coordenadas do local visto.")
        latitude_col, longitude_col = st.columns(2)
        latitude = latitude_col.number_input(
            "Latitude (opcional)",
            min_value=-35.0,
            max_value=6.0,
            value=person.last_seen_latitude if person else None,
            step=0.00001,
            format="%.5f",
            help="Coordenada sul/norte dentro do Brasil.",
        )
        longitude = longitude_col.number_input(
            "Longitude (opcional)",
            min_value=-75.0,
            max_value=-34.0,
            value=person.last_seen_longitude if person else None,
            step=0.00001,
            format="%.5f",
            help="Coordenada oeste/leste dentro do Brasil.",
        )
        description = st.text_area(
            "Descrição",
            value=person.description if person else defaults.get("description", ""),
            max_chars=2000,
            help="Características gerais da roupa ou contexto da imagem; não use para identificação biométrica.",
        )
        default_date = person.disappearance_date if person else date.today()
        date_value = defaults.get("disappearance_date", "")
        if isinstance(date_value, str) and date_value:
            try:
                default_date = date.fromisoformat(date_value)
            except ValueError:
                pass
            for fmt in ("%d/%m/%Y", "%d-%m-%Y"):
                try:
                    default_date = datetime.strptime(date_value, fmt).date()
                    break
                except ValueError:
                    continue
        disappearance_date = st.date_input("Data do desaparecimento *", value=default_date, max_value=date.today())
        status_choices = sorted(ALLOWED_STATUSES)
        current_status = person.status if person else defaults.get("status", "Desaparecida")
        status_index = status_choices.index(current_status) if current_status in status_choices else 0
        status = st.selectbox("Status *", status_choices, index=status_index)
        authorized_status = st.checkbox(
            "Confirmo que tenho autorização para registrar ou alterar esta situação."
        )
        public_map_consent = st.checkbox(
            "Autorizo publicar no mapa a foto, o nome, a idade, a cidade/UF, "
            "a data e o último local informado, incluindo coordenadas precisas se preenchidas.",
            value=person.public_map_consent if person else False,
            help="Coordenadas preenchidas serão mostradas como um ponto preciso no mapa. "
            "Deixe desmarcado para manter o cadastro fora do mapa.",
        )
        uploaded = st.file_uploader("Fotografia autorizada *", type=["jpg", "jpeg", "png"])
        if person:
            st.caption("Envie uma nova imagem somente se desejar substituir a fotografia atual.")
        submitted = st.form_submit_button("Salvar cadastro", type="primary")

    if not submitted:
        return
    session = get_session()
    try:
        fields = validate_person_fields(
            full_name,
            int(age),
            city,
            state,
            location,
            disappearance_date,
            status,
            description,
            latitude,
            longitude,
        )
        fields["public_map_consent"] = public_map_consent
        validate_status_change(person.status if person else None, status, authorized_status)
        image_path = None
        if uploaded is not None:
            image_path = store_image(uploaded.getvalue(), uploaded.name)
        elif person is None:
            raise ValidationError("Selecione uma fotografia para o cadastro.")

        if person:
            old_path = person.image_path
            update_person(session, person, fields, image_path)
            if image_path and old_path != image_path:
                delete_image(old_path)
            st.success("Cadastro atualizado.")
        else:
            create_person(session, fields, image_path)
            st.success("Cadastro salvo.")
        st.rerun()
    except (ValidationError, OSError, ValueError) as exc:
        session.rollback()
        st.error(str(exc))
    except Exception as exc:
        session.rollback()
        st.error(f"Não foi possível salvar o cadastro: {exc}")
    finally:
        session.close()


def registration_page(defaults: dict | None = None) -> None:
    st.header("Cadastrar pessoa")
    st.caption("Use somente fotografias próprias ou enviadas com autorização.")
    _person_form("new-person-form", defaults=defaults)


def records_page() -> None:
    st.header("Galeria Milk Carton")
    st.caption("Cartazes para divulgação responsável. Não afirmam identidade nem localização.")
    query = st.text_input("Pesquisar por nome ou cidade")
    status = st.selectbox("Filtrar por status", ["Todos", *sorted(ALLOWED_STATUSES)])
    session = get_session()
    try:
        people = search_people(session, query, None if status == "Todos" else status)
        if not people:
            st.info("Nenhum cadastro encontrado.")
            return
        for person in people:
            with st.container(border=True):
                left, right = st.columns([1, 3], vertical_alignment="top")
                photo = load_image(person.image_path)
                with left:
                    st.image(photo, width=180)
                with right:
                    st.subheader(person.full_name)
                    status_color = "green" if person.status == "Localizada" else "red"
                    st.badge(person.status, color=status_color)
                    age_col, city_col, date_col = st.columns(3)
                    age_col.markdown(f"**Idade**  \n{person.age} anos")
                    city_col.markdown(f"**Cidade/UF**  \n{person.city}/{person.state}")
                    date_col.markdown(
                        f"**Data**  \n{person.disappearance_date.strftime('%d/%m/%Y')}"
                    )
                    st.markdown(f"**Último local visto:** {person.last_seen_location}")
                    if person.description:
                        st.markdown(f"**Descrição:** {person.description}")

                    poster = generate_poster(
                        photo,
                        full_name=person.full_name,
                        age=person.age,
                        city=person.city,
                        state=person.state,
                        disappearance_date=person.disappearance_date,
                        last_seen_location=person.last_seen_location,
                        description=person.description,
                        status=person.status,
                    )
                    filename = safe_poster_filename(person.full_name)
                    png_col, pdf_col = st.columns(2)
                    png_col.download_button(
                        "Baixar cartaz PNG",
                        poster_png_bytes(poster),
                        file_name=f"{filename}.png",
                        mime="image/png",
                        key=f"poster-png-{person.id}",
                        width="stretch",
                    )
                    pdf_col.download_button(
                        "Baixar cartaz PDF",
                        poster_pdf_bytes(poster),
                        file_name=f"{filename}.pdf",
                        mime="application/pdf",
                        key=f"poster-pdf-{person.id}",
                        width="stretch",
                    )
                    with st.expander("Editar cadastro"):
                        with st.form(f"edit-form-{person.id}"):
                            name = st.text_input("Nome completo", person.full_name, key=f"name-{person.id}")
                            age = st.number_input("Idade", 0, 120, person.age, key=f"age-{person.id}")
                            city = st.text_input("Cidade", person.city, key=f"city-{person.id}")
                            states = sorted(ALLOWED_STATES)
                            state = st.selectbox("Estado", states, index=states.index(person.state), key=f"state-{person.id}")
                            location = st.text_input("Último local visto", person.last_seen_location, key=f"location-{person.id}")
                            latitude_col, longitude_col = st.columns(2)
                            latitude = latitude_col.number_input(
                                "Latitude (opcional)",
                                min_value=-35.0,
                                max_value=6.0,
                                value=person.last_seen_latitude,
                                step=0.00001,
                                format="%.5f",
                                key=f"latitude-{person.id}",
                            )
                            longitude = longitude_col.number_input(
                                "Longitude (opcional)",
                                min_value=-75.0,
                                max_value=-34.0,
                                value=person.last_seen_longitude,
                                step=0.00001,
                                format="%.5f",
                                key=f"longitude-{person.id}",
                            )
                            description = st.text_area("Descrição", person.description, max_chars=2000, key=f"description-{person.id}")
                            missing_date = st.date_input("Data do desaparecimento", person.disappearance_date, max_value=date.today(), key=f"date-{person.id}")
                            statuses = sorted(ALLOWED_STATUSES)
                            new_status = st.selectbox(
                                "Situação",
                                statuses,
                                index=statuses.index(person.status) if person.status in statuses else 0,
                                key=f"status-{person.id}",
                            )
                            authorized_status = st.checkbox(
                                "Confirmo autorização para registrar ou alterar esta situação.",
                                key=f"authorized-status-{person.id}",
                            )
                            public_map_consent = st.checkbox(
                                "Autorizo publicar os dados, a foto e as coordenadas precisas no mapa.",
                                value=person.public_map_consent,
                                key=f"map-consent-{person.id}",
                                help="As coordenadas preenchidas serão exibidas como ponto preciso.",
                            )
                            new_photo = st.file_uploader("Substituir fotografia (opcional)", type=["jpg", "jpeg", "png"], key=f"photo-{person.id}")
                            save = st.form_submit_button("Atualizar cadastro")
                        if save:
                            try:
                                fields = validate_person_fields(
                                    name,
                                    int(age),
                                    city,
                                    state,
                                    location,
                                    missing_date,
                                    new_status,
                                    description,
                                    latitude,
                                    longitude,
                                )
                                fields["public_map_consent"] = public_map_consent
                                validate_status_change(person.status, new_status, authorized_status)
                                new_path = store_image(new_photo.getvalue(), new_photo.name) if new_photo else None
                                old_path = person.image_path
                                update_person(session, person, fields, new_path)
                                if new_path:
                                    delete_image(old_path)
                                st.success("Cadastro atualizado.")
                                st.rerun()
                            except (ValidationError, OSError, ValueError) as exc:
                                session.rollback()
                                st.error(str(exc))
                    with st.expander("Excluir cadastro"):
                        confirm_delete = st.checkbox(
                            f"Confirmo a exclusão do registro de {person.full_name}.",
                            key=f"confirm-delete-{person.id}",
                        )
                        if st.button(
                            "Excluir permanentemente",
                            key=f"delete-{person.id}",
                            type="secondary",
                            disabled=not confirm_delete,
                        ):
                            try:
                                image_paths = [person.image_path]
                                image_paths.extend(
                                    path
                                    for analysis in person.analyses
                                    for path in (analysis.image_path, analysis.annotated_image_path)
                                )
                                delete_person(session, person)
                                for path in set(image_paths):
                                    try:
                                        delete_image(path)
                                    except FileNotFoundError:
                                        pass
                                st.success("Cadastro excluído.")
                                st.rerun()
                            except Exception as exc:
                                session.rollback()
                                st.error(f"Não foi possível excluir o cadastro: {exc}")
    finally:
        session.close()


def records_dataframe() -> pd.DataFrame:
    session = get_session()
    try:
        people = search_people(session)
        people.sort(key=lambda item: (item.public_number is None, item.public_number or 0))
        return pd.DataFrame(
            [
                {
                    "ID": item.public_number,
                    "Nome": item.full_name,
                    "Idade": item.age,
                    "Cidade": item.city,
                    "UF": item.state,
                    "Última localização": item.last_seen_location,
                    "Descrição": item.description,
                    "Data": item.disappearance_date.strftime("%d/%m/%Y"),
                    "Status": item.status,
                }
                for item in people
            ]
        )
    finally:
        session.close()
