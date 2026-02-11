import re
import unicodedata
from psycopg2.extras import execute_values
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scraper.db import get_conn
from scraper.fetch import fetch_rendered_html

URL = "https://www.footmercato.net/france/ligue-1/buteur"
SEASON = "2025/2026"
BASE = "https://www.footmercato.net"

def clean_player_name(raw_name):
    """ Enlève les postes (BU, MC...) collés au nom du joueur """
    postes = ["BU", "AD", "AG", "MC", "MD", "MG", "DG", "DD", "DC", "G", "MIL", "M", "D"]
    parts = raw_name.split()
    if not parts:
        return ""
    if parts[-1].upper() in postes:
        parts.pop()
    return " ".join(parts).strip()

def parse_scorers(html: str):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        raise RuntimeError("Table des buteurs introuvable.")

    rows = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        # 1. Rang
        rank_txt = tds[0].get_text(strip=True)
        rank = int(rank_txt) if rank_txt.isdigit() else 0

        # 2. Joueur (Nettoyage + Photo)
        player_td = tds[1]
        raw_name = player_td.get_text(" ", strip=True)
        player_name = clean_player_name(raw_name)
        
        photo_url = None
        img_player = player_td.find("img")
        if img_player:
            photo_url = img_player.get("data-src") or img_player.get("src")
            if photo_url and not photo_url.startswith("http"):
                photo_url = urljoin(BASE, photo_url)

        # 3. Club (Logo)
        logo_url = None
        imgs = tr.find_all("img")
        if len(imgs) >= 2:
            src = imgs[1].get("data-src") or imgs[1].get("src")
            logo_url = urljoin(BASE, src)

        # 4. Buts (souvent colonne 3) et Penaltys (colonne 4)
        try:
            goals = int(tds[2].get_text(strip=True) or 0)
            penalties = int(tds[3].get_text(strip=True) or 0)
        except ValueError:
            goals, penalties = 0, 0

        if player_name:
            rows.append({
                "season": SEASON,
                "rank": rank,
                "player_name": player_name,
                "team": None,
                "goals": goals,
                "penalties": penalties,
                "photo_url": photo_url,
                "logo_url": logo_url
            })

    return rows

def upsert_scorers(rows):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE scorers ADD COLUMN IF NOT EXISTS photo_url TEXT;")
            cur.execute("ALTER TABLE scorers ADD COLUMN IF NOT EXISTS logo_url TEXT;")
    
    sql = """
    INSERT INTO scorers (season, rank, player_name, team, goals, penalties, photo_url, logo_url)
    VALUES %s
    ON CONFLICT (season, player_name)
    DO UPDATE SET
      rank = EXCLUDED.rank,
      goals = EXCLUDED.goals,
      penalties = EXCLUDED.penalties,
      photo_url = EXCLUDED.photo_url,
      logo_url = EXCLUDED.logo_url,
      scraped_at = CURRENT_TIMESTAMP;
    """
    values = [
        (r["season"], r["rank"], r["player_name"], r["team"], 
         r["goals"], r["penalties"], r["photo_url"], r["logo_url"]) 
        for r in rows
    ]

    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
    finally:
        conn.close()

def main():
    html = fetch_rendered_html(URL, wait_text="Buteurs")
    rows = parse_scorers(html)
    upsert_scorers(rows)
    print(f"✅ OK: {len(rows)} buteurs mis à jour avec images et noms nettoyés.")

if __name__ == "__main__":
    main()