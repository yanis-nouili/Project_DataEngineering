import re
import unicodedata
from psycopg2.extras import execute_values
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scraper.db import get_conn
from scraper.fetch import fetch_rendered_html

URL = "https://www.footmercato.net/france/ligue-1/passeur"
SEASON = "2025/2026"
BASE = "https://www.footmercato.net"

def clean_player_name(raw_name):
    """
    Supprime le poste (ex: MC, BU, DG) s'il est collé à la fin du nom.
    """
    # Liste des postes affichés sur Foot Mercato
    postes = {
        "BU", "AD", "AG", "MC", "MD", "MG", 
        "DG", "DD", "DC", "G", "MIL", "M", "D"
    }
    
    parts = raw_name.split()
    if not parts:
        return ""
    
    # Si le dernier mot est dans notre liste de postes, on l'enlève
    if parts[-1].upper() in postes:
        parts.pop()
        
    return " ".join(parts).strip()

def parse_assists(html: str):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        raise RuntimeError("Table des passeurs introuvable.")

    rows = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        # 1. Rang
        rank_txt = tds[0].get_text(strip=True)
        rank = int(rank_txt) if rank_txt.isdigit() else 0

        # 2. Joueur (Nettoyage du nom + Photo)
        player_td = tds[1]
        raw_name = player_td.get_text(" ", strip=True)
        player_name = clean_player_name(raw_name) # Nettoyage ici
        
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

        # 4. Passes
        assists_val = 0
        for td in tds[2:]:
            txt = td.get_text(strip=True)
            if txt.isdigit():
                assists_val = int(txt)
                break

        if player_name:
            rows.append({
                "season": SEASON,
                "rank": rank,
                "player_name": player_name,
                "team": None,
                "assists": assists_val,
                "photo_url": photo_url,
                "logo_url": logo_url
            })
    return rows

def upsert_assists(rows):
    conn = get_conn()
    sql = """
    INSERT INTO assists (season, rank, player_name, team, assists, photo_url, logo_url)
    VALUES %s
    ON CONFLICT (season, player_name, team)
    DO UPDATE SET
      rank = EXCLUDED.rank,
      assists = EXCLUDED.assists,
      photo_url = EXCLUDED.photo_url,
      logo_url = EXCLUDED.logo_url,
      scraped_at = CURRENT_TIMESTAMP;
    """
    values = [(r["season"], r["rank"], r["player_name"], r["team"], 
               r["assists"], r["photo_url"], r["logo_url"]) for r in rows]

    try:
        with conn:
            with conn.cursor() as cur:
                # Ajout des colonnes si besoin
                cur.execute("ALTER TABLE assists ADD COLUMN IF NOT EXISTS photo_url TEXT;")
                cur.execute("ALTER TABLE assists ADD COLUMN IF NOT EXISTS logo_url TEXT;")
                execute_values(cur, sql, values)
    finally:
        conn.close()

def main():
    html = fetch_rendered_html(URL, wait_text="Passeurs")
    rows = parse_assists(html)
    upsert_assists(rows)
    print(f"✅ OK: {len(rows)} passeurs mis à jour (noms nettoyés).")

if __name__ == "__main__":
    main()