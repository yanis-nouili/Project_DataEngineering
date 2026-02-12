import os
import pandas as pd
import streamlit as st
import psycopg2
from dotenv import load_dotenv
import altair as alt

load_dotenv()

st.set_page_config(page_title="Ligue 1 Dashboard", layout="wide")

# ========================
# CSS
# ========================
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

SEASON = os.environ.get("SEASON", "2025/2026")

# ========================
# DB
# ========================
def get_conn():
    return psycopg2.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "db"), # "db" pour docker, "localhost" en local
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
    )

@st.cache_data(ttl=60)
def load_df(query: str):
    conn = get_conn()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# ========================
# NAVIGATION
# ========================
st.title("Ligue 1 — Dashboard")

page = st.sidebar.radio(
    "Navigation",
    ["Accueil", 
    "Classement", 
    "Buteurs",
    "Passeurs", 
    "Contributions", 
    "Palmarès"]
)

# ========================
# ACCUEIL
# ========================
if page == "Accueil":
    st.subheader("Aperçu Ligue 1")

    standings = load_df(f"SELECT team, points FROM standings WHERE season='{SEASON}' ORDER BY rank LIMIT 1;")
    scorers = load_df(f"SELECT player_name, goals FROM scorers WHERE season='{SEASON}' ORDER BY goals DESC LIMIT 1;")
    assists = load_df(f"SELECT player_name, assists FROM assists WHERE season='{SEASON}' ORDER BY assists DESC LIMIT 1;")

    k1, k2, k3 = st.columns(3)
    if not standings.empty:
        k1.metric("Leader", standings.iloc[0]["team"], f"{int(standings.iloc[0]['points'])} pts")
    if not scorers.empty:
        k2.metric("Meilleur buteur", scorers.iloc[0]["player_name"], f"{int(scorers.iloc[0]['goals'])} buts")
    if not assists.empty:
        k3.metric("Meilleur passeur", assists.iloc[0]["player_name"], f"{int(assists.iloc[0]['assists'])} passes")

# ========================
# CLASSEMENT
# ========================
elif page == "Classement":
    st.subheader(f"Classement Ligue 1 - Saison {SEASON}")
    df = load_df(f"""
        SELECT 
            rank AS "Rang", 
            logo_url AS " ", 
            team AS "Équipe", 
            played AS "J", 
            wins AS "G", 
            draws AS "N", 
            losses AS "P", 
            goal_diff AS "Diff", 
            points AS "Pts"
        FROM standings WHERE season='{SEASON}' ORDER BY rank ASC;
    """)
    st.dataframe(df, column_config={
        " ": st.column_config.ImageColumn(" ", width="small"),
        "Pts": st.column_config.NumberColumn("Pts", format="%d")
    }, use_container_width=True, hide_index=True)

# ========================
# BUTEURS
# ========================
elif page == "Buteurs":
    st.subheader("Classement des Buteurs")
    df = load_df(f"""
        SELECT 
            photo_url AS " ", 
            player_name AS "Joueur", 
            logo_url AS "Club", 
            goals AS "Buts", 
            penalties AS "Penaltys"
        FROM scorers WHERE season='{SEASON}' ORDER BY goals DESC, rank ASC;
    """)
    q = st.text_input("Rechercher un buteur")
    if q: df = df[df["Joueur"].str.contains(q, case=False)]

    st.dataframe(df, column_config={
        " ": st.column_config.ImageColumn(" ", width="small"),
        "Club": st.column_config.ImageColumn("Équipe", width="small")
    }, use_container_width=True, height=650, hide_index=True)

# ========================
# PASSEURS
# ========================
elif page == "Passeurs":
    st.subheader("Classement des Passeurs")
    df = load_df(f"""
        SELECT 
            photo_url AS " ", 
            player_name AS "Joueur", 
            logo_url AS "Club", 
            assists AS "Passes"
        FROM assists WHERE season='{SEASON}' ORDER BY assists DESC, rank ASC;
    """)
    q = st.text_input("Rechercher un joueur")
    if q: df = df[df["Joueur"].str.contains(q, case=False)]

    st.dataframe(df, column_config={
        " ": st.column_config.ImageColumn(" ", width="small"),
        "Club": st.column_config.ImageColumn("Club", width="small")
    }, use_container_width=True, height=650, hide_index=True)

# ========================
# CONTRIBUTIONS
# ========================
elif page == "Contributions":
    st.subheader("Contributions Combinées (Buts + Passes)")
    df = load_df(f"""
        SELECT 
            photo_url AS " ",
            player_name AS "Joueur", 
            logo_url AS "Équipe",
            SUM(goals) AS "Buts", 
            SUM(assists) AS "Passes",
            (SUM(goals) + SUM(assists)) AS "Total"
        FROM (
            SELECT 
                player_name, 
                goals, 
                0 AS assists, 
                photo_url, 
                logo_url FROM scorers WHERE season='{SEASON}'
                UNION ALL
            SELECT 
                player_name, 
                0 AS goals, 
                assists, 
                photo_url, 
                logo_url FROM assists WHERE season='{SEASON}'
        ) AS combined
        GROUP BY player_name, photo_url, logo_url
        ORDER BY "Total" DESC;
    """)

    st.dataframe(df, column_config={
        " ": st.column_config.ImageColumn(" ", width="small"),
        "Équipe": st.column_config.ImageColumn("Équipe", width="small"),
        "Total": st.column_config.NumberColumn("Total", format="%d")
    }, use_container_width=True, height=650, hide_index=True)

# ========================
# PALMARES 
# ========================
elif page == "Palmarès":
    st.subheader("Palmarès Ligue 1")

    # 1. TOP CLUBS - Correction des guillemets simples en doubles guillemets pour les alias
    clubs = load_df("""
        SELECT 
            logo_url AS "Logo", 
            team AS "Equipe", titles AS "Titres" 
        FROM palmares_clubs 
        WHERE titles < 30 
        ORDER BY titles DESC;
    """)

    # 2. HISTORIQUE
    history = load_df("""
        SELECT season AS "Saison", 
               winner_logo AS " ", 
                winner AS "Vainqueurs", 
               runner_up_logo AS "  ", 
                runner_up AS "Dauphins"
        FROM palmares_history 
        ORDER BY season DESC;
    """)

    st.markdown("### Clubs les plus titrés")
    st.dataframe(clubs, column_config={
        "Logo": st.column_config.ImageColumn("Logo", width="small"),
        "Titres": st.column_config.NumberColumn("Titres", format="%d")
    }, use_container_width=True, hide_index=True)

    st.markdown("### Historique vainqueurs de chaque saison")
    st.dataframe(history, column_config={
        " ": st.column_config.ImageColumn(" ", width="small"),
        "  ": st.column_config.ImageColumn("  ", width="small")
    }, use_container_width=True, hide_index=True)