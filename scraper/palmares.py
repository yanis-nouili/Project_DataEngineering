import requests
from bs4 import BeautifulSoup
import psycopg2
import os
import re
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

URL = "https://www.footmercato.net/france/ligue-1/palmares"
BASE = "https://www.footmercato.net"

def get_conn():
    return psycopg2.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
    )

def scrape_palmares():
    r = requests.get(URL)
    r.encoding = r.apparent_encoding 
    soup = BeautifulSoup(r.text, "html.parser")

    clubs = []
    history = []

    # ======================
    # 1. TOP CLUBS (Avec Logos)
    # ======================
    for block in soup.find_all("div"):
        text = block.get_text(" ", strip=True)
        if text and any(char.isdigit() for char in text):
            parts = text.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                try:
                    titles = int(parts[-1])
                    team = " ".join(parts[:-1])
                    
                    if len(team) > 35 or titles > 30 or titles == 0:
                        continue
                    
                    blacklist = ["top", "vainqueur", "champion", "ligue", "classement"]
                    if any(word in team.lower() for word in blacklist):
                        continue

                    logo_url = None
                    img = block.find("img")
                    if img:
                        src = (img.get("data-src") or img.get("data-lazy-src") or 
                               img.get("src") or img.get("srcset"))
                        if src:
                            if " " in src and "," in src:
                                src = src.split(",")[0].strip().split(" ")[0].strip()
                            if not src.startswith("data:image"):
                                logo_url = urljoin(BASE, src)

                    clubs.append((team, titles, logo_url))
                except ValueError:
                    continue

    # ======================
    # 2. HISTORIQUE (Avec Logos Champion/Finaliste)
    # ======================
    table = soup.find("table")
    if table:
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) >= 3:
                season = cols[0].text.strip()
                
                # Extraction Champion + Logo
                winner_name = cols[1].text.strip()
                winner_logo = None
                img_w = cols[1].find("img")
                if img_w:
                    src_w = img_w.get("data-src") or img_w.get("src")
                    if src_w: winner_logo = urljoin(BASE, src_w)

                # Extraction Finaliste + Logo
                runner_name = cols[2].text.strip()
                runner_logo = None
                img_r = cols[2].find("img")
                if img_r:
                    src_r = img_r.get("data-src") or img_r.get("src")
                    if src_r: runner_logo = urljoin(BASE, src_r)

                history.append((season, winner_name, winner_logo, runner_name, runner_logo))

    return clubs, history

def save_db(clubs, history):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            # On s'assure que les colonnes existent (au cas où)
            cur.execute("ALTER TABLE palmares_history ADD COLUMN IF NOT EXISTS winner_logo TEXT;")
            cur.execute("ALTER TABLE palmares_history ADD COLUMN IF NOT EXISTS runner_up_logo TEXT;")
            cur.execute("ALTER TABLE palmares_clubs ADD COLUMN IF NOT EXISTS logo_url TEXT;")

            for team, titles, logo in clubs:
                cur.execute("""
                    INSERT INTO palmares_clubs(team, titles, logo_url)
                    VALUES (%s, %s, %s)
                    ON CONFLICT(team)
                    DO UPDATE SET titles = EXCLUDED.titles, logo_url = EXCLUDED.logo_url;
                """, (team, titles, logo))

            for season, w_name, w_logo, r_name, r_logo in history:
                cur.execute("""
                    INSERT INTO palmares_history(season, winner, winner_logo, runner_up, runner_up_logo)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(season)
                    DO UPDATE SET 
                        winner=EXCLUDED.winner, winner_logo=EXCLUDED.winner_logo,
                        runner_up=EXCLUDED.runner_up, runner_up_logo=EXCLUDED.runner_up_logo;
                """, (season, w_name, w_logo, r_name, r_logo))
    conn.close()

if __name__ == "__main__":
    print("🚀 Scraping des palmarès et des logos...")
    c, h = scrape_palmares()
    save_db(c, h)
    print(f"✅ Terminé ! {len(c)} clubs et {len(h)} saisons avec logos.")