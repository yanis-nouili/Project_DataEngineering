import re
import unicodedata
from psycopg2.extras import execute_values

from scraper.db import get_conn
from scraper.fetch import fetch_rendered_html

URL = "https://www.footmercato.net/france/ligue-1/buteur"
SEASON = "2025/2026"

def norm(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def parse_scorers(html: str):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text(" ", strip=True)

    raw_tokens = raw_text.split()
    tokens = [norm(t) for t in raw_tokens]

    # postes observés (on accepte aussi les codes en MAJUSCULES 1-4 lettres)
    POS = {"bu", "ad", "ag", "mc", "md", "mg", "dg", "dd", "dc", "g", "mil"}

    def is_int(t: str) -> bool:
        return t.isdigit()

    def is_float(t: str) -> bool:
        try:
            float(t.replace(",", "."))
            return True
        except Exception:
            return False

    def is_pos(tok_raw: str, tok_norm: str) -> bool:
        if tok_norm in POS:
            return True
        return tok_raw.isalpha() and tok_raw.upper() == tok_raw and 1 <= len(tok_raw) <= 4

    # Se placer au début du tableau : après "P. B/M B/90m." ou équivalent
    start = 0
    for i in range(len(tokens) - 3):
        if tokens[i] in {"p.", "p"} and tokens[i + 1] == "b/m" and tokens[i + 2].startswith("b/"):
            start = i + 3
            break
        if tokens[i] == "b/m" and tokens[i + 1].startswith("b/"):
            start = i + 2
            break

    if start == 0:
        for i, t in enumerate(tokens):
            if t == "buteurs":
                start = i
                break

    rows = []
    i = start
    current_rank = 0

    # Lire des entrées jusqu'à un nombre raisonnable
    while i < len(tokens) and len(rows) < 250:
        # rang = chiffre ou '-'
        if tokens[i] == "-" or is_int(tokens[i]):
            if is_int(tokens[i]):
                current_rank = int(tokens[i])
            i += 1
        else:
            i += 1
            continue

        # nom joueur jusqu'à trouver un poste
        name_start = i
        while i < len(tokens) and not is_pos(raw_tokens[i], tokens[i]):
            i += 1
        if i >= len(tokens):
            break

        player_name = " ".join(raw_tokens[name_start:i]).strip()
        player_name = player_name.strip("-").strip()

        # poste (on ne le stocke pas pour l'instant)
        i += 1

        # ensuite : goals (int), penalties (int), bpm (float), b90 (float)
        if i + 3 >= len(tokens):
            break

        if not (is_int(tokens[i]) and is_int(tokens[i + 1]) and is_float(tokens[i + 2]) and is_float(tokens[i + 3])):
            # si le pattern ne colle pas, on continue la recherche
            continue

        goals = int(tokens[i])
        penalties = int(tokens[i + 1])
        # bpm = float(tokens[i + 2].replace(",", "."))
        # b90 = float(tokens[i + 3].replace(",", "."))
        i += 4

        # filtre anti "noms" cassés qui contiennent des chiffres
        if any(ch.isdigit() for ch in player_name):
            continue
        if current_rank <= 0 or not player_name:
            continue


        rows.append(
            dict(
                season=SEASON,
                rank=current_rank,
                player_name=player_name,
                team=None,
                goals=goals,
                penalties=penalties,
            )
        )

    if len(rows) < 10:
        print("DEBUG: pas assez de buteurs parsés. Tokens (200) autour du start:")
        print(" ".join(raw_tokens[start : start + 200]))
        raise RuntimeError("Impossible d'extraire les buteurs (tableau non détecté).")

    return rows

def upsert_scorers(rows):
    sql = """
    INSERT INTO scorers (season, rank, player_name, team, goals, penalties)
    VALUES %s
    ON CONFLICT (season, player_name)
    DO UPDATE SET
      rank = EXCLUDED.rank,
      team = EXCLUDED.team,
      goals = EXCLUDED.goals,
      penalties = EXCLUDED.penalties,
      scraped_at = CURRENT_TIMESTAMP;
    """
    values = [(r["season"], r["rank"], r["player_name"], r["team"], r["goals"], r["penalties"]) for r in rows]

    conn = get_conn()
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
    print(f"OK: {len(rows)} lignes insérées/maj dans scorers.")

if __name__ == "__main__":
    main()
