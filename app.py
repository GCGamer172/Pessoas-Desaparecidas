import streamlit as st

from database import initialize_database
from pages.analysis import analysis_page
from pages.dashboard import dashboard_page
from pages.map import map_page
from pages.ocr_page import ocr_page
from pages.records import records_page, registration_page


st.set_page_config(
    page_title="Sistema de Busca de Pessoas Desaparecidas",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f5f7fb; }
    [data-testid="stSidebar"] { background: #10243a; }
    [data-testid="stSidebar"] * { color: #f3f6fa; }
    [data-testid="stMain"] h1 {
      font-size: clamp(1.75rem, 2.8vw, 2.5rem);
      line-height: 1.2;
    }
    div[data-testid="stMetric"] {
      background: white; padding: 12px; border-radius: 12px;
      border: 1px solid #e4e9f0;
    }
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] p {
      font-size: 0.9rem;
      white-space: normal;
      overflow: visible;
      text-overflow: clip;
    }
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_database()
with st.sidebar:
    st.title("🥛 Milk Carton")
    st.caption("Sistema de busca · protótipo acadêmico")
    page = st.radio(
        "Navegação",
        [
            "Painel inicial",
            "Mapa do Brasil",
            "Cadastrar pessoa",
            "Galeria Milk Carton",
            "Analisar imagem (YOLO)",
            "Ler cartaz (OCR)",
        ],
        index=1,
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Uso responsável · Revisão humana obrigatória")

if page == "Painel inicial":
    dashboard_page()
elif page == "Mapa do Brasil":
    map_page()
elif page == "Cadastrar pessoa":
    registration_page()
elif page == "Galeria Milk Carton":
    records_page()
elif page == "Analisar imagem (YOLO)":
    analysis_page()
else:
    ocr_page()
