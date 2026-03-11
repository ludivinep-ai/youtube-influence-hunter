"""
Engine YouTube Scraper
Logique Selenium pure : recherche de chaînes, extraction abonnés, vues, contact.
Aucune règle de score ici — uniquement de l'extraction de données brutes.
"""

import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# DRIVER & NAVIGATION
# ============================================================

def create_driver():
    """Crée un driver Chrome headless et accepte le consentement cookies."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=fr-FR")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Accepter le consentement une seule fois au démarrage
    driver.get("https://www.youtube.com")
    time.sleep(2)
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            txt = btn.text.strip().lower()
            if any(w in txt for w in ["tout accepter", "accept all", "j'accepte"]):
                btn.click()
                time.sleep(3)
                print("  [Init] Consentement cookies accepte")
                break
    except Exception:
        pass

    return driver


def safe_get(driver, url):
    """Navigue vers une URL."""
    driver.get(url)
    time.sleep(3)


def get_yt_initial_data(driver):
    """Extrait ytInitialData du page source courant."""
    source = driver.page_source
    m = re.search(r'var\s+ytInitialData\s*=\s*(\{.+?\});\s*</', source, re.DOTALL)
    return (m.group(1), source) if m else (None, source)


# ============================================================
# PARSING TEXTE YOUTUBE
# ============================================================

def clean_yt_text(text):
    """Nettoie un texte YouTube : décode unicode escapes, normalise espaces."""
    text = text.replace('\\u00a0', ' ').replace('\\u202f', ' ')
    text = text.replace('\xa0', ' ').replace('\u202f', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_number(text):
    """Parse un nombre YouTube FR/EN (abonnés ou vues)."""
    if not text:
        return None
    text = clean_yt_text(text).lower()
    match = re.search(r'([\d.,\s]+)\s*(k|m|b|mille|million|milliard)?', text, re.IGNORECASE)
    if match:
        num_str = match.group(1).strip().replace(' ', '').replace(',', '.')
        unit = (match.group(2) or "").lower()
        multipliers = {
            'k': 1_000, 'mille': 1_000,
            'm': 1_000_000, 'million': 1_000_000,
            'b': 1_000_000_000, 'milliard': 1_000_000_000,
        }
        try:
            return int(float(num_str) * multipliers.get(unit, 1))
        except Exception:
            pass
    return None


def fmt(n):
    """Formate un nombre pour affichage compact (ex: 132k, 1.5M)."""
    if n is None:
        return "?"
    if n >= 1_000_000:
        v = n / 1_000_000
        return f"{v:.0f}M" if v == int(v) else f"{v:.1f}M"
    if n >= 1_000:
        v = n / 1_000
        return f"{v:.0f}k" if v == int(v) else f"{v:.1f}k"
    return str(n)


# ============================================================
# RECHERCHE DE CHAINES
# ============================================================

def search_channels(driver, keyword, max_results=10):
    """
    Recherche YouTube filtrée "Chaîne" pour un mot-clé.
    Retourne une liste de dict bruts : {name, url, handle, channel_id}
    """
    search_url = (
        f"https://www.youtube.com/results"
        f"?search_query={keyword.replace(' ', '+')}"
        f"&sp=EgIQAg%3D%3D"
    )
    safe_get(driver, search_url)

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(1.5)

    yt_data, _ = get_yt_initial_data(driver)
    if not yt_data:
        return []

    channels = []
    for m in re.finditer(
        r'"channelRenderer"\s*:\s*\{[^}]*?"channelId"\s*:\s*"(UC[^"]+)"', yt_data
    ):
        if len(channels) >= max_results:
            break

        channel_id = m.group(1)
        block = yt_data[m.start():m.start() + 3000]

        name_match = re.search(r'"simpleText"\s*:\s*"([^"]+)"', block)
        name = name_match.group(1) if name_match else "Inconnu"

        handle_match = re.search(r'"canonicalBaseUrl"\s*:\s*"(/(@[^"]+))"', block)
        handle = handle_match.group(2) if handle_match else None
        url = f"https://www.youtube.com/{handle}" if handle else f"https://www.youtube.com/channel/{channel_id}"

        if any(c["url"] == url for c in channels):
            continue

        channels.append({
            "name": name, "url": url,
            "handle": handle, "channel_id": channel_id,
        })

    return channels


# ============================================================
# EXTRACTION ABONNES
# ============================================================

def scrape_subscribers(yt_data):
    """Extrait le nombre d'abonnés depuis ytInitialData."""
    patterns = [
        r'"content"\s*:\s*"([\d.,]+(?:\\u00a0|\s)*(?:k|m|b)?(?:\\u00a0|\s)*(?:abonn[^"]*|subscri[^"]*?))"',
        r'"accessibilityLabel"\s*:\s*"([\d.,]+\s*(?:mille|million|milliard)?[^"]*(?:abonn[^"]*?))"',
        r'"subscriberCountText"[^}]*?"simpleText"\s*:\s*"([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, yt_data, re.IGNORECASE)
        if m:
            raw = m.group(1).replace('\\u00a0', ' ')
            val = parse_number(raw)
            if val is not None:
                return val
    return None


# ============================================================
# EXTRACTION VUES & DERNIERE VIDEO
# ============================================================

def scrape_views_and_videos(yt_data):
    """
    Extrait les vues des 6 premières vidéos depuis ytInitialData de /videos.
    Retourne (avg_views, latest_title, views_list, latest_published)
    """
    views = []
    latest_title = "N/A"
    latest_published = ""

    view_matches = list(re.finditer(
        r'"viewCountText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
        yt_data
    ))

    for vm in view_matches[:6]:
        raw = clean_yt_text(vm.group(1))
        v = parse_number(raw)
        if v is not None:
            views.append(v)

    if view_matches:
        first_view_pos = view_matches[0].start()
        chunk_before = yt_data[max(0, first_view_pos - 2000):first_view_pos]
        title_matches = list(re.finditer(
            r'"title"\s*:\s*\{[^}]*"text"\s*:\s*"([^"]{5,})"', chunk_before
        ))
        if title_matches:
            latest_title = clean_yt_text(title_matches[-1].group(1))[:80]

        # Extraire la date de publication de la première vidéo
        chunk_after = yt_data[first_view_pos:first_view_pos + 500]
        pub_match = re.search(
            r'"publishedTimeText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
            chunk_after
        )
        if not pub_match:
            pub_match = re.search(
                r'"publishedTimeText"\s*:\s*\{\s*"simpleText"\s*:\s*"([^"]+)"',
                yt_data[:first_view_pos + 2000]
            )
        if pub_match:
            latest_published = clean_yt_text(pub_match.group(1))

    avg = int(sum(views) / len(views)) if views else None
    return avg, latest_title, views, latest_published


# ============================================================
# EXTRACTION CONTACT
# ============================================================

def scrape_contact_info(yt_data, page_source):
    """Détecte la présence d'infos de contact (mail, insta, site externe)."""
    search_text = yt_data + page_source
    found = []
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', search_text):
        found.append("Mail")
    if re.search(r'instagram\.com/', search_text, re.IGNORECASE):
        found.append("Insta")
    if re.search(
        r'"urlEndpoint"[^}]*"url"\s*:\s*"(https?://(?!www\.youtube|accounts\.google|play\.google)[^"]+)"',
        search_text
    ):
        found.append("Site")
    return found


# ============================================================
# SCRAPING COMPLET D'UNE CHAINE
# ============================================================

def scrape_channel_full(driver, channel_url):
    """
    Scraping complet d'une chaîne :
    1. Page profil -> abonnés + contact
    2. Page /videos -> vues moy 6 vidéos + titre dernière vidéo

    Retourne un dict de données brutes.
    Inclut "_yt_data_videos" pour réutilisation par le contact finder.
    """
    result = {
        "subscribers": None,
        "avg_views": None,
        "latest_video": "N/A",
        "latest_published": "",
        "views_list": [],
        "contact": [],
        "_yt_data_videos": None,
    }

    try:
        # Page profil
        safe_get(driver, channel_url)
        yt_data, source = get_yt_initial_data(driver)

        if yt_data:
            result["subscribers"] = scrape_subscribers(yt_data)
            result["contact"] = scrape_contact_info(yt_data, source)

        # Page /videos
        safe_get(driver, channel_url.rstrip("/") + "/videos")
        yt_data_v, _ = get_yt_initial_data(driver)

        if yt_data_v:
            result["_yt_data_videos"] = yt_data_v
            avg, latest, vlist, published = scrape_views_and_videos(yt_data_v)
            result["avg_views"] = avg
            result["latest_video"] = latest
            result["views_list"] = vlist
            result["latest_published"] = published

        # Fallback DOM
        if result["latest_video"] == "N/A":
            try:
                el = driver.find_element(By.CSS_SELECTOR, "#video-title")
                txt = el.text.strip()
                if txt:
                    result["latest_video"] = txt[:80]
            except Exception:
                pass

    except Exception:
        pass

    return result
