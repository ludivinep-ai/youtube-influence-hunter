"""
Main Influencer Hunter
Script principal : orchestre le scraping et le scoring
pour détecter les influenceurs YouTube à haut ROI.
"""

import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from engine_youtube_scraper import (
    create_driver, search_channels, scrape_channel_full, fmt,
)
from skill_influence_scoring import (
    is_excluded, analyze, get_top,
    MIN_AVG_VIEWS, MIN_SCORE_DISPLAY,
)
from skill_contact_finder import find_contacts, format_contact_tags


# ============================================================
# CONFIGURATION
# ============================================================

KEYWORDS = [
    "rénovation maison",
    "bricolage",
    "autoconsommation",
    "écologique",
    "rénover soi même",
]

MAX_CHANNELS_PER_KEYWORD = 10


# ============================================================
# AFFICHAGE
# ============================================================

def print_results(top, total_scraped, total_qualified):
    """Affiche le tableau Markdown final + détails."""

    if not top:
        print("\n  Aucune chaine ne depasse le seuil de score >= 7.")
        print("  Voici les meilleures qualifiees :")

    print("\n")
    print("=" * 105)
    print("  INFLUENCEURS YOUTUBE A HAUT ROI - SCORE >= 7/10")
    print("=" * 105)
    print()

    header = f"| {'#':>2} | {'Chaine':<26} | {'Abonnes':>8} | {'Vues moy':>9} | {'Categorie':<18} | {'Score':>5} | {'Contact':<9} |"
    sep = f"|{'-'*4}|{'-'*28}|{'-'*10}|{'-'*11}|{'-'*20}|{'-'*7}|{'-'*11}|"
    print(header)
    print(sep)

    for rank, ch in enumerate(top, 1):
        name = ch["name"].replace("\\u0026", "&")[:26]
        subs = fmt(ch.get("subscribers"))
        avg_v = fmt(ch.get("avg_views"))
        cat = ch["category"][:18]
        score = f"{ch['score']}/10"
        contact = "Oui" if ch.get("contact") else "Non"
        print(f"| {rank:>2} | {name:<26} | {subs:>8} | {avg_v:>9} | {cat:<18} | {score:>5} | {contact:<9} |")

    print(sep)

    # Détails
    print("\n  Details :")
    for rank, ch in enumerate(top, 1):
        name = ch["name"].replace("\\u0026", "&")[:26]
        contact_detail = ", ".join(ch.get("contact", [])) or "Aucun"
        video = (ch.get("latest_video") or "N/A")[:55]
        vues_detail = ", ".join(fmt(v) for v in ch.get("views_list", []))
        print(f"  {rank:>2}. {name}")
        print(f"      URL     : {ch['url']}")
        print(f"      Contact : {contact_detail}")
        print(f"      Video   : {video}")
        print(f"      Vues 6v : [{vues_detail}]")
        print()

    # Stats
    cats = {}
    for ch in top:
        c = ch["category"]
        cats[c] = cats.get(c, 0) + 1
    print(f"  --- Bilan ---")
    print(f"  Total scrapees : {total_scraped} | Qualifiees : {total_qualified} | Affichees (score>={MIN_SCORE_DISPLAY}) : {len(top)}")
    for c, n in sorted(cats.items()):
        print(f"    {c}: {n}")


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 70)
    print("  DETECTION D'INFLUENCEURS YOUTUBE A HAUT ROI")
    print("  Cible : kits solaires | Personas : Manu & Didier")
    print("=" * 70)

    driver = create_driver()
    all_channels = {}

    try:
        # --- PHASE 1 : Recherche ---
        print("\n[Phase 1/3] Recherche de chaines par mot-cle...")

        for kw in KEYWORDS:
            print(f"\n  '{kw}'", end="", flush=True)
            results = search_channels(driver, kw, max_results=MAX_CHANNELS_PER_KEYWORD)
            count = 0
            for ch in results:
                if is_excluded(ch["name"]):
                    continue
                url = ch["url"]
                if url not in all_channels:
                    all_channels[url] = {
                        "name": ch["name"], "url": url,
                        "handle": ch["handle"], "keywords": [kw],
                    }
                    count += 1
                else:
                    all_channels[url]["keywords"].append(kw)
            print(f" -> {count} nouvelles ({len(results)} brutes)")

        total = len(all_channels)
        print(f"\n  -> {total} chaines uniques")

        # --- PHASE 2 : Scraping profond ---
        print(f"\n[Phase 2/3] Scraping profond ({total} chaines)...")
        print(f"  {'#':>4}  {'Chaine':<28} {'Abos':>7} {'Vues moy':>9} {'Vids':>4}  Contact")
        print(f"  {'-'*4}  {'-'*28} {'-'*7} {'-'*9} {'-'*4}  {'-'*10}")

        for i, (url, ch) in enumerate(all_channels.items(), 1):
            name_short = ch["name"].replace("\\u0026", "&")[:28]
            print(f"  {i:>4}  {name_short:<28}", end=" ", flush=True)

            data = scrape_channel_full(driver, url)
            ch.update(data)

            # Recherche approfondie de contacts
            try:
                contact_result = find_contacts(
                    driver, url,
                    yt_data_videos=data.get("_yt_data_videos"),
                )
                ch["email"] = contact_result["emails"][0] if contact_result["emails"] else ""
                ch["social_links"] = contact_result.get("social", {})
                ch["contact"] = format_contact_tags(contact_result) or ch.get("contact", [])
            except Exception:
                ch["email"] = ""
                ch["social_links"] = {}
            ch.pop("_yt_data_videos", None)

            s = fmt(ch["subscribers"])
            v = fmt(ch["avg_views"])
            n_vids = len(ch["views_list"])
            contact_disp = ch.get("email") or ", ".join(ch["contact"]) if ch["contact"] else "-"
            print(f"{s:>7} {v:>9} {n_vids:>4}  {contact_disp}")

    finally:
        driver.quit()

    # --- PHASE 3 : Scoring ---
    print(f"\n[Phase 3/3] Classification et scoring...")

    qualified, elim_views, elim_nodata = analyze(all_channels)
    top = get_top(qualified)

    print(f"\n  Eliminees (vues moy < {MIN_AVG_VIEWS:,}) : {elim_views}")
    print(f"  Eliminees (pas de data)       : {elim_nodata}")
    print(f"  Qualifiees (vues >= {MIN_AVG_VIEWS:,})    : {len(qualified)}")
    print(f"  Score >= {MIN_SCORE_DISPLAY}                    : {len(top)}")

    # Fallback si aucune >= 7
    if not top:
        top = qualified[:15]

    print_results(top, len(all_channels), len(qualified))


if __name__ == "__main__":
    main()
