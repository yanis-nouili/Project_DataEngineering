import re
import unicodedata
from psycopg2.extras import execute_values
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from scraper.db import get_conn
from scraper.fetch import fetch_rendered_html

URL = "https://www.footmercato.net/france/ligue-1/classement"
SEASON = "2025/2026"

def norm(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s


BASE = "https://www.footmercato.net"

def parse_standings(html: str):
    soup = BeautifulSoup(html, "html.parser")

    def to_int(td):
        txt = td.get_text(" ", strip=True).replace("+", "")
        txt = re.sub(r"[^\d\-]", "", txt)
        return int(txt or 0)

    # On prend le premier tableau qui ressemble à un classement
    table = soup.find("table")
    if not table:
        raise RuntimeError("Table classement introuvable.")

    rows = []
    for tr in table.find_all("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) < 5:
            continue

        # Rank (souvent 1ère colonne)
        rank_txt = tds[0].get_text(" ", strip=True)
        if not rank_txt.isdigit():
            continue
        rank = int(rank_txt)

        # Team + logo : on cherche un lien + image dans la ligne
        team = None
        logo_url = None

        a = tr.find("a")
        if a:
            team = a.get_text(" ", strip=True)

        img = tr.find("img")
        if img:
            src = (
                img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("data-original")
                or img.get("srcset")
                or img.get("src")
            )
            if src:
            # si srcset: "url 1x, url2 2x" -> on prend la première url
                if " " in src and "," in src:
                    src = src.split(",")[0].strip().split(" ")[0].strip()
                # ignore les placeholders svg
                if not src.startswith("data:image"):
                    logo_url = urljoin(BASE, src)

        # Récupération des chiffres (selon structure : played/w/d/l/gf/ga/gd/pts)
        nums = [td.get_text(" ", strip=True) for td in tds]
        nums = [re.sub(r"[^\d\-]", "", x) for x in nums]  # garde digits et -
        nums = [x for x in nums if x != ""]

        # Ici on suppose un format classique :
        # rank, ..., played, wins, draws, losses, goals_for, goals_against, goal_diff, points
        # On prend les 8 derniers nombres comme (played..points)
        if len(nums) < 9:
            continue
        tail = nums[-8:]  # played,wins,draws,losses,gf,ga,gd,pts

        #played, wins, draws, losses, gf, ga, gd, pts = map(int, tail)
        pts    = to_int(tds[2])  # Pts
        played = to_int(tds[3])  # J
        gd     = to_int(tds[4])  # DIF
        wins   = to_int(tds[5])  # G
        draws  = to_int(tds[6])  # N
        losses = to_int(tds[7])  # D
        gf     = to_int(tds[8])  # BP
        ga     = to_int(tds[9])  # BC


        rows.append({
            "season": "2025/2026",
            "rank": rank,
            "team": team,
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": gf,
            "goals_against": ga,
            "goal_diff": gd,
            "points": pts,
            "logo_url": logo_url,
        })

    if len(rows) < 10:
        raise RuntimeError("Pas assez de lignes parsées pour le classement (structure différente).")

    return rows


def upsert_standings(rows):
    sql = """
    INSERT INTO standings
    (season, rank, team, played, wins, draws, losses, goals_for, goals_against, goal_diff, points, logo_url)
    VALUES %s
    ON CONFLICT (season, team)
    DO UPDATE SET
      rank = EXCLUDED.rank,
      played = EXCLUDED.played,
      wins = EXCLUDED.wins,
      draws = EXCLUDED.draws,
      losses = EXCLUDED.losses,
      goals_for = EXCLUDED.goals_for,
      goals_against = EXCLUDED.goals_against,
      goal_diff = EXCLUDED.goal_diff,
      points = EXCLUDED.points,
      logo_url = EXCLUDED.logo_url,
      scraped_at = CURRENT_TIMESTAMP;
    """

    values = [
        (
            r["season"], r["rank"], r["team"], r["played"],
            r["wins"], r["draws"], r["losses"],
            r["goals_for"], r["goals_against"], r["goal_diff"], r["points"], r.get("logo_url")
        )
        for r in rows
    ]

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
    finally:
        conn.close()

def main():
    html = fetch_rendered_html(URL)
    rows = parse_standings(html)
    upsert_standings(rows)
    print(f"OK: {len(rows)} lignes insérées/maj dans standings.")

if __name__ == "__main__":
    main()
