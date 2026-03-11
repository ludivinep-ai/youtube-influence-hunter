"""
Skill Influence Scoring
Filtrage, classification et scoring des chaînes YouTube.
Prend des données brutes en entrée, ressort une liste analysée.
"""


# ============================================================
# CONFIGURATION
# ============================================================

# Exclusion : institutionnels, marques, hors-sujet
EXCLUDE_TERMS = [
    "ministère", "gouvernement", "mairie", "officiel", "préfecture",
    "edf", "engie", "totalenergies", "grdf",
    "ikea", "leroy merlin", "castorama", "brico dépôt", "brico depot",
    "samsung", "philips", "makita", "bosch",
    "football", "génétique", "yasmine", "slick slime", "girl crafts",
    "parti ", "politique", "municipale", "assemblée",
    "rev ", "révolution", "animaliste",
    "gâteau", "halloween", "skincare", "maquillage",
]

# Seuils de classification
THRESHOLD_LEADER = 150_000
THRESHOLD_MICRO = 20_000
THRESHOLD_NANO = 10_000

# Critère éliminatoire
MIN_AVG_VIEWS = 10_000

# Seuil d'affichage final
MIN_SCORE_DISPLAY = 7


# ============================================================
# FILTRAGE
# ============================================================

def is_excluded(name):
    """Vérifie si un nom de chaîne correspond à un terme exclu."""
    name_lower = name.lower()
    return any(term in name_lower for term in EXCLUDE_TERMS)


def filter_channels(channels):
    """
    Filtre une liste de chaînes brutes.
    Supprime les institutionnels/marques et les doublons.
    Entrée : liste de dict {name, url, ...}
    Sortie : dict url -> channel (dédupliqué, filtré)
    """
    filtered = {}
    for ch in channels:
        if is_excluded(ch["name"]):
            continue
        url = ch["url"]
        if url not in filtered:
            filtered[url] = ch
    return filtered


# ============================================================
# CLASSIFICATION
# ============================================================

def classify(subscribers):
    """Classifie une chaîne selon son nombre d'abonnés."""
    if subscribers is None:
        return "Inconnu"
    if subscribers >= THRESHOLD_LEADER:
        return "Leader d'opinion"
    if subscribers >= THRESHOLD_MICRO:
        return "Micro pepite"
    if subscribers >= THRESHOLD_NANO:
        return "Nano pepite"
    return "Petite chaine"


# ============================================================
# SCORING
# ============================================================

def compute_score(channel):
    """
    Scoring sur 10 :
      +5 si avg_views >= 15 000 (garantie de visibilité)
      +3 si Nano ou Micro pépite (meilleure authenticité)
      +2 si contact détecté (mail, insta, site)
    """
    score = 0

    avg = channel.get("avg_views")
    if avg is not None and avg >= 15_000:
        score += 5

    cat = channel.get("category", "")
    if cat in ("Nano pepite", "Micro pepite"):
        score += 3

    if channel.get("contact"):
        score += 2

    return score


# ============================================================
# PIPELINE COMPLET
# ============================================================

def analyze(channels_dict):
    """
    Pipeline d'analyse complet.
    Entrée : dict url -> channel avec données brutes (subscribers, avg_views, contact, etc.)
    Sortie : (qualified, eliminated_low_views, eliminated_no_data)
      - qualified : liste de channels triée par score, avec catégorie et score ajoutés
    """
    qualified = []
    eliminated_low_views = 0
    eliminated_no_data = 0

    for url, ch in channels_dict.items():
        ch["category"] = classify(ch.get("subscribers"))
        avg = ch.get("avg_views")

        if avg is None:
            eliminated_no_data += 1
            continue
        if avg < MIN_AVG_VIEWS:
            eliminated_low_views += 1
            continue

        ch["score"] = compute_score(ch)
        qualified.append(ch)

    qualified.sort(key=lambda c: (c["score"], c.get("avg_views") or 0), reverse=True)

    return qualified, eliminated_low_views, eliminated_no_data


def get_top(qualified, min_score=None):
    """Filtre les chaînes qualifiées par score minimum."""
    if min_score is None:
        min_score = MIN_SCORE_DISPLAY
    return [ch for ch in qualified if ch["score"] >= min_score]
