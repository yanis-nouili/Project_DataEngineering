import re
import unicodedata
from psycopg2.extras import execute_values

from scraper.db import get_conn
from scraper.fetch import fetch_rendered_html

URL = "https://www.footmercato.net/france/ligue-1/passeur"
SEASON = "2025/2026"

def norm(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def parse_assists(html: str):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    raw_text = soup.get_text(" ", strip=True)

    raw_tokens = raw_text.split()
    tokens = [norm(t) for t in raw_tokens]

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
        # codes type "MC", "BU", "DG" en majuscules
        return tok_raw.isalpha() and tok_raw.upper() == tok_raw and 1 <= len(tok_raw) <= 4

    # Ancrage sur l'entête du tableau : "Joueur PD PD/M PD/90m."
    start = 0
    for i in range(len(tokens) - 4):
        if tokens[i] == "joueur" and tokens[i + 1] == "pd":
            start = i + 2
            break

    # fallback si l'entête est un peu différente
    if start == 0:
        for i in range(len(tokens) - 3):
            if tokens[i] == "pd" and tokens[i + 1].startswith("pd/"):
                start = i + 2
                break

    # Ensuite on cherche le premier rang "1" après start
    if start != 0:
        for j in range(start, min(start + 1500, len(tokens))):
            if tokens[j] == "1":
                start = j
                break

    if start == 0:
        # dernier fallback : premier "1" trouvé
        for j in range(len(tokens)):
            if tokens[j] == "1":
                start = j
                break

    rows = []
    i = start
    current_rank = 0

    # Format attendu par ligne :
    # rank (int ou '-') + player_name... + POS + PD(int) + PD/M(float) + PD/90m(float)
    while i < len(tokens) and len(rows) < 300:
        # rank
        if tokens[i] == "-" or is_int(tokens[i]):
            if is_int(tokens[i]):
                current_rank = int(tokens[i])
            i += 1
        else:
            i += 1
            continue

        # player name jusqu'au POS
        name_start = i
        while i < len(tokens) and not is_pos(raw_tokens[i], tokens[i]):
            i += 1
        if i >= len(tokens):
            break

        player_name = " ".join(raw_tokens[name_start:i]).strip().strip("-").strip()
        pos_raw = raw_tokens[i]  # non utilisé, mais utile si tu veux stocker plus tard
        i += 1

        # il doit rester: int + float + float
        if i + 2 >= len(tokens):
            break

        if not (is_int(tokens[i]) and is_float(tokens[i + 1]) and is_float(tokens[i + 2])):
            # si ça ne colle pas, on tente de se resynchroniser en avançant un peu
            continue

        assists = int(tokens[i])
        # pd_per_match = float(tokens[i + 1].replace(",", "."))
        # pd_per_90 = float(tokens[i + 2].replace(",", "."))
        i += 3

        # filtres anti bruit
        if current_rank <= 0 or not player_name:
            continue
        if any(ch.isdigit() for ch in player_name):
            continue

        rows.append(
            dict(
                season=SEASON,
                rank=current_rank,
                player_name=player_name,
                team=None,
                assists=assists,
            )
        )

    if len(rows) < 10:
        print("DEBUG: pas assez de passeurs parsés. Tokens (250) autour du start:")
        print(" ".join(raw_tokens[start:start+250]))
        raise RuntimeError("Impossible d'extraire les passeurs (tableau non détecté).")

    return rows

def upsert_assists(rows):
    sql = """
    INSERT INTO assists (season, rank, player_name, team, assists)
    VALUES %s
    ON CONFLICT (season, player_name, team)
    DO UPDATE SET
      rank = EXCLUDED.rank,
      team = EXCLUDED.team,
      assists = EXCLUDED.assists,
      scraped_at = CURRENT_TIMESTAMP;
    """
    values = [(r["season"], r["rank"], r["player_name"], r["team"], r["assists"]) for r in rows]

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, values)
    finally:
        conn.close()


def main():
    html = fetch_rendered_html(URL, wait_text="Passeurs")
    rows = parse_assists(html)
    upsert_assists(rows)
    print(f"OK: {len(rows)} lignes insérées/maj dans assists.")

if __name__ == "__main__":
    main()
