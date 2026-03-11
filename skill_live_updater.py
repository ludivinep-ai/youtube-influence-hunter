"""
Skill Live Updater
Re-scrape les statistiques YouTube (abonnés, vues moyennes) pour une liste de chaînes
et met à jour le DataFrame en temps réel.
"""

from engine_youtube_scraper import (
    create_driver, safe_get, get_yt_initial_data,
    scrape_subscribers, scrape_views_and_videos, fmt,
)


def rescrape_channel_stats(driver, channel_url):
    """
    Re-scrape les stats d'une chaîne YouTube.

    Returns:
        dict: {"subscribers": int|None, "avg_views": int|None, "latest_video": str}
    """
    result = {"subscribers": None, "avg_views": None, "latest_video": "N/A"}

    try:
        # Page profil -> abonnés
        safe_get(driver, channel_url)
        yt_data, _ = get_yt_initial_data(driver)
        if yt_data:
            result["subscribers"] = scrape_subscribers(yt_data)

        # Page /videos -> vues moyennes
        safe_get(driver, channel_url.rstrip("/") + "/videos")
        yt_data_v, _ = get_yt_initial_data(driver)
        if yt_data_v:
            avg, latest, vlist, published = scrape_views_and_videos(yt_data_v)
            result["avg_views"] = avg
            result["latest_video"] = latest
    except Exception:
        pass

    return result


def bulk_rescrape(urls, progress_callback=None):
    """
    Re-scrape les stats pour une liste d'URLs de chaînes.

    Args:
        urls: list of channel URLs
        progress_callback: callable(i, total, name, stats) appelé après chaque chaîne

    Returns:
        dict: {url: {"subscribers": ..., "avg_views": ..., "latest_video": ...}}
    """
    results = {}
    driver = create_driver()

    try:
        for i, url in enumerate(urls):
            stats = rescrape_channel_stats(driver, url)
            results[url] = stats
            if progress_callback:
                progress_callback(i + 1, len(urls), url, stats)
    finally:
        driver.quit()

    return results
