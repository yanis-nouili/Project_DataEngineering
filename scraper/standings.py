import re
import unicodedata
from psycopg2.extras import execute_values

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

def parse_standings(html: str):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text(" ", strip=True)

    # tokens "bruts" (pour reconstruire le nom d'équipe)
    raw_tokens = raw_text.split()

    # tokens normalisés (pour matcher sans accents, etc.)
    def n(s: str) -> str:
        import re, unicodedata
        s = s.replace("\xa0", " ")
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"\s+", " ", s).strip().lower()
        return s

    tokens = [n(t) for t in raw_tokens]

    def is_int(tok: str) -> bool:
        return tok.isdigit()

    def is_signed_int(tok: str) -> bool:
        import re
        return re.match(r"^[+-]?\d+$", tok) is not None

    # 1) trouver l'endroit du header (équipe pts j dif g n d bp bc)
    header_seq = ["equipe", "pts", "j", "dif", "g", "n", "d", "bp", "bc"]
    start = 0
    for i in range(len(tokens) - len(header_seq)):
        if tokens[i:i+len(header_seq)] == header_seq:
            start = i + len(header_seq)
            break
    # si on ne trouve pas exactement, on ne bloque pas : on démarre plus loin
    # (le tableau est parfois plus bas)
    # on prend un start raisonnable (après "classement" / saison) si possible
    if start == 0:
        for i, t in enumerate(tokens):
            if t == "classement":
                start = i
                break

    rows = []
    i = start

    # 2) extraire 18 équipes : rank + team + 8 champs numériques
    # champs attendus après team : pts, played, diff, w, d, l, bp, bc
    expected_rank = 1
    while expected_rank <= 18 and i < len(tokens):
        # chercher le prochain rank (1..18) à partir de i
        try:
            rpos = tokens.index(str(expected_rank), i)
        except ValueError:
            break

        j = rpos + 1  # début du nom d'équipe
        k = j

        # chercher la première position k où tokens[k:k+8] correspond au pattern numérique
        found = None
        while k + 7 < len(tokens) and k < j + 12:  # nom équipe pas trop long
            if (
                is_int(tokens[k]) and
                is_int(tokens[k+1]) and
                is_signed_int(tokens[k+2]) and
                is_int(tokens[k+3]) and
                is_int(tokens[k+4]) and
                is_int(tokens[k+5]) and
                is_int(tokens[k+6]) and
                is_int(tokens[k+7])
            ):
                found = k
                break
            k += 1

        if found is None:
            # on n'a pas réussi à parser ce rank -> on avance et on retente
            i = rpos + 1
            continue

        team = " ".join(raw_tokens[j:found]).strip()
        pts = int(tokens[found])
        played = int(tokens[found+1])
        diff = int(tokens[found+2])
        w = int(tokens[found+3])
        d = int(tokens[found+4])
        l = int(tokens[found+5])
        bp = int(tokens[found+6])
        bc = int(tokens[found+7])

        rows.append(dict(
            season=SEASON,
            rank=expected_rank,
            team=team,
            points=pts,
            played=played,
            wins=w,
            draws=d,
            losses=l,
            goals_for=bp,
            goals_against=bc,
            goal_diff=diff
        ))

        expected_rank += 1
        i = found + 8

    if len(rows) < 10:
        print("DEBUG: tokens autour du début du tableau (200 tokens):")
        print(" ".join(raw_tokens[start:start+200]))
        raise RuntimeError("Impossible d'extraire le classement (tableau non détecté).")

    return rows

def upsert_standings(rows):
    sql = """
    INSERT INTO standings
    (season, rank, team, played, wins, draws, losses, goals_for, goals_against, goal_diff, points)
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
      scraped_at = CURRENT_TIMESTAMP;
    """

    values = [
        (
            r["season"], r["rank"], r["team"], r["played"],
            r["wins"], r["draws"], r["losses"],
            r["goals_for"], r["goals_against"], r["goal_diff"], r["points"]
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
