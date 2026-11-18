import json

import streamlit as st

from database.connection import get_session
from database.models import ImageAnalysis
from detector import detect_people, detections_as_dicts, image_to_jpeg_bytes
from services.images import delete_image, load_image, store_generated_image, store_image
from services.records import create_analysis
from services.validation import ValidationError


def analysis_page() -> None:
    st.header("Analisar imagem com YOLO")
    st.info(
        "A detecção identifica apenas a classe genérica “pessoa”. Não identifica indivíduos, "
        "não confirma identidade ou localização e exige revisão humana."
    )
    uploaded = st.file_uploader("Imagem autorizada para análise", type=["jpg", "jpeg", "png"], key="yolo-upload")
    if uploaded is not None and st.button("Executar detecção", type="primary"):
        source_path = None
        annotated_path = None
        try:
            content = uploaded.getvalue()
            source_path = store_image(content, uploaded.name)
            source_image = load_image(source_path)
            annotated, detections = detect_people(source_image)
            annotated_bytes = image_to_jpeg_bytes(annotated)
            annotated_path = store_generated_image(annotated_bytes)
            session = get_session()
            try:
                result = create_analysis(
                    session,
                    source_path,
                    annotated_path,
                    len(detections),
                    json.dumps(detections_as_dicts(detections), ensure_ascii=False),
                )
            finally:
                session.close()
            st.image(annotated, caption="Resultado de detecção — requer revisão humana", width="stretch")
            st.metric("Pessoas detectadas", len(detections))
            st.dataframe(
                [
                    {"Confiança": f"{d.confidence:.1%}", "Caixa (x1, y1, x2, y2)": (d.x1, d.y1, d.x2, d.y2)}
                    for d in detections
                ],
                width="stretch",
            )
            st.success(f"Análise {result.id} salva e aguardando revisão humana.")
        except (ValidationError, OSError, ValueError, RuntimeError) as exc:
            if source_path:
                try:
                    delete_image(source_path)
                except (FileNotFoundError, ValueError):
                    pass
            if annotated_path:
                try:
                    delete_image(annotated_path)
                except (FileNotFoundError, ValueError):
                    pass
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Falha ao concluir a análise: {exc}")

    st.subheader("Imagens aguardando revisão")
    session = get_session()
    try:
        pending = list(
            session.query(ImageAnalysis).filter(ImageAnalysis.reviewed.is_(False)).order_by(ImageAnalysis.created_at.desc()).all()
        )
        if not pending:
            st.info("Não há novas imagens aguardando revisão.")
        for item in pending:
            with st.expander(f"Análise {item.id[:8]} · {item.created_at:%d/%m/%Y %H:%M} · {item.detected_people} pessoa(s) detectada(s)"):
                st.image(load_image(item.annotated_image_path), width="stretch")
                st.json(json.loads(item.results_json))
                acknowledged = st.checkbox("Revisei esta análise; ela não confirma identidade ou localização.", key=f"review-{item.id}")
                if st.button("Concluir revisão humana", key=f"review-btn-{item.id}", disabled=not acknowledged):
                    item.reviewed = True
                    session.commit()
                    st.rerun()
    finally:
        session.close()
