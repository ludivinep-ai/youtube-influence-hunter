"""
Skill Contact Finder
Stratégie de contournement Captcha YouTube :
1. Scan des descriptions des 3 dernières vidéos (emails, mots-clés contact)
2. Détection de liens sociaux (Linktree, Instagram, TikTok, sites perso)
3. Résultat structuré pour affichage intelligent dans le CRM
"""

import re
from engine_youtube_scraper import safe_get, get_yt_initial_data, clean_yt_text


# ============================================================
# EXTRACTION EMAILS
# ============================================================

# Extensions de fichiers à ignorer (faux positifs)
_FAKE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4", ".pdf"}

# Mots-clés qui signalent un email de contact business
_BUSINESS_KEYWORDS = [
    "contact", "business", "pro", "collab", "partenariat",
    "partnership", "sponsor", "presse", "press", "commercial",
]


def extract_emails(text):
    """Extrait les adresses email, en priorisant les emails business."""
    raw = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
    # Dédupliquer en gardant l'ordre
    seen = set()
    emails = []
    for e in raw:
        low = e.lower()
        if low in seen:
            continue
        seen.add(low)
        # Filtrer les faux positifs (extensions fichiers)
        if any(low.endswith(ext) for ext in _FAKE_EXTENSIONS):
            continue
        emails.append(e)

    # Trier : emails business en premier
    business = [e for e in emails if any(kw in e.lower() for kw in _BUSINESS_KEYWORDS)]
    others = [e for e in emails if e not in business]
    return business + others


# ============================================================
# EXTRACTION LIENS SOCIAUX
# ============================================================

def extract_social_links(text):
    """Extrait les liens Instagram, TikTok, Linktree et sites perso."""
    links = {}

    # Instagram
    m = re.search(r'https?://(?:www\.)?instagram\.com/([\w.]+)', text)
    if m:
        links["instagram"] = f"https://www.instagram.com/{m.group(1)}"

    # TikTok
    m = re.search(r'https?://(?:www\.)?tiktok\.com/@([\w.]+)', text)
    if m:
        links["tiktok"] = f"https://www.tiktok.com/@{m.group(1)}"

    # Linktree
    m = re.search(r'https?://(?:www\.)?linktr\.ee/([\w.]+)', text)
    if m:
        links["linktree"] = f"https://linktr.ee/{m.group(1)}"

    # Site perso (hors plateformes connues et CDN d'images)
    _exclude = (
        "youtube", "ytimg", "googlevideo", "ggpht",
        "google", "gstatic", "googleapis",
        "instagram", "tiktok", "twitter", "x.com",
        "facebook", "linktr", "twitch", "discord", "reddit",
        "amazon", "amzn", "bit.ly", "t.co", "imgur",
    )
    _img_ext = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp")
    for site_m in re.finditer(
        r'https?://(?:www\.)?([\w.-]+\.\w{2,})(?:/[^\s"<>]*)?', text
    ):
        full_url = site_m.group(0).lower()
        domain = site_m.group(1).lower()
        # Exclure les plateformes connues
        if any(ex in domain for ex in _exclude):
            continue
        # Exclure les URLs qui pointent vers des images
        if any(full_url.split("?")[0].endswith(ext) for ext in _img_ext):
            continue
        links["site"] = site_m.group(0)
        break

    return links


# ============================================================
# EXTRACTION DESCRIPTIONS VIDEOS
# ============================================================

def get_video_ids_from_yt_data(yt_data, max_videos=3):
    """Extrait les IDs des premières vidéos depuis ytInitialData de /videos."""
    ids = []
    for m in re.finditer(r'"videoId"\s*:\s*"([\w-]{11})"', yt_data):
        vid = m.group(1)
        if vid not in ids:
            ids.append(vid)
        if len(ids) >= max_videos:
            break
    return ids


def scrape_video_description(driver, video_id):
    """Extrait la description d'une vidéo depuis sa page."""
    safe_get(driver, f"https://www.youtube.com/watch?v={video_id}")
    yt_data, _ = get_yt_initial_data(driver)
    if not yt_data:
        return ""

    # Tenter attributedDescription (format moderne)
    m = re.search(r'"attributedDescription"\s*:\s*\{[^}]*"content"\s*:\s*"([^"]*)"', yt_data)
    if not m:
        # Fallback: description simpleText
        m = re.search(r'"description"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]*)"', yt_data)
    if m:
        return m.group(1).replace("\\n", "\n").replace("\\u0026", "&").replace("\\u003d", "=")
    return ""


# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def find_contacts(driver, channel_url, yt_data_videos=None):
    """
    Recherche approfondie de contacts pour une chaîne YouTube.

    Stratégie :
    1. Page profil/about : emails + liens dans les métadonnées
    2. Descriptions des 3 dernières vidéos : emails + liens sociaux

    Args:
        driver: Selenium WebDriver
        channel_url: URL de la chaîne
        yt_data_videos: ytInitialData de /videos (optionnel, évite un chargement)

    Returns:
        dict: {
            "emails": ["email@example.com", ...],
            "social": {"instagram": "url", "tiktok": "url", ...},
        }
    """
    all_text = ""

    # 1. Page profil (about)
    about_url = channel_url.rstrip("/") + "/about"
    safe_get(driver, about_url)
    yt_data, source = get_yt_initial_data(driver)
    if yt_data:
        all_text += yt_data

    # 2. Récupérer les IDs vidéo depuis /videos
    if not yt_data_videos:
        safe_get(driver, channel_url.rstrip("/") + "/videos")
        yt_data_videos, _ = get_yt_initial_data(driver)

    video_ids = []
    if yt_data_videos:
        video_ids = get_video_ids_from_yt_data(yt_data_videos, max_videos=3)

    # 3. Scanner les descriptions des 3 dernières vidéos
    for vid in video_ids:
        desc = scrape_video_description(driver, vid)
        if desc:
            all_text += "\n" + desc

    # 4. Extraire emails et liens
    emails = extract_emails(all_text)
    social = extract_social_links(all_text)

    return {
        "emails": emails,
        "social": social,
    }


def format_contact_tags(contact_result):
    """
    Convertit le résultat find_contacts en liste de tags pour le champ 'contact'.
    Compatible avec le format existant (["Mail", "Insta", "Site"]).
    """
    tags = []
    if contact_result.get("emails"):
        tags.append("Mail")
    social = contact_result.get("social", {})
    if "instagram" in social:
        tags.append("Insta")
    if "tiktok" in social:
        tags.append("TikTok")
    if "linktree" in social:
        tags.append("Linktree")
    if "site" in social:
        tags.append("Site")
    return tags
