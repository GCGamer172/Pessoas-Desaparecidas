from datetime import datetime
import json

import streamlit as st

from database.connection import get_session
from pages.records import registration_page
from services.images import delete_image, store_image
from services.records import create_ocr_analysis
from ocr import read_poster, suggest_fields
from services.validation import ValidationError, validate_image


def ocr_page() -> None:
    st.header("Leitura assistida de cartaz (OCR)")
    st.info("O OCR pode errar. Confira e corrija cada campo; nenhum cadastro é salvo automaticamente.")
    uploaded = st.file_uploader("Imagem autorizada do cartaz", type=["jpg", "jpeg", "png"], key="ocr-upload")
    if uploaded is None:
        return
    try:
        content = uploaded.getvalue()
        validate_image(content, uploaded.name)
        if st.button("Extrair texto", type="primary"):
            image_path = store_image(content, uploaded.name)
            try:
                lines = read_poster(content)
                suggestions = suggest_fields(lines)
                session = get_session()
                try:
                    result = create_ocr_analysis(
                        session,
                        image_path,
                        len(lines),
                        json.dumps(suggestions, ensure_ascii=False),
                    )
                finally:
                    session.close()
            except Exception:
                delete_image(image_path)
                raise
            st.session_state["ocr_lines"] = lines
            st.session_state["ocr_suggestions"] = suggestions
            st.session_state["ocr_analysis_id"] = result.id
    except (ValidationError, RuntimeError) as exc:
        st.error(str(exc))
        return

    lines = st.session_state.get("ocr_lines")
    suggestions = st.session_state.get("ocr_suggestions")
    if lines is None or suggestions is None:
        return
    st.subheader("Texto reconhecido")
    st.dataframe(
        [{"Texto": line["text"], "Confiança OCR": f"{float(line['confidence']):.1%}"} for line in lines],
        width="stretch",
    )
    if "ocr_analysis_id" in st.session_state:
        st.caption(f"Leitura OCR registrada: {st.session_state['ocr_analysis_id']}")
    st.subheader("Revise os dados sugeridos")
    with st.form("ocr-review-form"):
        name = st.text_input("Nome completo", suggestions["full_name"])
        age = st.number_input("Idade", 0, 120, int(suggestions["age"]))
        city = st.text_input("Cidade", suggestions["city"])
        state = st.text_input("Estado (UF)", suggestions["state"], max_chars=2)
        location = st.text_input("Última localização", suggestions["last_seen_location"])
        description = st.text_area("Descrição", suggestions["description"], max_chars=2000)
        missing_date_text = st.text_input(
            "Data do desaparecimento (DD/MM/AAAA)",
            suggestions["disappearance_date"],
        )
        approved = st.checkbox("Revisei e confirmei os dados acima.")
        submit = st.form_submit_button("Continuar para cadastro", disabled=not approved)
    if submit:
        try:
            if not missing_date_text.strip():
                raise ValueError("Informe a data do desaparecimento após revisar o cartaz.")
            parsed_date = None
            for date_format in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    parsed_date = datetime.strptime(missing_date_text.strip(), date_format).date()
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                raise ValueError("Data inválida; use DD/MM/AAAA.")
            st.session_state["ocr_registration_defaults"] = {
                "full_name": name,
                "age": int(age),
                "city": city,
                "state": state.upper(),
                "last_seen_location": location,
                "description": description,
                "disappearance_date": parsed_date.isoformat(),
            }
            st.success("Dados revisados. Complete os campos obrigatórios e adicione uma fotografia para salvar.")
            st.session_state["show_ocr_registration"] = True
        except ValueError as exc:
            st.error(str(exc))
    if st.session_state.get("show_ocr_registration"):
        registration_page(st.session_state.get("ocr_registration_defaults"))
