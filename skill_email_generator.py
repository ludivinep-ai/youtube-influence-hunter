"""
Skill Email Generator
Génère des brouillons d'emails personnalisés pour la prospection influenceurs.
Template Mon Kit Solaire avec personnalisation automatique.
"""

import re
import random
import urllib.parse


# ============================================================
# ACCROCHE PERSONNALISEE
# ============================================================

# Chaque pattern génère une accroche complète qui s'insère après
# "Je suis votre travail sur YouTube et "
# La phrase doit être autonome, naturelle et faire référence à la vidéo.

_ACCROCHE_PATTERNS = [
    # Rénovation / Travaux
    (r"rénovation|rénover|travaux|chantier",
     [
         'votre dernière vidéo "{title}" m\'a vraiment captivée — on sent toute la passion que vous mettez dans chaque chantier',
         'j\'ai été bluffée par votre vidéo "{title}", ça donne tellement envie de se lancer dans la rénovation',
         'votre vidéo "{title}" montre à quel point vous maîtrisez le sujet, c\'est un vrai plaisir à regarder',
     ]),
    # Transformation / Avant-Après
    (r"transform|avant.?après|relooking|était triste|regardez",
     [
         'votre vidéo "{title}" est une vraie pépite — le résultat avant/après est spectaculaire',
         'j\'ai adoré le rendu final dans "{title}", la transformation est vraiment impressionnante',
         'votre dernière vidéo "{title}" prouve une fois de plus votre talent pour métamorphoser les espaces',
     ]),
    # Bricolage / DIY
    (r"bricolage|bricol|diy|fabriqu|outil|atelier",
     [
         'votre vidéo "{title}" est exactement le genre de contenu pratique que j\'adore découvrir',
         'j\'ai regardé "{title}" avec beaucoup d\'intérêt — vos conseils bricolage sont toujours au top',
         'votre dernière vidéo "{title}" m\'a donné plein d\'idées, votre approche du bricolage est vraiment inspirante',
     ]),
    # Maison / Intérieur
    (r"maison|appartement|intérieur|déco|pièce|chambre|cuisine|salon",
     [
         'votre vidéo "{title}" donne des idées incroyables pour aménager son intérieur',
         'j\'ai adoré votre approche dans "{title}", on sent votre oeil pour créer des espaces de vie chaleureux',
         'votre dernière vidéo "{title}" m\'a convaincue que vous avez un vrai don pour sublimer les intérieurs',
     ]),
    # Jardin / Extérieur
    (r"jardin|extérieur|terrasse|piscine|abri|pergola|clôture",
     [
         'votre vidéo "{title}" m\'a donné envie de repenser tout mon extérieur — quel beau projet',
         'j\'ai été impressionnée par "{title}", votre vision de l\'aménagement extérieur est vraiment inspirante',
     ]),
    # Énergie / Solaire
    (r"solaire|panneau|énergi|électri|autoconsommation|watt",
     [
         'votre vidéo "{title}" tombe pile dans notre domaine et j\'ai trouvé votre approche très pertinente',
         'j\'ai regardé "{title}" avec attention — c\'est exactement le type de contenu qui parle à notre communauté aussi',
     ]),
    # Économies / Budget
    (r"économi|budget|prix|coût|astuce|pas cher|gratuit",
     [
         'votre vidéo "{title}" est remplie de bons conseils — vos astuces pour économiser sont vraiment précieuses',
         'j\'ai adoré "{title}", votre capacité à trouver des solutions malignes et économiques est impressionnante',
     ]),
    # Test / Review / Produit
    (r"test|avis|review|comparatif|produit|miracle|indispensable|meilleur",
     [
         'votre vidéo "{title}" était super complète — j\'apprécie beaucoup votre honnêteté dans vos tests',
         'j\'ai regardé "{title}" et votre façon de présenter les produits est vraiment engageante et crédible',
     ]),
    # Tuto / Guide
    (r"tuto|comment|guide|apprendre|étape|facile",
     [
         'votre vidéo "{title}" est un modèle de clarté — on comprend tout du premier coup grâce à vos explications',
         'j\'ai adoré "{title}", vos tutos sont parmi les plus accessibles que j\'ai vus sur YouTube',
     ]),
    # Abonnés / Communauté
    (r"abonn|communaut|merci|million|100k|50k",
     [
         'votre vidéo "{title}" montre à quel point votre communauté vous suit avec passion, et c\'est mérité',
         'j\'ai vu "{title}" et on ressent vraiment le lien authentique que vous avez avec votre audience',
     ]),
    # Peur / Défi / Challenge
    (r"peur|défi|challenge|oser|risqu|effondre|galèr",
     [
         'votre vidéo "{title}" m\'a tenue en haleine du début à la fin — j\'admire votre courage face aux défis',
         'j\'ai adoré "{title}", votre authenticité quand vous partagez les moments difficiles est vraiment touchante',
     ]),
]

_DEFAULT_ACCROCHES = [
    'votre dernière vidéo "{title}" m\'a beaucoup plu — votre énergie et votre authenticité sont vraiment communicatives',
    'j\'ai découvert votre vidéo "{title}" récemment et j\'ai tout de suite accroché à votre univers et votre bonne humeur',
    'votre vidéo "{title}" m\'a vraiment marquée — on sent la passion dans chaque minute de contenu que vous créez',
]

_NO_VIDEO_ACCROCHES = [
    "j'apprécie énormément la qualité et l'authenticité de vos vidéos — votre énergie est communicative",
    "votre contenu est vraiment passionnant, on sent une vraie passion et un vrai savoir-faire dans chacune de vos vidéos",
]


def generate_accroche(latest_video):
    """Génère une accroche personnalisée basée sur le titre de la dernière vidéo."""
    if not latest_video or latest_video == "N/A":
        return random.choice(_NO_VIDEO_ACCROCHES)

    title_clean = latest_video.strip()
    title_lower = title_clean.lower()

    for pattern, accroches in _ACCROCHE_PATTERNS:
        if re.search(pattern, title_lower):
            template = random.choice(accroches)
            return template.format(title=title_clean)

    # Fallback : référence directe au titre
    template = random.choice(_DEFAULT_ACCROCHES)
    return template.format(title=title_clean)


# ============================================================
# EMAIL GENERATOR
# ============================================================

_TEMPLATE = """Bonjour,

Je suis Ludivine de l'entreprise Mon Kit Solaire.

Je suis votre travail sur YouTube et {accroche} ! C'est précisément cette approche et votre bonne humeur qui nous donnent envie de collaborer avec vous.

Nous concevons des kits solaires en autoconsommation pensés pour être installés très facilement par des particuliers. Au vu de la hausse des prix de l'électricité, je suis convaincue que montrer une installation réelle et ses bénéfices intéresserait fortement votre communauté.

L'idée est simple : Nous vous envoyons gratuitement un kit complet (panneaux solaire, micro-onduleur, fixations) en échange de vidéo. C'est un produit que vous gardez, bien entendu.

Seriez-vous ouvert à une collaboration pour présenter cette solution sur votre chaîne ? Si oui, je serais ravie d'échanger d'avantage avec vous.

Dans l'attente de votre retour, je vous souhaite une excellente journée.

Bien cordialement,"""


_SUBJECTS = [
    "Collaboration ☀️ | Installation d'un kit solaire — {name} x Mon Kit Solaire",
    "Collaboration ☀️ | Kit solaire offert pour votre chaîne — {name} x Mon Kit Solaire",
    "Collaboration ☀️ | Vidéo partenaire kit solaire — {name} x Mon Kit Solaire",
]


def generate_email(channel_name, latest_video=""):
    """
    Génère le brouillon complet : objet + corps.

    Returns:
        tuple: (subject, body)
    """
    accroche = generate_accroche(latest_video)
    subject = random.choice(_SUBJECTS).format(name=channel_name)
    body = _TEMPLATE.format(accroche=accroche)
    return subject, body


def build_mailto_link(email, subject, body):
    """Construit un lien mailto: avec objet et corps pré-remplis."""
    params = urllib.parse.urlencode({
        "subject": subject,
        "body": body,
    }, quote_via=urllib.parse.quote)
    return f"mailto:{email}?{params}"
