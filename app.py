"""
CRM Influence Mon Kit Solaire ☀️
3 onglets : Prospection | À Contacter | Suivi Campagnes
"""

import os
import sys
import re
import random
import html as html_mod
import streamlit as st
import pandas as pd
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from streamlit_gsheets import GSheetsConnection

from engine_youtube_scraper import (
    create_driver, search_channels, scrape_channel_full, fmt,
)
from skill_influence_scoring import (
    is_excluded, classify, compute_score,
    MIN_AVG_VIEWS, MIN_SCORE_DISPLAY,
)
from skill_contact_finder import find_contacts, format_contact_tags
from skill_email_generator import generate_email, build_mailto_link
from skill_live_updater import bulk_rescrape

# ============================================================
# GOOGLE SHEETS CONFIG
# ============================================================

GSHEET_URL = "https://docs.google.com/spreadsheets/d/14EIAPzCCR7A9gpxFr7jdFup9An_BFgsKhjaelxpr1yk/edit"

# ============================================================
# CONFIG
# ============================================================

DB_FILE = os.path.join(os.path.dirname(__file__), "influenceurs_db.csv")
CRM_FILE = os.path.join(os.path.dirname(__file__), "crm_database.csv")

DEFAULT_KEYWORDS = [
    "rénovation maison",
    "bricolage",
    "autoconsommation",
    "écologique",
    "rénover soi même",
]

STATUTS = ["À contacter", "Contacté", "En négociation", "Kit envoyé", "Terminé"]

DB_COLUMNS = [
    "name", "url", "handle", "subscribers", "avg_views",
    "latest_video", "latest_published", "views_list", "contact",
    "category", "score", "favori", "statut", "date_ajout", "ignored",
    "email", "social_links", "mail_manual",
]

CRM_COLUMNS = [
    "alias", "url", "statut", "agence", "chaine_yt", "date_fin_contrat",
    "infos", "mail", "nom_contact", "subscribers", "avg_views",
    "nb_videos", "views_list", "likes", "commentaires",
]

# Palette Mon Kit Solaire — Fond lumineux crème + Accents solaires vifs
ACCENT = "#FF6B35"
ORANGE = "#FF8C42"
GOLD = "#FFBE0B"
GREEN_MINT = "#06D6A0"
BLUE_AZUR = "#118AB2"
PINK = "#EF476F"
LAVENDER = "#7B68EE"
BG = "#FFF8F0"
BG_CARD = "#FFFFFF"
BG_CARD_LIGHT = "#FFF0E0"
BORDER = "#E8DDD0"
TEXT = "#2D2A26"
TEXT_MUTED = "#7A7067"
WHITE = "#FFFFFF"

# Citations solaires
CITATIONS = [
    "Une pépite par jour éloigne la grisaille ! ☀️",
    "Le soleil brille pour ceux qui cherchent ! 🔍✨",
    "Chaque influenceur est un rayon de soleil pour votre marque ! 🌞",
    "L'énergie solaire, c'est aussi l'énergie des bonnes rencontres ! ⚡",
    "Aujourd'hui est un jour parfait pour trouver LA pépite ! 💎☀️",
    "Le succès se construit un partenariat à la fois ! 🤝🌟",
    "Votre prochain ambassadeur se cache peut-être ici ! 🎯✨",
]

# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="CRM Influence Mon Kit Solaire",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# ONGLET ACTIF — pour masquer la sidebar hors Prospection
# ============================================================

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "🔍 Recherche"

# CSS dynamique : sidebar cachée hors Recherche
# On lit nav_radio (mis à jour par Streamlit AVANT le rerun) pour éviter le décalage
current_tab = st.session_state.get("nav_radio", st.session_state.get("active_tab", "🔍 Recherche"))
sidebar_css = ""
if current_tab not in ("🔍 Recherche", "🔍 Prospection"):
    sidebar_css = """
    section[data-testid="stSidebar"] {
        display: none !important;
        width: 0 !important;
        min-width: 0 !important;
    }
    .main .block-container {
        max-width: 100% !important;
        padding-left: 2rem !important;
    }
    """

st.markdown(f"""
<style>
    /* ========= FOND ANTHRACITE CHAUD ========= */
    .stApp {{
        background-color: {BG} !important;
        color: {TEXT};
    }}
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #FFF4E8 0%, #FFF8F0 100%);
        border-right: 1px solid {BORDER};
    }}
    {sidebar_css}

    /* ========= TITRES — GROS, CENTRÉS, ORANGE ========= */
    .main-title {{
        text-align: center;
        font-size: 3.2rem;
        font-weight: 900;
        color: {ACCENT};
        margin-bottom: 4px;
        letter-spacing: -0.5px;
        padding-top: 50px;
    }}
    .main-subtitle {{
        text-align: center;
        font-size: 1rem;
        color: {TEXT_MUTED};
        margin-bottom: 20px;
        font-weight: 500;
    }}
    .section-title {{
        text-align: center;
        font-size: 1.5rem;
        font-weight: 800;
        color: {ACCENT};
        margin: 24px 0 12px 0;
    }}
    .quote-box {{
        text-align: center;
        font-size: 1.05rem;
        font-style: italic;
        color: #B45309;
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 14px 24px;
        margin: 0 0 18px 0;
    }}

    /* ========= KPI BULLES — RONDS COLORÉS ========= */
    .kpi-row {{
        display: flex;
        justify-content: center;
        gap: 24px;
        flex-wrap: wrap;
        margin: 16px 0 24px 0;
    }}
    .kpi-bubble {{
        width: 140px;
        height: 140px;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 6px 30px rgba(0,0,0,0.12);
        transition: transform 0.2s;
        cursor: default;
    }}
    .kpi-bubble:hover {{
        transform: scale(1.1);
    }}
    .kpi-value {{
        font-size: 1.6rem;
        font-weight: 900;
        color: {WHITE};
        line-height: 1.1;
    }}
    .kpi-label {{
        font-size: 0.7rem;
        font-weight: 600;
        color: rgba(255,255,255,0.85);
        text-align: center;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ========= METRICS CLASSIQUES ========= */
    div[data-testid="stMetric"] {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 18px 14px;
        box-shadow: 0 3px 15px rgba(0,0,0,0.06);
        text-align: center;
    }}
    div[data-testid="stMetric"] label {{
        color: {TEXT_MUTED} !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: {ACCENT} !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
    }}

    /* ========= BOUTONS ORANGE ========= */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {ACCENT} 0%, {ORANGE} 100%) !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        padding: 12px 24px !important;
        color: {WHITE} !important;
        box-shadow: 0 4px 18px rgba(255,107,53,0.3) !important;
    }}
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {{
        box-shadow: 0 6px 28px rgba(255,107,53,0.4) !important;
        transform: translateY(-1px) !important;
    }}

    /* ========= LIENS ========= */
    a {{ color: {ORANGE} !important; text-decoration: none !important; font-weight: 600; }}
    a:hover {{ color: {GOLD} !important; }}

    /* ========= TABLEAUX ARRONDIS ========= */
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {{
        border-radius: 16px !important;
        overflow: hidden;
        border: 1px solid {BORDER};
        box-shadow: 0 3px 15px rgba(0,0,0,0.06);
    }}

    /* ========= HTML TABLES CENTRÉES ========= */
    .styled-table {{
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid {BORDER};
        box-shadow: 0 3px 15px rgba(0,0,0,0.06);
        background: {BG_CARD};
    }}
    .styled-table th {{
        background: linear-gradient(135deg, {ACCENT} 0%, {ORANGE} 100%);
        color: {WHITE};
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
        padding: 12px 10px;
        border-bottom: 2px solid {ORANGE};
    }}
    .styled-table td {{
        text-align: center;
        padding: 10px 10px;
        color: {TEXT};
        font-size: 0.88rem;
        border-bottom: 1px solid {BORDER};
        vertical-align: middle;
    }}
    .styled-table tr:last-child td {{
        border-bottom: none;
    }}
    .styled-table tr:hover td {{
        background: {BG_CARD_LIGHT};
    }}
    .styled-table td.infos-cell {{
        text-align: left;
        white-space: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
        max-width: 350px;
        line-height: 1.5;
    }}
    .styled-table th, .styled-table td {{
        white-space: nowrap;
    }}
    .styled-table td.infos-cell,
    .styled-table td.wrap-cell {{
        white-space: normal;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }}
    .table-scroll-wrapper {{
        max-height: 420px;
        overflow-y: auto !important;
        overflow-x: auto !important;
        border-radius: 16px;
        border: 1px solid {BORDER};
        box-shadow: 0 3px 15px rgba(0,0,0,0.06);
        position: relative;
    }}
    /* Force Streamlit markdown wrappers to not clip overflow */
    .stMarkdown:has(.table-scroll-wrapper) {{
        overflow: visible !important;
    }}
    .stMarkdown:has(.table-scroll-wrapper) > div {{
        overflow: visible !important;
    }}
    .table-scroll-wrapper .styled-table {{
        border: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        overflow: visible !important;
        table-layout: auto;
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
    }}
    .table-scroll-wrapper .styled-table thead {{
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 10;
    }}
    .table-scroll-wrapper .styled-table thead th {{
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 10;
        background: linear-gradient(135deg, {ACCENT} 0%, {ORANGE} 100%) !important;
        color: {WHITE} !important;
    }}

    /* ========= CHANNEL ROW ========= */
    .ch-row {{
        display: flex;
        align-items: center;
        gap: 12px;
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 14px 18px;
        margin-bottom: 4px;
        min-height: 62px;
        transition: all 0.2s;
    }}
    .ch-row:hover {{
        border-color: {ACCENT};
        box-shadow: 0 4px 20px rgba(255,107,53,0.1);
    }}

    .ch-name {{ flex: 2.8; min-width: 0; overflow: hidden; }}
    .ch-name a {{
        font-size: 1.05rem; font-weight: 700; color: {TEXT} !important;
        display: block; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis;
    }}
    .ch-video {{
        font-size: 0.73rem; color: {TEXT_MUTED};
        white-space: nowrap; overflow: hidden;
        text-overflow: ellipsis; margin-top: 2px;
    }}

    .ch-stat {{ flex: 0.9; text-align: center; white-space: nowrap; }}
    .ch-stat .val {{ font-size: 1rem; font-weight: 700; color: {TEXT}; display: block; }}
    .ch-stat .lbl {{ font-size: 0.68rem; color: {TEXT_MUTED}; }}

    /* ========= BADGES ========= */
    .score-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.82rem;
        white-space: nowrap;
    }}
    .score-high {{ background: #D1FAE5; color: #065F46; box-shadow: 0 0 8px rgba(6,214,160,0.2); }}
    .score-mid  {{ background: #FEF3C7; color: #92400E; box-shadow: 0 0 8px rgba(251,191,36,0.2); }}
    .score-low  {{ background: #FEE2E2; color: #991B1B; box-shadow: 0 0 8px rgba(248,113,113,0.2); }}

    .cat-pill {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 600;
        background: {BG_CARD_LIGHT};
        color: {TEXT_MUTED};
        border: 1px solid {BORDER};
    }}

    .active-badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.7rem;
        font-weight: 700;
        background: #FFEDD5;
        color: #C2410C;
        margin-left: 4px;
    }}

    .contact-text {{ flex: 0.8; color: {TEXT_MUTED}; font-size: 0.75rem; text-align: center; white-space: nowrap; }}
    .ch-tags {{ flex: 1.6; display: flex; align-items: center; gap: 6px; justify-content: center; }}

    /* ========= NAVIGATION RADIO (style onglets plats) ========= */
    div[data-testid="stRadio"] > div {{
        display: flex !important;
        justify-content: center !important;
        gap: 0 !important;
        border-bottom: 2px solid {BORDER} !important;
    }}
    div[data-testid="stRadio"] > div > label {{
        background: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        border-radius: 0 !important;
        padding: 12px 32px !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        cursor: pointer !important;
        transition: all 0.2s !important;
        color: {TEXT_MUTED} !important;
        margin-bottom: -2px !important;
    }}
    div[data-testid="stRadio"] > div > label:hover {{
        color: {ACCENT} !important;
        border-bottom-color: {ACCENT} !important;
    }}
    div[data-testid="stRadio"] > div > label[data-checked="true"],
    div[data-testid="stRadio"] > div > label:has(input:checked) {{
        background: transparent !important;
        border-bottom: 3px solid {ACCENT} !important;
        color: {ACCENT} !important;
        font-weight: 800 !important;
    }}
    div[data-testid="stRadio"] label span[data-testid="stMarkdownContainer"] {{
        color: inherit !important;
    }}
    /* Hide radio circles */
    div[data-testid="stRadio"] input[type="radio"] {{
        display: none !important;
    }}

    /* ========= SIDEBAR ========= */
    .stTextArea textarea {{ background-color: {BG_CARD}; border-color: {BORDER}; color: {TEXT}; border-radius: 10px; }}
    .stNumberInput input {{ background-color: {BG_CARD}; border-color: {BORDER}; color: {TEXT}; border-radius: 10px; }}

    /* ========= BOUTONS EMOJI (coeur/poubelle) — pas de fond ========= */
    .stButton > button {{
        background: transparent !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        padding: 4px 10px !important;
        min-height: 0 !important;
        line-height: 1.4 !important;
    }}
    .stButton > button:hover {{
        border-color: {ACCENT} !important;
        background: {BG_CARD_LIGHT} !important;
    }}
    /* Re-style primary buttons (override above) */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {ACCENT} 0%, {ORANGE} 100%) !important;
        border: none !important;
        padding: 12px 24px !important;
    }}

    hr {{ border-color: {BORDER} !important; margin: 8px 0 !important; }}
    .block-container {{ padding-top: 0.5rem; }}

    /* ========= TAILLES POLICE GLOBALES ========= */
    .stApp .stMarkdown p, .stApp .stMarkdown > div > p {{
        font-size: 1.05rem;
    }}
    /* Exclure les cards agences du font override */
    .agence-card, .agence-card * {{
        font-size: unset;
    }}
    .stApp .stTextInput label, .stApp .stSelectbox label, .stApp .stNumberInput label {{
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }}
    .stApp .stExpander summary span {{
        font-size: 1.05rem !important;
        font-weight: 700 !important;
    }}
    .main-subtitle {{
        font-size: 1.15rem !important;
    }}
    .section-title {{
        font-size: 1.6rem !important;
    }}
    div[data-testid="stMetric"] label {{
        font-size: 0.9rem !important;
    }}

    /* ========= YT ICON ========= */
    .yt-ico {{
        display: flex; align-items: center; justify-content: center;
        width: 28px; height: 20px;
        background: #ff0000; border-radius: 4px;
        flex-shrink: 0; position: relative;
    }}
    .yt-ico::after {{
        content: "";
        border-left: 8px solid #fff;
        border-top: 5px solid transparent;
        border-bottom: 5px solid transparent;
    }}

    /* ========= CRM SECTION HEADERS ========= */
    .crm-section {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 16px 20px;
        margin: 16px 0 10px 0;
        box-shadow: 0 3px 15px rgba(0,0,0,0.06);
        text-align: center;
    }}
    .crm-section h4 {{
        margin: 0;
        color: {TEXT};
        font-size: 1.15rem;
        font-weight: 800;
    }}

    /* ========= ALERTE SECTION ========= */
    .alert-section {{
        background: linear-gradient(135deg, #FFF1F0 0%, #FFE4E1 100%);
        border: 1px solid #FFB3AA;
        border-left: 5px solid {ACCENT};
        border-radius: 16px;
        padding: 16px 20px;
        margin: 10px 0 16px 0;
        text-align: center;
        box-shadow: 0 3px 15px rgba(255,107,53,0.08);
    }}
    .alert-section h4 {{ margin: 0; color: #C0392B; font-size: 1.1rem; font-weight: 800; }}

    /* ========= AGENCE CARDS ========= */
    .agence-card {{
        background: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 22px 24px;
        min-height: 160px;
        box-shadow: 0 3px 18px rgba(0,0,0,0.06);
        transition: all 0.2s;
        text-align: center;
    }}
    .agence-card:hover {{
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 10px 40px rgba(0,0,0,0.1), 0 0 15px rgba(255,140,66,0.08);
    }}
    .agence-card h3 {{
        margin: 0 0 6px 0;
        font-size: 1.2rem;
        font-weight: 900;
    }}
    .agence-contact {{
        font-size: 0.85rem !important;
        color: {TEXT_MUTED};
        margin: 4px 0;
        line-height: 1.5;
    }}
    .agence-contact strong {{ color: {TEXT}; font-size: 0.85rem !important; }}
    .agence-contact a {{ font-weight: 600; font-size: 0.85rem !important; }}
    .agence-influencers {{
        margin: 12px 0 0 0;
        padding: 0;
        list-style: none;
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        justify-content: center;
    }}
    .agence-influencers li {{
        display: inline-block;
        background: {BG_CARD_LIGHT};
        border: 1px solid {BORDER};
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem !important;
        font-weight: 600;
        color: {TEXT};
    }}

    /* ========= PODIUM CARDS ========= */
    .podium-card {{
        border-radius: 18px;
        padding: 20px 14px;
        text-align: center;
        box-shadow: 0 6px 30px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }}
    .podium-card:hover {{ transform: translateY(-6px) scale(1.03); box-shadow: 0 12px 45px rgba(0,0,0,0.35); }}
    .podium-rank {{ font-size: 2.2rem; font-weight: 900; margin-bottom: 4px; }}
    .podium-name {{
        font-size: 0.92rem; font-weight: 700;
        margin-bottom: 8px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }}
    .podium-stat {{
        font-size: 0.8rem; line-height: 1.6;
    }}
    .podium-stat strong {{
        font-size: 1.15rem; display: block;
    }}
</style>
""", unsafe_allow_html=True)


# ============================================================
# BASE DE DONNEES
# ============================================================

def load_db():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, dtype=str).fillna("")
        for col in DB_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=DB_COLUMNS)


def save_db(df):
    df.to_csv(DB_FILE, index=False)


def load_crm():
    if os.path.exists(CRM_FILE):
        df = pd.read_csv(CRM_FILE, dtype=str).fillna("")
        for col in CRM_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=CRM_COLUMNS)


def save_crm(df):
    df.to_csv(CRM_FILE, index=False)


def add_to_db(channel_data):
    df = load_db()
    url = channel_data.get("url", "")
    if url and url in df["url"].values:
        return False
    row = {col: "" for col in DB_COLUMNS}
    row.update({
        "name": channel_data.get("name", ""),
        "url": url,
        "handle": channel_data.get("handle", ""),
        "subscribers": str(channel_data.get("subscribers", "")),
        "avg_views": str(channel_data.get("avg_views", "")),
        "latest_video": channel_data.get("latest_video", ""),
        "latest_published": channel_data.get("latest_published", ""),
        "views_list": str(channel_data.get("views_list", [])),
        "contact": ", ".join(channel_data.get("contact", [])) if isinstance(channel_data.get("contact"), list) else str(channel_data.get("contact", "")),
        "category": channel_data.get("category", ""),
        "score": str(channel_data.get("score", "")),
        "favori": "1",
        "statut": "À contacter",
        "date_ajout": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ignored": "0",
        "email": channel_data.get("email", ""),
        "social_links": str(channel_data.get("social_links", "{}")),
        "mail_manual": "",
    })
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_db(df)
    return True


def push_to_crm(channel_data):
    crm = load_crm()
    url = channel_data.get("url", "")
    if url and url in crm["url"].values:
        return False
    row = {col: "" for col in CRM_COLUMNS}
    # Priorité : email trouvé par le contact finder > ancien tag "Mail"
    mail = channel_data.get("email", "")
    if not mail:
        contact_list = channel_data.get("contact", [])
        if isinstance(contact_list, str):
            contact_list = [c.strip() for c in contact_list.split(",") if c.strip()]
        for c in contact_list:
            if "@" in c:
                mail = c
                break
    row.update({
        "alias": channel_data.get("handle", "") or channel_data.get("name", ""),
        "url": url,
        "statut": "À contacter",
        "agence": "",
        "chaine_yt": channel_data.get("name", ""),
        "date_fin_contrat": "",
        "infos": "",
        "mail": mail,
        "nom_contact": "",
        "subscribers": str(channel_data.get("subscribers", "")),
        "avg_views": str(channel_data.get("avg_views", "")),
        "nb_videos": str(len(channel_data.get("views_list", []))),
        "views_list": str(channel_data.get("views_list", [])),
        "likes": "",
        "commentaires": "",
    })
    crm = pd.concat([crm, pd.DataFrame([row])], ignore_index=True)
    save_crm(crm)
    return True


def update_field(url, field, value):
    df = load_db()
    mask = df["url"] == url
    if mask.any():
        df.loc[mask, field] = value
        save_db(df)


# ============================================================
# SCRAPING
# ============================================================

def run_search(keywords, max_per_kw, progress_callback):
    results = []
    all_channels = {}
    driver = create_driver()
    try:
        progress_callback(0.1, "Recherche de chaînes...")
        for i, kw in enumerate(keywords):
            progress_callback(
                0.1 + 0.3 * (i / len(keywords)),
                f"Recherche : '{kw}'..."
            )
            for ch in search_channels(driver, kw, max_results=max_per_kw):
                if is_excluded(ch["name"]):
                    continue
                url = ch["url"]
                if url not in all_channels:
                    all_channels[url] = {
                        "name": ch["name"], "url": url,
                        "handle": ch.get("handle", ""),
                        "keywords": [kw],
                    }
                else:
                    all_channels[url]["keywords"].append(kw)

        total = len(all_channels)
        for i, (url, ch) in enumerate(all_channels.items()):
            progress_callback(
                0.4 + 0.55 * (i / max(total, 1)),
                f"Analyse {i+1}/{total} : {ch['name'][:30]}..."
            )
            data = scrape_channel_full(driver, url)
            ch.update(data)
            ch["category"] = classify(ch.get("subscribers"))
            ch["score"] = compute_score(ch)
            # Recherche approfondie de contacts (descriptions vidéos)
            try:
                contact_result = find_contacts(
                    driver, url,
                    yt_data_videos=data.get("_yt_data_videos"),
                )
                ch["email"] = contact_result["emails"][0] if contact_result["emails"] else ""
                ch["social_links"] = str(contact_result.get("social", {}))
                # Enrichir les tags contact existants
                ch["contact"] = format_contact_tags(contact_result) or ch.get("contact", [])
            except Exception:
                ch["email"] = ""
                ch["social_links"] = "{}"
            ch.pop("_yt_data_videos", None)
            results.append(ch)
    finally:
        driver.quit()
    progress_callback(1.0, "Terminé !")
    return results


# ============================================================
# HELPERS
# ============================================================

def is_recently_active(published_text):
    if not published_text:
        return False
    t = published_text.lower()
    if any(w in t for w in ["heure", "hour", "minute", "seconde", "second"]):
        return True
    if any(w in t for w in ["jour", "day"]):
        m = re.search(r'(\d+)', t)
        return m is not None and int(m.group(1)) <= 31
    if any(w in t for w in ["semaine", "week"]):
        m = re.search(r'(\d+)', t)
        return m is not None and int(m.group(1)) <= 4
    return False


def score_html(score):
    try:
        s = int(float(score))
    except (ValueError, TypeError):
        return '<span class="score-badge score-low">—</span>'
    cls = "score-high" if s >= 7 else "score-mid" if s >= 5 else "score-low"
    return f'<span class="score-badge {cls}">{s}/10</span>'


def cat_html(cat):
    return f'<span class="cat-pill">{cat}</span>' if cat else ""


def active_html(pub):
    return '<span class="active-badge">🔥 Actif</span>' if is_recently_active(pub) else ""


def channel_info_html(name, url, video, published):
    badge = active_html(published)
    safe_name = html_mod.escape(str(name))
    safe_video = html_mod.escape(str(video))
    yt_svg = '<svg style="display:inline-block;vertical-align:middle;margin-right:6px;" width="24" height="17" viewBox="0 0 24 17"><rect width="24" height="17" rx="4" fill="#FF0000"/><polygon points="10,3.5 10,13.5 17,8.5" fill="#FFF"/></svg>'
    return (
        f'{yt_svg}'
        f'<a href="{url}" target="_blank" style="font-size:1.05rem;font-weight:700;">{safe_name}</a>'
        f' {badge}'
        f'<div style="color:{TEXT_MUTED};font-size:0.73rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px;">{safe_video}</div>'
    )


def kpi_bubble_html(value, label, color):
    return (
        f'<div class="kpi-bubble" style="background: linear-gradient(135deg, {color} 0%, {color}CC 100%);">'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'</div>'
    )


# ============================================================
# SIDEBAR — VISIBLE UNIQUEMENT SUR PROSPECTION (via CSS)
# ============================================================

def render_sidebar():
    with st.sidebar:
        st.markdown("### ☀️ Paramètres de Recherche")
        st.markdown("---")

        kw_input = st.text_area(
            "🔑 Mots-clés (un par ligne)",
            value=st.session_state.get("kw_text", "\n".join(DEFAULT_KEYWORDS)),
            height=150,
            key="kw_area",
        )
        max_per_kw = st.slider("📺 Chaînes / mot-clé", 5, 100, 10, 5)
        min_views = st.number_input("👁️ Vues moy. minimum", 0, 500000, MIN_AVG_VIEWS, 5000)
        subs_range = st.slider(
            "👥 Abonnés (min — max)",
            min_value=5_000,
            max_value=8_000_000,
            value=(5_000, 8_000_000),
            step=5_000,
            format="%d",
        )

        st.markdown("---")
        with st.expander("ℹ️ Comprendre le Score"):
            st.markdown("""
| Critère | Pts |
|---|---|
| Vues moy. >= 15k | **+5** |
| Nano / Micro pépite | **+3** |
| Contact détecté | **+2** |

**Catégories** : Leader >= 150k · Micro 20k-150k · Nano 10k-20k · Petite < 10k
""")
        st.markdown("---")
        try:
            st.connection("gsheets", type=GSheetsConnection)
            st.success("✅ Synchronisé avec Google Sheets")
        except Exception:
            st.caption("🔗 Google Sheets : non configuré")

        return kw_input, max_per_kw, min_views, subs_range


# ============================================================
# TAB 1 — 🔍 PROSPECTION
# ============================================================

def tab_prospection(kw_input, max_per_kw, min_views, subs_range=(5000, 8000000)):
    # Afficher les ballons après un rerun (ajout favori)
    if st.session_state.pop("show_balloons", False):
        st.balloons()

    launch = st.button("🚀 Lancer l'analyse", width="stretch", type="primary")

    if launch:
        keywords = [k.strip() for k in kw_input.strip().split("\n") if k.strip()]
        if not keywords:
            st.warning("Entrez au moins un mot-clé.")
            return
        st.session_state["kw_text"] = kw_input
        bar = st.progress(0)
        txt = st.empty()

        def cb(pct, msg):
            bar.progress(min(pct, 1.0))
            txt.info(msg)

        with st.spinner("Analyse en cours..."):
            results = run_search(keywords, max_per_kw, cb)
        bar.empty()
        txt.empty()
        st.session_state["search_results"] = results
        st.session_state.pop("ignored_urls", None)
        st.success(f"🎉 {len(results)} chaînes analysées !")

    results = st.session_state.get("search_results", [])
    if not results:
        st.markdown(f"<div style='text-align:center; padding:40px 0; color:{TEXT_MUTED}; font-size:1.1rem;'>🔎 Configurez vos mots-clés dans la sidebar puis lancez l'analyse.</div>", unsafe_allow_html=True)
        return

    ignored = st.session_state.get("ignored_urls", set())
    db = load_db()
    urls_in_db = set(db["url"].values) if not db.empty else set()
    min_subs, max_subs = subs_range
    qualified = [
        ch for ch in results
        if ch.get("avg_views") is not None
        and ch["avg_views"] >= min_views
        and (ch.get("subscribers") or 0) >= min_subs
        and (ch.get("subscribers") or 0) <= max_subs
        and ch.get("url", "") not in ignored
        and ch.get("url", "") not in urls_in_db
    ]

    c_sort, _, c1, c2, c3, c4 = st.columns([1.5, 0.5, 1, 1, 1, 1])
    with c_sort:
        sort_by = st.selectbox("🔃 Trier par :", ["Score", "Vues Moyennes", "Abonnés"], key="sp")

    if sort_by == "Vues Moyennes":
        qualified.sort(key=lambda c: c.get("avg_views", 0) or 0, reverse=True)
    elif sort_by == "Abonnés":
        qualified.sort(key=lambda c: c.get("subscribers", 0) or 0, reverse=True)
    else:
        qualified.sort(key=lambda c: (c.get("score", 0), c.get("avg_views", 0)), reverse=True)

    with c1:
        st.metric("🔬 Scrapées", len(results))
    with c2:
        st.metric("✅ Qualifiées", len(qualified))
    with c3:
        st.metric("📢 Reach", fmt(sum(ch.get("subscribers") or 0 for ch in qualified)))
    with c4:
        st.metric(f"🏆 Score>={MIN_SCORE_DISPLAY}", sum(1 for ch in qualified if ch.get("score", 0) >= MIN_SCORE_DISPLAY))

    if not qualified:
        st.warning("Aucune chaîne ne dépasse le seuil.")
        return

    st.markdown("---")

    for ch in qualified:
        name = html_mod.escape(ch.get("name", "").replace("\\u0026", "&"))
        url = ch.get("url", "")
        video = html_mod.escape((ch.get("latest_video") or "N/A")[:60])
        published = ch.get("latest_published", "")
        subs = fmt(ch.get("subscribers"))
        avg_v = fmt(ch.get("avg_views"))
        cat = html_mod.escape(ch.get("category", ""))
        score = ch.get("score", 0)
        # Contact intelligent pour Recherche
        ch_email = ch.get("email", "")
        ch_social = ch.get("social_links", {})
        if isinstance(ch_social, str):
            try:
                ch_social = eval(ch_social)
            except Exception:
                ch_social = {}
        # Filtrer les faux "site" pour Recherche aussi
        rech_site = ch_social.get("site", "")
        if rech_site:
            rs_low = rech_site.lower()
            if any(rs_low.split("?")[0].endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")) or any(d in rs_low for d in ("ytimg.com", "ggpht.com", "googleusercontent.com")):
                rech_site = ""
        rech_contact_parts = []
        if ch_email:
            safe_em = html_mod.escape(ch_email)
            rech_contact_parts.append(f'<a href="mailto:{safe_em}" style="color:{ACCENT};font-weight:700;font-size:0.82rem">📧 {safe_em}</a>')
        if ch_social.get("instagram"):
            rech_contact_parts.append(f'<a href="{html_mod.escape(ch_social["instagram"])}" target="_blank" title="Instagram"><img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png" width="18" height="18" style="vertical-align:middle"></a>')
        if ch_social.get("tiktok"):
            rech_contact_parts.append(f'<a href="{html_mod.escape(ch_social["tiktok"])}" target="_blank" title="TikTok">🎵</a>')
        if rech_site:
            rech_contact_parts.append(f'<a href="{html_mod.escape(rech_site)}" target="_blank" title="Site web">🌐</a>')
        if not ch_email and not rech_contact_parts:
            tag_str = ", ".join(ch.get("contact", []))
            rech_contact_parts.append(f'<span style="color:{TEXT_MUTED};font-size:0.82rem">{html_mod.escape(tag_str) or "—"}</span>')
        contact = " &nbsp;&nbsp; ".join(rech_contact_parts)

        # Card HTML — tout en un bloc coloré et punchy
        score_val = int(float(score)) if score else 0
        if score_val >= 7:
            card_border = GREEN_MINT
            score_bg = "#D1FAE5"
            score_color = "#065F46"
        elif score_val >= 5:
            card_border = GOLD
            score_bg = "#FEF3C7"
            score_color = "#92400E"
        else:
            card_border = PINK
            score_bg = "#FEE2E2"
            score_color = "#991B1B"

        yt_svg = '<svg style="display:inline-block;vertical-align:middle;margin-right:6px" width="22" height="16" viewBox="0 0 24 17"><rect width="24" height="17" rx="4" fill="#FF0000"/><polygon points="10,3.5 10,13.5 17,8.5" fill="#FFF"/></svg>'
        badge = active_html(published)

        # Espacement entre les cards
        st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

        # Boutons coeur/poubelle + card sur la même ligne via st.columns
        c_fav, c_del, c_card = st.columns([0.06, 0.06, 0.88])
        with c_fav:
            if st.button("💛", key=f"add_{url}", help="Ajouter aux favoris"):
                add_to_db(ch)
                push_to_crm(ch)
                st.session_state["show_balloons"] = True
                st.rerun()
        with c_del:
            if st.button("🗑️", key=f"ign_{url}", help="Ignorer"):
                ignored.add(url)
                st.session_state["ignored_urls"] = ignored
                st.rerun()
        with c_card:
            card_html = (
                f'<div style="display:flex;align-items:center;gap:14px;background:{BG_CARD};border:1px solid {BORDER};border-left:4px solid {card_border};border-radius:14px;padding:14px 18px">'
                f'<div style="flex:3;min-width:0">{yt_svg}<a href="{url}" target="_blank" style="font-size:1.15rem;font-weight:700;color:{TEXT} !important">{name}</a>{badge}'
                f'<div style="color:{TEXT_MUTED};font-size:0.82rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px">{video}</div></div>'
                f'<div style="flex:0.7;text-align:center"><div style="font-size:1.2rem;font-weight:800;color:{ORANGE}">{subs}</div><div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase">abonnés</div></div>'
                f'<div style="flex:0.7;text-align:center"><div style="font-size:1.2rem;font-weight:800;color:{BLUE_AZUR}">{avg_v}</div><div style="font-size:0.72rem;color:{TEXT_MUTED};text-transform:uppercase">vues moy.</div></div>'
                f'<div style="flex:0.6;text-align:center"><span style="display:inline-block;padding:4px 12px;border-radius:12px;font-size:0.8rem;font-weight:600;background:{BG_CARD_LIGHT};color:{LAVENDER};border:1px solid {BORDER}">{cat}</span></div>'
                f'<div style="flex:0.5;text-align:center"><span style="display:inline-block;padding:6px 16px;border-radius:20px;font-weight:800;font-size:1rem;background:{score_bg};color:{score_color}">{score_val}/10</span></div>'
                f'<div style="flex:1;text-align:center;font-size:0.82rem;display:flex;flex-wrap:wrap;justify-content:center;gap:4px">{contact}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)


def _rescan_contacts(db):
    """Rescanne les contacts (emails, réseaux) pour toutes les chaînes en base."""
    urls = db["url"].tolist()
    if not urls:
        return
    progress = st.progress(0, text="Scan des contacts en cours...")
    driver = create_driver()
    try:
        for i, url in enumerate(urls):
            name = db.loc[db["url"] == url, "name"].values[0] if len(db.loc[db["url"] == url]) > 0 else url
            progress.progress((i + 1) / len(urls), text=f"Scan contacts {i+1}/{len(urls)} : {str(name)[:30]}...")
            try:
                contact_result = find_contacts(driver, url)
                email = contact_result["emails"][0] if contact_result["emails"] else ""
                social = str(contact_result.get("social", {}))
                tags = format_contact_tags(contact_result)
                mask = db["url"] == url
                df = load_db()
                m = df["url"] == url
                if m.any():
                    if email:
                        df.loc[m, "email"] = email
                    if social and social != "{}":
                        df.loc[m, "social_links"] = social
                    if tags:
                        df.loc[m, "contact"] = ", ".join(tags)
                    save_db(df)
            except Exception:
                continue
    finally:
        driver.quit()
    progress.progress(1.0, text="Scan terminé !")
    st.rerun()


# ============================================================
# TAB 2 — 📝 À CONTACTER
# ============================================================

def tab_a_contacter():
    if st.session_state.pop("show_balloons_prosp", False):
        st.balloons()
    db = load_db()
    if db.empty:
        st.markdown(f"<div style='text-align:center; padding:40px 0; color:{TEXT_MUTED}; font-size:1.1rem;'>📋 Ajoutez des chaînes depuis l'onglet Recherche.</div>", unsafe_allow_html=True)
        return

    db = db[db["ignored"] != "1"]
    if db.empty:
        st.markdown(f"<div style='text-align:center; padding:40px 0; color:{TEXT_MUTED}; font-size:1.1rem;'>📋 Votre liste est vide.</div>", unsafe_allow_html=True)
        return

    total = len(db)
    reach = 0
    for v in db["subscribers"]:
        try:
            reach += int(float(v))
        except (ValueError, TypeError):
            pass
    contacted = int((db["statut"].isin(["Contacté", "En négociation", "Kit envoyé", "Terminé"])).sum())

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📊 Total", total)
    with c2:
        st.metric("📢 Reach", fmt(reach))
    with c3:
        st.metric("📧 Contactés", contacted)

    st.markdown("---")

    cf1, cf2, cf3, cf4 = st.columns([2, 2, 1.5, 1])
    with cf1:
        cats = db["category"].unique().tolist()
        filter_cat = st.multiselect("🏷️ Catégorie", cats, default=[], placeholder="Toutes les catégories")
    with cf2:
        filter_statut = st.multiselect("📌 Statut", STATUTS, default=[], placeholder="Tous les statuts")
    with cf3:
        sort_by = st.selectbox("🔃 Trier par", ["Score", "Vues Moyennes", "Abonnés"], key="sf")
    with cf4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Scanner contacts", help="Recherche emails & réseaux pour toutes les chaînes", key="rescan_contacts"):
            _rescan_contacts(db)

    filtered = db.copy()
    if filter_cat:
        filtered = filtered[filtered["category"].isin(filter_cat)]
    if filter_statut:
        filtered = filtered[filtered["statut"].isin(filter_statut)]
    if filtered.empty:
        st.info("Aucun résultat.")
        return

    filtered = filtered.copy()
    sort_col = {"Score": "score", "Vues Moyennes": "avg_views", "Abonnés": "subscribers"}[sort_by]
    filtered["_s"] = pd.to_numeric(filtered[sort_col], errors="coerce").fillna(0)
    filtered = filtered.sort_values("_s", ascending=False).drop(columns=["_s"])

    st.markdown("---")

    for row_i, (idx, row) in enumerate(filtered.iterrows()):
        name = str(row["name"]).replace("\\u0026", "&")
        url = str(row["url"])
        video = str(row.get("latest_video", ""))[:60]
        published = str(row.get("latest_published", ""))
        cat = str(row.get("category", ""))
        score = str(row.get("score", ""))
        contact_str = str(row.get("contact", "")) or "—"
        email_found = str(row.get("email", "")).strip()
        mail_manual = str(row.get("mail_manual", "")).strip()
        social_raw = str(row.get("social_links", "{}"))
        is_fav = str(row.get("favori", "0")) == "1"
        current_statut = str(row.get("statut", "À contacter"))

        try:
            subs_d = fmt(int(float(row.get("subscribers", 0))))
        except (ValueError, TypeError):
            subs_d = "?"
        try:
            avg_d = fmt(int(float(row.get("avg_views", 0))))
        except (ValueError, TypeError):
            avg_d = "?"

        row_bg = "#FFFFFF"
        safe_name = html_mod.escape(name)
        safe_video = html_mod.escape(video)
        safe_cat = html_mod.escape(cat)
        yt_svg = '<svg style="display:inline-block;vertical-align:middle;margin-right:6px" width="22" height="16" viewBox="0 0 24 17"><rect width="24" height="17" rx="4" fill="#FF0000"/><polygon points="10,3.5 10,13.5 17,8.5" fill="#FFF"/></svg>'
        badge = active_html(published)

        # --- Contact intelligent ---
        display_mail = mail_manual or email_found
        social = {}
        try:
            social = eval(social_raw) if social_raw and social_raw != "{}" else {}
        except Exception:
            pass
        # Filtrer les faux "site" (images/miniatures YouTube)
        _img_ext = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico")
        _bad_domains = ("ytimg.com", "ggpht.com", "googleusercontent.com", "gstatic.com")
        site_url = social.get("site", "")
        if site_url:
            site_low = site_url.lower()
            if any(site_low.split("?")[0].endswith(ext) for ext in _img_ext) or any(d in site_low for d in _bad_domains):
                site_url = ""
        contact_parts = []
        if display_mail:
            safe_mail = html_mod.escape(display_mail)
            contact_parts.append(f'<a href="mailto:{safe_mail}" style="color:{ACCENT};font-weight:700;font-size:0.82rem" title="Envoyer un mail">📧 {safe_mail}</a>')
        if social.get("instagram"):
            contact_parts.append(f'<a href="{html_mod.escape(social["instagram"])}" target="_blank" title="Instagram"><img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png" width="18" height="18" style="vertical-align:middle"></a>')
        if social.get("tiktok"):
            contact_parts.append(f'<a href="{html_mod.escape(social["tiktok"])}" target="_blank" title="TikTok">🎵</a>')
        if social.get("linktree"):
            contact_parts.append(f'<a href="{html_mod.escape(social["linktree"])}" target="_blank" title="Linktree">🌳</a>')
        if site_url:
            contact_parts.append(f'<a href="{html_mod.escape(site_url)}" target="_blank" title="Site web">🌐</a>')
        if not display_mail:
            google_q = html_mod.escape(f'"{name}" contact email')
            contact_parts.append(f'<a href="https://www.google.com/search?q={google_q}" target="_blank" style="color:{LAVENDER};font-weight:600;font-size:0.82rem" title="Chercher le mail sur Google">🔍 Trouver</a>')
        contact_html_cell = " &nbsp;&nbsp; ".join(contact_parts) if contact_parts else '<span style="color:#aaa">—</span>'

        # Espacement entre les cards
        st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

        # Toujours les mêmes colonnes pour garder l'alignement
        c_del, c_card, c_statut = st.columns([0.04, 0.78, 0.18])
        with c_del:
            if st.button("🗑️", key=f"del_{idx}_{url}", help="Supprimer"):
                d = load_db()
                d = d[d["url"] != url]
                save_db(d)
                st.rerun()
        with c_card:
            card_html = (
                f'<div style="background:{row_bg};border:1px solid {BORDER};border-radius:14px;padding:14px 20px;display:flex;align-items:center;gap:20px">'
                f'<div style="flex:2.5;min-width:0">{yt_svg}<a href="{url}" target="_blank" style="font-size:1.1rem;font-weight:700;color:{TEXT} !important">{safe_name}</a>{badge}'
                f'<div style="color:{TEXT_MUTED};font-size:0.8rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px">{safe_video}</div></div>'
                f'<div style="flex:0.55;text-align:center"><div style="font-size:1.1rem;font-weight:800;color:{ORANGE}">{subs_d}</div><div style="font-size:0.68rem;color:{TEXT_MUTED};text-transform:uppercase">abonnés</div></div>'
                f'<div style="flex:0.55;text-align:center"><div style="font-size:1.1rem;font-weight:800;color:{BLUE_AZUR}">{avg_d}</div><div style="font-size:0.68rem;color:{TEXT_MUTED};text-transform:uppercase">vues moy.</div></div>'
                f'<div style="flex:0.6;text-align:center;white-space:nowrap">{cat_html(safe_cat)}</div>'
                f'<div style="flex:0.35;text-align:center">{score_html(score)}</div>'
                f'<div style="flex:1.4;text-align:center;font-size:0.82rem;display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:8px">{contact_html_cell}</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if not display_mail:
                new_mail = st.text_input("m", value=mail_manual, key=f"mail_{idx}_{url}", placeholder="✉️ Saisir email manuellement...", label_visibility="collapsed")
                if new_mail != mail_manual:
                    update_field(url, "mail_manual", new_mail)
                    st.rerun()
        with c_statut:
            si = STATUTS.index(current_statut) if current_statut in STATUTS else 0
            ns = st.selectbox("Statut", STATUTS, si, key=f"st_{idx}_{url}", label_visibility="collapsed")
            if ns != current_statut:
                update_field(url, "statut", ns)
                # Push vers Suivi Campagnes quand "En négociation"
                if ns == "En négociation":
                    pushed = push_influencer_to_suivi(row)
                    if pushed:
                        st.toast(f"✅ {name} ajouté au Suivi Campagnes !")
                st.rerun()
            if st.button("✍️ Brouillon", key=f"draft_{idx}_{url}", help="Générer un brouillon d'email"):
                st.session_state[f"show_draft_{url}"] = True
                st.rerun()

        # Expander brouillon email (affiché sous la card si activé)
        if st.session_state.get(f"show_draft_{url}", False):
            subject, body = generate_email(name, video)
            with st.expander(f"✉️ Brouillon pour {safe_name}", expanded=True):
                st.markdown(
                    f'<div style="background:#FFF8E1;border-radius:10px;padding:12px 16px;margin-bottom:8px">'
                    f'<strong style="color:{ORANGE}">Objet :</strong> <span style="color:{TEXT}">{html_mod.escape(subject)}</span></div>',
                    unsafe_allow_html=True,
                )
                edited_body = st.text_area(
                    "Corps du mail", value=body, height=350,
                    key=f"body_{idx}_{url}",
                )
                mail_to = display_mail or ""
                if mail_to:
                    mailto_link = build_mailto_link(mail_to, subject, edited_body)
                    col_send, col_spacer = st.columns([1, 3])
                    with col_send:
                        if st.button(f"📧 Envoyer à {name}", key=f"send_{idx}_{url}"):
                            st.session_state["show_balloons_prosp"] = True
                            st.session_state[f"mailto_{url}"] = mailto_link
                            st.rerun()
                    # Ouvrir le mailto via JS si le bouton a été cliqué
                    if st.session_state.pop(f"mailto_{url}", None):
                        st.markdown(f'<script>window.open("{mailto_link}", "_blank");</script>', unsafe_allow_html=True)
                        st.markdown(
                            f'<a href="{mailto_link}" target="_blank" style="display:inline-block;padding:8px 20px;background:{GREEN_MINT};color:#fff;border-radius:8px;font-weight:700;font-size:0.88rem;text-decoration:none;margin-top:4px">📧 Cliquez ici si le mail ne s\'est pas ouvert</a>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.info("Aucun email trouvé — copiez le texte et utilisez le lien 🔍 Trouver Mail dans la card.")
                col_close, _ = st.columns([1, 4])
                with col_close:
                    if st.button("❌ Fermer", key=f"close_draft_{idx}_{url}"):
                        st.session_state[f"show_draft_{url}"] = False
                        st.rerun()

    st.markdown("---")
    st.download_button(
        "📥 Exporter CSV",
        data=db.to_csv(index=False),
        file_name=f"a_contacter_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        width="stretch",
    )


# ============================================================
# TAB 3 — 📈 SUIVI CAMPAGNES
# ============================================================

def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def fmt_table(val):
    """Formate un nombre pour les tableaux HTML (ex: 142 218 ou 1.5M)."""
    try:
        n = int(float(val))
    except (ValueError, TypeError):
        return str(val) if val else "—"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.0f}M" if v == int(v) else f"{v:.1f}M"
    return f"{n:,}".replace(",", " ")


def fmt_date(val):
    """Extrait uniquement la date (sans l'heure) d'une valeur date/datetime."""
    s = str(val).strip()
    if not s:
        return "—"
    # Couper au premier espace (retire l'heure)
    return s.split(" ")[0].split("T")[0]


def load_gsheet_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)

        df_influenceurs = conn.read(spreadsheet=GSHEET_URL, worksheet="Influenceurs", ttl=300)
        df_videos = conn.read(spreadsheet=GSHEET_URL, worksheet="Vidéos", ttl=300)
        df_dashboard = conn.read(spreadsheet=GSHEET_URL, worksheet="Dashboard_Data", ttl=300)
        df_agences = conn.read(spreadsheet=GSHEET_URL, worksheet="Agences", ttl=300)

        df_influenceurs = df_influenceurs.dropna(how="all").fillna("")
        df_videos = df_videos.dropna(how="all").fillna("")
        df_dashboard = df_dashboard.dropna(how="all").fillna("")
        df_agences = df_agences.dropna(how="all").fillna("")

        return df_influenceurs, df_videos, df_dashboard, df_agences, True

    except Exception as e:
        st.sidebar.caption(f"⚠️ GSheets: {str(e)[:60]}")
        if not os.path.exists(CRM_FILE):
            pd.DataFrame(columns=CRM_COLUMNS).to_csv(CRM_FILE, index=False)
        crm = load_crm()
        return crm, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False


def save_to_gsheet(worksheet_name, df):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(spreadsheet=GSHEET_URL, worksheet=worksheet_name, data=df)
        return True
    except Exception as e:
        st.error(f"Erreur écriture GSheets : {e}")
        return False


def push_influencer_to_suivi(channel_row):
    """
    Ajoute un influenceur de la DB Prospection dans le Google Sheet Influenceurs
    s'il n'y est pas déjà. Appelé quand le statut passe à 'En négociation'.
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_inf = conn.read(spreadsheet=GSHEET_URL, worksheet="Influenceurs", ttl=0)
        df_inf = df_inf.dropna(how="all").fillna("")

        # Identifier par le nom/handle pour éviter les doublons
        name = str(channel_row.get("name", ""))
        handle = str(channel_row.get("handle", ""))
        alias = handle.lstrip("@") if handle else name

        # Vérifier si déjà présent
        if not df_inf.empty and "Alias" in df_inf.columns:
            existing = df_inf["Alias"].astype(str).str.strip().str.lower()
            if alias.strip().lower() in existing.values:
                return False  # Déjà présent

        mail = str(channel_row.get("email", "") or channel_row.get("mail_manual", "") or "")
        subs = str(channel_row.get("subscribers", ""))
        url = str(channel_row.get("url", ""))

        new_row = {
            "Alias": alias,
            "ID Influenceur": alias,
            "Nom": name,
            "Mail ": mail,
            "Infos": "",
            "Statut ": "En négociation",
            "Chaîne YT": url,
            "Channel ID ": "",
            "Abonnés": subs,
            "Agence/Indep": "Independant",
            "Date fin de contrat": "",
            "Lien contrat": "",
            "📦 Kit Envoyé": False,
            "🎥 Vidéo 1 Reçue": False,
            "Vidéo 2 reçue": False,
        }

        # Ajouter les colonnes manquantes
        for col in new_row:
            if col not in df_inf.columns:
                df_inf[col] = ""

        df_inf = pd.concat([df_inf, pd.DataFrame([new_row])], ignore_index=True)
        conn.update(spreadsheet=GSHEET_URL, worksheet="Influenceurs", data=df_inf)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.toast(f"⚠️ Erreur push Suivi : {e}")
        return False


def tab_suivi_campagnes():
    df_influenceurs, df_videos, df_dashboard, df_agences, is_gsheet = load_gsheet_data()

    source_label = "🟢 Google Sheets" if is_gsheet else "🟡 CSV local"
    st.markdown(f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.85rem;'>Source : {source_label}</div>", unsafe_allow_html=True)

    # =============================================
    # 🔄 LIVE RE-SCRAPER
    # =============================================
    rescrape_col1, rescrape_col2 = st.columns([1, 3])
    with rescrape_col1:
        rescrape_btn = st.button("🔄 Actualiser les statistiques YouTube", key="rescrape_btn")
    with rescrape_col2:
        st.markdown(f"<div style='padding-top:8px; color:{TEXT_MUTED}; font-size:0.82rem;'>Re-scrape abonnés & vues moyennes pour chaque chaîne du Suivi</div>", unsafe_allow_html=True)

    if rescrape_btn and is_gsheet and not df_influenceurs.empty:
        # Identifier la colonne URL
        url_col = None
        for candidate in ["Chaîne YT", "Chaine YT", "URL"]:
            if candidate in df_influenceurs.columns:
                url_col = candidate
                break

        if url_col:
            urls = [str(u).strip() for u in df_influenceurs[url_col] if str(u).strip().startswith("http")]
            url_to_idx = {}
            for idx, row in df_influenceurs.iterrows():
                u = str(row.get(url_col, "")).strip()
                if u.startswith("http"):
                    url_to_idx[u] = idx

            if urls:
                progress_bar = st.progress(0, text="Lancement du scraper...")
                status_text = st.empty()

                def on_progress(i, total, url, stats):
                    progress_bar.progress(i / total, text=f"Chaîne {i}/{total}...")
                    subs_str = fmt(stats["subscribers"]) if stats["subscribers"] else "?"
                    views_str = fmt(stats["avg_views"]) if stats["avg_views"] else "?"
                    status_text.markdown(f"✅ **{i}/{total}** — {url} → Abonnés: {subs_str} | Vues moy: {views_str}")

                results = bulk_rescrape(urls, progress_callback=on_progress)
                progress_bar.progress(1.0, text="Terminé !")

                # Mettre à jour le DataFrame
                updated = False
                abos_col = "Abonnés" if "Abonnés" in df_influenceurs.columns else None
                for url, stats in results.items():
                    if url in url_to_idx:
                        idx = url_to_idx[url]
                        if stats["subscribers"] is not None and abos_col:
                            df_influenceurs.at[idx, abos_col] = stats["subscribers"]
                            updated = True

                if updated:
                    # Sauvegarder vers Google Sheets
                    save_df = df_influenceurs.copy()
                    ok = save_to_gsheet("Influenceurs", save_df)
                    if ok:
                        st.success("🎉 Statistiques mises à jour dans Google Sheets !")
                        st.cache_data.clear()
                    else:
                        st.error("Erreur lors de la sauvegarde.")
                else:
                    st.info("Aucune donnée mise à jour.")
            else:
                st.warning("Aucune URL de chaîne trouvée dans le tableau.")
        else:
            st.warning("Colonne URL de chaîne non trouvée dans le tableau Influenceurs.")
    elif rescrape_btn and not is_gsheet:
        st.warning("Le re-scraper nécessite une connexion Google Sheets active.")

    st.markdown("---")

    # =============================================
    # 🔎 RECHERCHE PAR INFLUENCEUR
    # =============================================
    search_col1, search_col2, search_col3 = st.columns([3, 0.4, 1])
    with search_col1:
        search_query = st.text_input(
            "🔎 Rechercher un influenceur",
            value="",
            placeholder="Tapez un nom, alias ou ID...",
            key="suivi_search",
        )
    with search_col2:
        st.markdown("<div style='padding-top:24px;'></div>", unsafe_allow_html=True)
        if st.button("🔄", key="reset_search", help="Réinitialiser la recherche"):
            st.session_state["suivi_search"] = ""
            st.rerun()
    with search_col3:
        st.markdown(f"<div style='padding-top:28px; color:{TEXT_MUTED}; font-size:0.9rem;'>Filtre tous les tableaux</div>", unsafe_allow_html=True)

    # Appliquer le filtre sur les dataframes
    sq = search_query.strip().lower()
    if sq:
        def match_row(row):
            return any(sq in str(v).lower() for v in row.values)
        if not df_influenceurs.empty:
            mask_inf = df_influenceurs.apply(match_row, axis=1)
            df_influenceurs = df_influenceurs[mask_inf]
        if not df_dashboard.empty:
            mask_dash = df_dashboard.apply(match_row, axis=1)
            df_dashboard = df_dashboard[mask_dash]
        if sq and (df_influenceurs.empty and df_dashboard.empty):
            st.warning(f"Aucun résultat pour « {search_query} »")

    st.markdown("---")

    # =============================================
    # ⚠️ ALERTES & EN COURS
    # =============================================
    st.markdown('<div class="section-title">⚠️ Alertes & Actions en cours</div>', unsafe_allow_html=True)

    # Colonnes Vidéos : Pseudo, ID Influenceurs, Lien vidéo, ID vidéo, Statut, Date publication
    vid_statut_col = "Statut" if (is_gsheet and not df_videos.empty and "Statut" in df_videos.columns) else None

    if is_gsheet and not df_videos.empty and vid_statut_col:
        alert_statuts = ["Pas commencé", "A venir", "Bloqué", "Shorts manquants", "Vidéo 2 a venir"]
        alert_df = df_videos[df_videos[vid_statut_col].astype(str).str.strip().isin(alert_statuts)].copy()

        # Jointure avec Influenceurs pour récupérer Mail et Chaîne YT
        if not alert_df.empty and not df_influenceurs.empty:
            inf_map = {}
            id_inf_col = "ID Influenceur" if "ID Influenceur" in df_influenceurs.columns else None
            mail_col = "Mail " if "Mail " in df_influenceurs.columns else ("Mail" if "Mail" in df_influenceurs.columns else None)
            yt_col = "Chaîne YT" if "Chaîne YT" in df_influenceurs.columns else None
            if id_inf_col:
                for _, inf_row in df_influenceurs.iterrows():
                    iid = str(inf_row.get(id_inf_col, "")).strip()
                    if iid:
                        inf_map[iid] = {
                            "mail": str(inf_row.get(mail_col, "")).strip() if mail_col else "",
                            "chaine_yt": str(inf_row.get(yt_col, "")).strip() if yt_col else "",
                        }
            # Ajouter les colonnes enrichies
            alert_df["📧 Contact"] = alert_df["ID Influenceurs"].astype(str).str.strip().map(
                lambda x: inf_map.get(x, {}).get("mail", "")
            )
            alert_df["_chaine_yt"] = alert_df["ID Influenceurs"].astype(str).str.strip().map(
                lambda x: inf_map.get(x, {}).get("chaine_yt", "")
            )

        if not alert_df.empty:
            # Tableau HTML avec Nom cliquable, Statut, Contact
            alert_html = '<div style="display:flex; justify-content:center;">'
            alert_html += '<table class="styled-table" style="table-layout:auto; width:auto;"><thead><tr>'
            alert_html += '<th style="padding:8px 24px;">📺 Nom</th><th style="padding:8px 24px;">⚠️ Statut</th><th style="padding:8px 24px;">📧 Contact</th>'
            alert_html += "</tr></thead><tbody>"
            for _, r in alert_df.iterrows():
                pseudo = str(r.get("Pseudo", "")).strip()
                statut = str(r.get(vid_statut_col, ""))
                mail = str(r.get("📧 Contact", ""))
                chaine_yt = str(r.get("_chaine_yt", "")).strip()
                # Nom cliquable vers la chaîne YT
                if chaine_yt and chaine_yt.startswith("http"):
                    nom_cell = f'<a href="{chaine_yt}" target="_blank">{pseudo} 🔗</a>'
                else:
                    nom_cell = pseudo
                # Mail cliquable
                mail_cell = f'<a href="mailto:{mail}">{mail}</a>' if mail and "@" in mail else mail or "—"
                alert_html += f'<tr><td style="padding:8px 24px;">{nom_cell}</td><td style="padding:8px 24px;">{statut}</td><td style="padding:8px 24px;">{mail_cell}</td></tr>'
            alert_html += "</tbody></table></div>"
            st.markdown(f'<div class="alert-section">{alert_html}</div>', unsafe_allow_html=True)

            # Éditeur alertes — caché par défaut
            alert_editor_df = alert_df[["Pseudo", vid_statut_col]].copy().reset_index(drop=True)
            alert_editor_df = alert_editor_df.rename(columns={vid_statut_col: "Statut", "Pseudo": "Nom"})
            alert_statuts_options = [
                "", "Publiée", "En cours", "Planifiée", "A venir",
                "Bloqué", "Shorts manquants", "Pas commencé", "Annulée",
            ]
            with st.expander("✏️ Modifier les alertes", expanded=False):
                edited_alerts = st.data_editor(
                    alert_editor_df,
                    use_container_width=True,
                    hide_index=True,
                    height=250,
                    column_config={
                        "Statut": st.column_config.SelectboxColumn("⚠️ Statut", options=alert_statuts_options),
                        "Nom": st.column_config.TextColumn("📺 Nom", disabled=True),
                    },
                    key="alert_editor",
                )
                if st.button("💾 Enregistrer les alertes", key="save_alerts_btn"):
                    save_vid = df_videos.copy()
                    for _, ar in edited_alerts.iterrows():
                        match_val = str(ar.get("Nom", "")).strip()
                        if match_val:
                            mask = save_vid["Pseudo"].astype(str).str.strip() == match_val
                            if mask.any():
                                save_vid.loc[mask, vid_statut_col] = ar.get("Statut", "")
                    ok = save_to_gsheet("Vidéos", save_vid)
                    if ok:
                        st.success("✅ Alertes sauvegardées !")
                        st.cache_data.clear()
                        st.rerun()
        else:
            st.markdown(f"<div class='alert-section' style='color:{GREEN_MINT}; font-size:1rem; font-weight:600;'>🎉 Aucune alerte — Tout roule !</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='alert-section' style='color:{TEXT_MUTED};'>Les alertes s'afficheront une fois connecté.</div>", unsafe_allow_html=True)

    st.markdown("---")

    # =============================================
    # ✨ KPIs — BULLES COLORÉES
    # =============================================
    st.markdown('<div class="section-title">✨ Stats Globales</div>', unsafe_allow_html=True)

    if is_gsheet and not df_dashboard.empty:
        vues_vals = pd.to_numeric(df_dashboard.get("Vues", pd.Series()), errors="coerce").dropna()
        likes_vals = pd.to_numeric(df_dashboard.get("Likes", pd.Series()), errors="coerce").dropna()
        abos_vals = pd.to_numeric(df_dashboard.get("Abonnés", pd.Series()), errors="coerce").dropna()

        nb_inf = df_dashboard.get("ID Influenceur", pd.Series()).nunique()
        nb_vid = len(df_dashboard)
        total_vues = int(vues_vals.sum()) if len(vues_vals) > 0 else 0
        avg_vues = int(vues_vals.mean()) if len(vues_vals) > 0 else 0
        avg_likes = int(likes_vals.mean()) if len(likes_vals) > 0 else 0
        avg_abos = int(abos_vals.mean()) if len(abos_vals) > 0 else 0
    elif not is_gsheet and not df_influenceurs.empty:
        subs_v = [safe_float(v) for v in df_influenceurs.get("subscribers", []) if v]
        views_v = [safe_float(v) for v in df_influenceurs.get("avg_views", []) if v]
        nb_inf = len(df_influenceurs)
        nb_vid = total_vues = 0
        avg_vues = int(sum(views_v) / len(views_v)) if views_v else 0
        avg_likes = 0
        avg_abos = int(sum(subs_v) / len(subs_v)) if subs_v else 0
    else:
        nb_inf = nb_vid = total_vues = avg_vues = avg_likes = avg_abos = 0

    bubbles = '<div class="kpi-row">'
    bubbles += kpi_bubble_html(str(nb_inf), "Influenceurs", BLUE_AZUR)
    bubbles += kpi_bubble_html(str(nb_vid), "Vidéos", GREEN_MINT)
    bubbles += kpi_bubble_html(fmt(total_vues) if total_vues else "—", "Total Vues", ORANGE)
    bubbles += kpi_bubble_html(fmt(avg_vues) if avg_vues else "—", "Moy. Vues", ACCENT)
    bubbles += kpi_bubble_html(fmt(avg_likes) if avg_likes else "—", "Moy. Likes", PINK)
    bubbles += kpi_bubble_html(fmt(avg_abos) if avg_abos else "—", "Moy. Abonnés", LAVENDER)
    bubbles += '</div>'
    st.markdown(bubbles, unsafe_allow_html=True)

    st.markdown("---")

    # =============================================
    # 🏆 TOP 5 PODIUM PRINTANIER
    # =============================================
    st.markdown('<div class="section-title">🏆 Top 5 Influenceurs</div>', unsafe_allow_html=True)

    PODIUM_STYLES = [
        ("background: linear-gradient(135deg, #FFD700 0%, #FFBE0B 100%); color: #5D4200;", "🥇"),
        ("background: linear-gradient(135deg, #C4D4E0 0%, #A8B8C8 100%); color: #3D4F5F;", "🥈"),
        ("background: linear-gradient(135deg, #E8A87C 0%, #D4956A 100%); color: #5A3520;", "🥉"),
        (f"background: linear-gradient(135deg, {GREEN_MINT} 0%, #04BF8A 100%); color: #FFF;", "4️⃣"),
        (f"background: linear-gradient(135deg, {BLUE_AZUR} 0%, #0E7490 100%); color: #FFF;", "5️⃣"),
    ]

    if is_gsheet and not df_dashboard.empty:
        df_c = df_dashboard.copy()
        df_c["Vues_n"] = pd.to_numeric(df_c.get("Vues", 0), errors="coerce").fillna(0)
        df_c["Likes_n"] = pd.to_numeric(df_c.get("Likes", 0), errors="coerce").fillna(0)
        df_c["Comments_n"] = pd.to_numeric(df_c.get("Commentaires", 0), errors="coerce").fillna(0)
        agg = df_c.groupby("ID Influenceur").agg(
            Nom=("Nom", "first"),
            Vues=("Vues_n", "mean"),
            Likes=("Likes_n", "mean"),
            Nb_videos=("Vues_n", "count"),
        ).reset_index()
        # Joindre avec df_influenceurs pour récupérer l'Alias (nom de chaîne YT)
        if not df_influenceurs.empty and "Alias" in df_influenceurs.columns and "ID Influenceur" in df_influenceurs.columns:
            alias_map = df_influenceurs.set_index("ID Influenceur")["Alias"].to_dict()
            agg["Alias"] = agg["ID Influenceur"].map(alias_map).fillna(agg["Nom"])
        else:
            agg["Alias"] = agg["Nom"]
        agg = agg.sort_values("Vues", ascending=False).head(5)

        if not agg.empty:
            podium_cols = st.columns(len(agg))
            for i, (_, row) in enumerate(agg.iterrows()):
                style, emoji = PODIUM_STYLES[i] if i < len(PODIUM_STYLES) else (PODIUM_STYLES[-1])
                alias = str(row.get("Alias", row["ID Influenceur"]))
                if len(alias) > 20:
                    alias = alias[:18] + "…"
                with podium_cols[i]:
                    st.markdown(f"""
                    <div class="podium-card" style="{style}">
                        <div class="podium-rank">{emoji}</div>
                        <div class="podium-name">{alias}</div>
                        <div class="podium-stat">
                            <strong>{fmt(int(row['Vues']))}</strong> vues moy.
                            <br><strong>{fmt(int(row['Likes']))}</strong> likes moy.
                            <br>{int(row['Nb_videos'])} vidéos
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align:center; color:{TEXT_MUTED}; padding:20px;'>Pas assez de données.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:center; color:{TEXT_MUTED}; padding:20px;'>🏆 Le podium s'affichera avec des données Google Sheets.</div>", unsafe_allow_html=True)

    st.markdown("---")

    # =============================================
    # 📊 Performance par Influenceur
    # =============================================
    st.markdown('<div class="section-title">📊 Performance par Influenceur</div>', unsafe_allow_html=True)

    if is_gsheet and not df_dashboard.empty:
        df_d = df_dashboard.copy()
        df_d["Vues_num"] = pd.to_numeric(df_d.get("Vues", 0), errors="coerce").fillna(0)
        df_d["Likes_num"] = pd.to_numeric(df_d.get("Likes", 0), errors="coerce").fillna(0)
        perf = df_d.groupby("ID Influenceur").agg(
            Nom=("Nom", "first"),
            Nb_videos=("Vues_num", "count"),
            Total_vues=("Vues_num", "sum"),
            Moy_vues=("Vues_num", "mean"),
            Total_likes=("Likes_num", "sum"),
        ).reset_index()

        # HTML table — texte centré garanti
        perf_html = '<table class="styled-table"><thead><tr>'
        for h in ["ID Influenceur", "Nom", "📹 Vidéos", "👁️ Total vues", "📊 Moy. vues", "❤️ Total likes"]:
            perf_html += f"<th>{h}</th>"
        perf_html += "</tr></thead><tbody>"
        for _, r in perf.iterrows():
            perf_html += "<tr>"
            perf_html += f"<td>{r['ID Influenceur']}</td>"
            perf_html += f"<td>{r['Nom']}</td>"
            perf_html += f"<td>{int(r['Nb_videos'])}</td>"
            perf_html += f"<td>{fmt_table(int(r['Total_vues'])) if r['Total_vues'] > 0 else '—'}</td>"
            perf_html += f"<td>{fmt_table(int(r['Moy_vues'])) if r['Moy_vues'] > 0 else '—'}</td>"
            perf_html += f"<td>{fmt_table(int(r['Total_likes'])) if r['Total_likes'] > 0 else '—'}</td>"
            perf_html += "</tr>"
        perf_html += "</tbody></table>"
        st.markdown(f'<div class="table-scroll-wrapper">{perf_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:center; color:{TEXT_MUTED}; padding:20px;'>Données de performance indisponibles.</div>", unsafe_allow_html=True)

    st.markdown("---")

    # =============================================
    # 🎬 Détails Vidéos
    # =============================================
    st.markdown('<div class="section-title">🎬 Détails Vidéos</div>', unsafe_allow_html=True)

    detail_cols = [
        "ID Influenceur", "Nom", "Lien vidéo", "Statut vidéo",
        "Date publication", "Vues", "Commentaires", "Likes", "Abonnés",
    ]
    if is_gsheet and not df_dashboard.empty:
        available_detail = [c for c in detail_cols if c in df_dashboard.columns]
        detail_df = df_dashboard[available_detail].copy().reset_index(drop=True)
    else:
        detail_df = pd.DataFrame(columns=detail_cols)

    # Affichage HTML centré
    if not detail_df.empty:
        vid_headers = ["ID Influenceur", "Nom", "🔗 Lien", "📌 Statut", "📅 Date", "👁️ Vues", "💬 Comments", "❤️ Likes", "👥 Abonnés"]
        vid_html = '<table class="styled-table"><thead><tr>'
        for h in vid_headers:
            vid_html += f"<th>{h}</th>"
        vid_html += "</tr></thead><tbody>"
        for _, r in detail_df.iterrows():
            lien = str(r.get("Lien vidéo", ""))
            lien_display = f'<a href="{lien}" target="_blank">🔗 Voir</a>' if lien and lien != "" else "—"
            vid_html += "<tr>"
            vid_html += f"<td>{r.get('ID Influenceur', '')}</td>"
            vid_html += f"<td>{r.get('Nom', '')}</td>"
            vid_html += f"<td>{lien_display}</td>"
            vid_html += f"<td>{r.get('Statut vidéo', '')}</td>"
            vid_html += f"<td>{fmt_date(r.get('Date publication', ''))}</td>"
            vid_html += f"<td>{fmt_table(r.get('Vues', ''))}</td>"
            vid_html += f"<td>{fmt_table(r.get('Commentaires', ''))}</td>"
            vid_html += f"<td>{fmt_table(r.get('Likes', ''))}</td>"
            vid_html += f"<td>{fmt_table(r.get('Abonnés', ''))}</td>"
            vid_html += "</tr>"
        vid_html += "</tbody></table>"
        st.markdown(f'<div class="table-scroll-wrapper">{vid_html}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # Éditeur pour modifier les détails vidéos — caché par défaut
    with st.expander("✏️ Modifier les détails vidéos", expanded=False):
        edited_details = st.data_editor(
            detail_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=350,
            column_config={
                "Statut vidéo": st.column_config.SelectboxColumn(
                    "📌 Statut",
                    options=["", "Publiée", "En cours", "Planifiée", "Annulée"],
                    default="",
                ),
                "Lien vidéo": st.column_config.LinkColumn("🔗 Lien"),
                "Vues": st.column_config.NumberColumn("👁️ Vues", format="%d"),
                "Likes": st.column_config.NumberColumn("❤️ Likes", format="%d"),
                "Commentaires": st.column_config.NumberColumn("💬 Comments", format="%d"),
                "Abonnés": st.column_config.NumberColumn("👥 Abonnés", format="%d"),
            },
            key="detail_editor",
        )
        if st.button("💾 Enregistrer les détails vidéos", key="save_details_btn"):
            if is_gsheet:
                save_detail = edited_details.copy()
                target_cols = [
                    "ID Influenceur", "Nom", "Lien vidéo", "Statut vidéo",
                    "Date publication", "Vues", "Commentaires", "Likes", "Abonnés",
                ]
                for col in target_cols:
                    if col not in save_detail.columns:
                        save_detail[col] = ""
                save_detail = save_detail[target_cols]
                ok = save_to_gsheet("Dashboard_Data", save_detail)
                if ok:
                    st.success("✅ Détails vidéos sauvegardés !")
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")

    # =============================================
    # 📇 Informations Influenceurs
    # =============================================
    st.markdown('<div class="section-title">📇 Informations Influenceurs</div>', unsafe_allow_html=True)

    CHECKLIST_COLS = ["📦 Kit Envoyé", "🎥 Vidéo 1 Reçue", "Vidéo 2 reçue"]

    if is_gsheet and not df_influenceurs.empty:
        contact_cols = [
            "Alias", "ID Influenceur", "Nom", "Mail ", "Infos",
            "Chaîne YT", "Channel ID ", "Abonnés", "Agence/Indep", "Date fin de contrat",
            "Lien contrat",
        ] + CHECKLIST_COLS
        available = [c for c in contact_cols if c in df_influenceurs.columns]
        contact_df = df_influenceurs[available].copy().reset_index(drop=True)
        contact_df = contact_df.rename(columns={
            "Mail ": "Mail",
            "Channel ID ": "Channel ID",
            "Date fin de contrat": "Date fin contrat",
        })
        # S'assurer que Lien contrat existe
        if "Lien contrat" not in contact_df.columns:
            contact_df["Lien contrat"] = ""
        # S'assurer que les colonnes checklist existent et sont booléennes
        for ck in CHECKLIST_COLS:
            if ck not in contact_df.columns:
                contact_df[ck] = False
            else:
                contact_df[ck] = contact_df[ck].apply(
                    lambda v: str(v).strip().upper() in ("TRUE", "1", "OUI", "YES", "VRAI")
                )
    else:
        base_cols = [
            "Alias", "ID Influenceur", "Nom", "Mail", "Infos",
            "Chaîne YT", "Channel ID", "Abonnés", "Agence/Indep", "Date fin contrat",
            "Lien contrat",
        ]
        contact_df = pd.DataFrame(columns=base_cols + CHECKLIST_COLS)
        for ck in CHECKLIST_COLS:
            contact_df[ck] = False

    # Affichage lecture seule — HTML centré avec Alias cliquable vers Chaîne YT
    if not contact_df.empty:
        info_headers = ["📺 Alias", "Nom", "📧 Mail", "📝 Infos", "👥 Abonnés", "🏢 Agence<br>+ contrat",
                        "📦 Kit<br>Envoyé", "🎥 Vidéo 1", "🎥 Vidéo 2"]
        info_widths = ["12%", "10%", "16%", "24%", "8%", "12%", "6%", "6%", "6%"]
        info_html = '<table class="styled-table" style="table-layout:fixed;width:100%"><colgroup>'
        for w in info_widths:
            info_html += f'<col style="width:{w}">'
        info_html += '</colgroup><thead><tr>'
        for h in info_headers:
            info_html += f"<th>{h}</th>"
        info_html += "</tr></thead><tbody>"
        for _, r in contact_df.iterrows():
            infos_text = str(r.get("Infos", "")).replace("\n", "<br>")
            alias = str(r.get("Alias", ""))
            chaine_yt = str(r.get("Chaîne YT", "")).strip()
            # Alias cliquable si Chaîne YT renseignée
            if chaine_yt and chaine_yt.startswith("http"):
                alias_cell = f'<a href="{chaine_yt}" target="_blank" title="{chaine_yt}">{alias} 🔗</a>'
            elif chaine_yt:
                alias_cell = f'{alias} <span style="color:{TEXT_MUTED}; font-size:0.75rem;">({chaine_yt})</span>'
            else:
                alias_cell = alias
            info_html += "<tr>"
            info_html += f'<td class="wrap-cell">{alias_cell}</td>'
            info_html += f'<td class="wrap-cell">{r.get("Nom", "")}</td>'
            info_html += f'<td class="wrap-cell">{r.get("Mail", "")}</td>'
            info_html += f'<td class="infos-cell">{infos_text}</td>'
            info_html += f"<td>{fmt_table(r.get('Abonnés', ''))}</td>"
            agence_val = str(r.get("Agence/Indep", ""))
            contrat_url = str(r.get("Lien contrat", "")).strip()
            contrat_line = f'<br><a href="{contrat_url}" target="_blank" title="Voir le contrat" style="font-size:0.85rem;">📄 Contrat</a>' if contrat_url and contrat_url.startswith("http") else ""
            info_html += f"<td>{agence_val}{contrat_line}</td>"
            for ck in CHECKLIST_COLS:
                val = r.get(ck, False)
                icon = "✅" if val else "⬜"
                info_html += f"<td style='text-align:center;'>{icon}</td>"
            info_html += "</tr>"
        info_html += "</tbody></table>"
        st.markdown(f'<div class="table-scroll-wrapper">{info_html}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # Éditeur pour modifier les données — caché par défaut
    with st.expander("✏️ Modifier les informations influenceurs", expanded=False):
        edited_contacts = st.data_editor(
            contact_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=400,
            column_config={
                "Alias": st.column_config.TextColumn("📺 Alias", pinned="left"),
                "Agence/Indep": st.column_config.SelectboxColumn(
                    "🏢 Agence/Indep",
                    options=["", "Agence", "Independant"],
                ),
                "Mail": st.column_config.TextColumn("📧 Mail"),
                "Chaîne YT": st.column_config.TextColumn("📺 Chaîne YT"),
                "Infos": st.column_config.TextColumn("📝 Infos", width="large"),
                "📦 Kit Envoyé": st.column_config.CheckboxColumn("📦 Kit Envoyé", default=False),
                "🎥 Vidéo 1 Reçue": st.column_config.CheckboxColumn("🎥 Vidéo 1 Reçue", default=False),
                "Vidéo 2 reçue": st.column_config.CheckboxColumn("🎥 Vidéo 2 reçue", default=False),
                "Lien contrat": st.column_config.TextColumn("📄 Lien contrat"),
            },
            key="contact_editor",
        )
        if st.button("💾 Enregistrer les informations influenceurs", key="save_contacts_btn"):
            if is_gsheet:
                save_df = edited_contacts.copy()
                save_df = save_df.rename(columns={
                    "Mail": "Mail ",
                    "Channel ID": "Channel ID ",
                    "Date fin contrat": "Date fin de contrat",
                })
                inf_target_cols = [
                    "Alias", "ID Influenceur", "Nom", "Mail ", "Infos", "Statut ",
                    "Chaîne YT", "Channel ID ", "Abonnés", "Agence/Indep", "Date fin de contrat",
                    "Lien contrat",
                ] + CHECKLIST_COLS
                for col in inf_target_cols:
                    if col not in save_df.columns:
                        save_df[col] = ""
                save_df = save_df[inf_target_cols]
                ok = save_to_gsheet("Influenceurs", save_df)
                if ok:
                    st.success("✅ Informations influenceurs sauvegardées !")
                    st.cache_data.clear()
                    st.rerun()

    st.markdown("---")

    # =============================================
    # 🤝 NOS PARTENAIRES AGENCES
    # =============================================
    st.markdown('<div class="section-title">🤝 Nos Partenaires Agences</div>', unsafe_allow_html=True)

    AGENCES_DATA = {
        "Atta": {
            "color": ORANGE,
            "emoji": "🟠",
            "contacts": [
                ("Théodore Genin", "theodore@atta-agence.com"),
                ("Pauline Hardy", "pauline@atta-agence.com"),
            ],
            "influenceurs": [],
        },
        "Surex": {
            "color": BLUE_AZUR,
            "emoji": "🔵",
            "contacts": [
                ("Léo Duthuit", "leo@surex.fr"),
            ],
            "influenceurs": [],
        },
    }

    if is_gsheet and not df_agences.empty:
        for agency_name in AGENCES_DATA:
            if agency_name in df_agences.columns:
                infs = [str(v).strip() for v in df_agences[agency_name].tolist() if str(v).strip()]
                AGENCES_DATA[agency_name]["influenceurs"] = infs

    agency_cols = st.columns(len(AGENCES_DATA))
    for i, (name, data) in enumerate(AGENCES_DATA.items()):
        color = data["color"]
        emoji = data["emoji"]
        contacts_html = ""
        for cname, cemail in data["contacts"]:
            contacts_html += f'<div class="agence-contact">👤 <strong>{cname}</strong><br>📧 <a href="mailto:{cemail}">{cemail}</a></div>'

        inf_list = data["influenceurs"]
        if inf_list:
            li_items = "".join(f"<li>{inf}</li>" for inf in inf_list)
        else:
            li_items = f"<li style='color:{TEXT_MUTED};'>Aucun influenceur listé</li>"

        with agency_cols[i]:
            st.markdown(f"""
            <div class="agence-card" style="border-top: 4px solid {color};">
                <h3 style="color:{color};">{emoji} {name}</h3>
                {contacts_html}
                <div style="margin-top:14px; padding-top:10px; border-top:1px solid {BORDER};">
                    <div style="font-size:0.78rem; color:{TEXT_MUTED}; font-weight:600; margin-bottom:6px;">📺 INFLUENCEURS GÉRÉS</div>
                    <ul class="agence-influencers">{li_items}</ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # =============================================
    # 💾 SAUVEGARDER — EN BAS, LARGE ET VISIBLE
    # =============================================
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("💾 Enregistrer les modifications", type="primary", width="stretch", key="save_btn"):
        if is_gsheet:
            save_df = edited_contacts.copy()
            save_df = save_df.rename(columns={
                "Mail": "Mail ",
                "Channel ID": "Channel ID ",
                "Date fin contrat": "Date fin de contrat",
            })

            inf_target_cols = [
                "Alias", "ID Influenceur", "Nom", "Mail ", "Infos", "Statut ",
                "Chaîne YT", "Channel ID ", "Abonnés", "Agence/Indep", "Date fin de contrat",
                "Lien contrat",
            ] + CHECKLIST_COLS
            for col in inf_target_cols:
                if col not in save_df.columns:
                    save_df[col] = ""
            save_df = save_df[inf_target_cols]
            ok1 = save_to_gsheet("Influenceurs", save_df)

            save_detail = edited_details.copy()
            target_cols = [
                "ID Influenceur", "Nom", "Lien vidéo", "Statut vidéo",
                "Date publication", "Vues", "Commentaires", "Likes", "Abonnés",
            ]
            for col in target_cols:
                if col not in save_detail.columns:
                    save_detail[col] = ""
            save_detail = save_detail[target_cols]
            ok2 = save_to_gsheet("Dashboard_Data", save_detail)

            if ok1 and ok2:
                st.balloons()
                st.success("🎉 Modifications sauvegardées dans Google Sheets !")
                st.cache_data.clear()
                st.rerun()
            elif ok1:
                st.warning("Fiches contacts OK. Erreur sur les détails vidéos.")
            elif ok2:
                st.warning("Détails vidéos OK. Erreur sur les fiches contacts.")
        else:
            if len(edited_contacts) > 0:
                save_data = pd.DataFrame(columns=CRM_COLUMNS)
                for i in range(len(edited_contacts)):
                    row = {col: "" for col in CRM_COLUMNS}
                    ec = edited_contacts.iloc[i]
                    row["alias"] = str(ec.get("Alias", ""))
                    row["statut"] = str(ec.get("Statut", ""))
                    row["agence"] = str(ec.get("Agence/Indep", ""))
                    row["chaine_yt"] = str(ec.get("Chaîne YT", ""))
                    row["date_fin_contrat"] = str(ec.get("Date fin contrat", ""))
                    row["infos"] = str(ec.get("Infos", ""))
                    row["mail"] = str(ec.get("Mail", ""))
                    row["nom_contact"] = str(ec.get("Nom", ""))
                    row["subscribers"] = str(ec.get("Abonnés", ""))
                    save_data = pd.concat([save_data, pd.DataFrame([row])], ignore_index=True)
                save_crm(save_data)
            st.balloons()
            st.success("🎉 Modifications sauvegardées (CSV local) !")
            st.rerun()

    st.markdown("---")

    # Export
    if is_gsheet and not df_dashboard.empty:
        export_df = df_dashboard.copy()
    elif not is_gsheet:
        export_df = load_crm()
    else:
        export_df = pd.DataFrame()

    if not export_df.empty:
        st.download_button(
            "📥 Exporter les données (CSV)",
            data=export_df.to_csv(index=False),
            file_name=f"suivi_campagnes_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            width="stretch",
        )


# ============================================================
# MAIN
# ============================================================

def main():
    st.markdown('<div class="main-title">☀️ CRM Influence Mon Kit Solaire</div>', unsafe_allow_html=True)

    # Citation solaire centrée sous le titre
    quote = random.choice(CITATIONS)
    st.markdown(f'<div class="main-subtitle" style="font-style:italic; color:#D97706; font-weight:600;">{quote}</div>', unsafe_allow_html=True)

    kw_input, max_per_kw, min_views, subs_range = render_sidebar()

    # Navigation par radio — seul l'onglet actif est rendu
    TAB_OPTIONS = ["🔍 Recherche", "📝 Prospection", "📈 Suivi Campagnes"]
    # Compatibilité avec anciennes sessions
    if st.session_state["active_tab"] not in TAB_OPTIONS:
        st.session_state["active_tab"] = TAB_OPTIONS[0]
    selected = st.radio(
        "Navigation",
        TAB_OPTIONS,
        index=TAB_OPTIONS.index(st.session_state["active_tab"]),
        horizontal=True,
        label_visibility="collapsed",
        key="nav_radio",
    )
    st.session_state["active_tab"] = selected

    st.markdown("---")

    if selected == "🔍 Recherche":
        tab_prospection(kw_input, max_per_kw, min_views, subs_range)
    elif selected == "📝 Prospection":
        tab_a_contacter()
    else:
        tab_suivi_campagnes()


if __name__ == "__main__":
    main()
