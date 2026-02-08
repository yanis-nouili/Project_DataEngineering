import os
import pandas as pd
import streamlit as st
import psycopg2
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(page_title="Ligue 1 Dashboard", layout="wide")

SEASON = os.environ.get("SEASON", "2025/2026")

def get_conn():
    return psycopg2.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
    )

@st.cache_data(ttl=60)
def load_df(query: str) -> pd.DataFrame:
    conn = get_conn()
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

st.title("Ligue 1 — Dashboard")
st.caption("Données scrapées depuis Foot Mercato, stockées dans PostgreSQL (Docker).")

page = st.sidebar.radio("Navigation", ["Classement", "Buteurs", "Passeurs", "Contributions"])

if page == "Classement":
    st.subheader("Classement")

    df = load_df(f"""
        SELECT
            rank AS "rank",team AS "Equipe", played AS "Matchs joués",wins AS "Victoires", draws AS "Nuls",
            losses AS "Défaites", goals_for AS "Buts pour", goals_against AS "Buts contre",goal_diff AS "Différence de but",
            points AS "Points"
        FROM standings
        WHERE season='{SEASON}'
        ORDER BY rank;
    """)


    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df, use_container_width=True, height=650)
    with col2:
        st.metric("Équipes", len(df))
        if len(df):
            st.metric("Leader", df.iloc[0]["Equipe"])
            st.metric("Points leader", int(df.iloc[0]["Points"]))
        st.write("Top 6 (points)")
        if len(df) >= 6:
            top6 = df.head(6).copy()
            top6["label"] = top6["rank"].astype(str) + " - " + top6["Equipe"]
            chart = top6.set_index("label")["Points"]
            st.bar_chart(chart)

elif page == "Buteurs":
    st.subheader("Buteurs")
    df = load_df(f"""
        SELECT
            rank AS "rank",
            player_name AS "Joueur",
            goals AS "Buts",
            penalties AS "Pénaltys"
        FROM scorers
        WHERE season='{SEASON}'
        ORDER BY goals DESC, rank ASC, player_name ASC;
    """)

    q = st.text_input("Recherche joueur", "")
    if q:
        df = df[df["Joueur"].str.lower().str.contains(q.lower(), na=False)]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df, use_container_width=True, height=650)
    with col2:
        st.metric("Joueurs", len(df))
        st.write("Top 10 (buts) — triés par buts")
        top = df.sort_values(["Buts", "rank"], ascending=[False, True]).head(10).copy()
        top = top.iloc[::-1]
        top["label"] = top["Buts"].astype(str) + " - " + top["Joueur"]
        st.bar_chart(top.set_index("label")["Buts"])

elif page == "Passeurs":
    st.subheader("Passeurs")
    df = load_df(f"""
        SELECT
            rank AS "rank",
            player_name AS "Joueur",
            assists AS "Assists"
        FROM assists
        WHERE season='{SEASON}'
        ORDER BY assists DESC, rank ASC, player_name ASC;
    """)

    q = st.text_input("Recherche joueur", "")
    if q:
        df = df[df["Joueur"].str.lower().str.contains(q.lower(), na=False)]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df, use_container_width=True, height=650)
    with col2:
        st.metric("Joueurs", len(df))
        st.write("Top 10 (passes décisives) — triés par passes")
        top = df.sort_values(["Assists", "rank"], ascending=[False, True]).head(10).copy()
        top = top.iloc[::-1]
        top["label"] = top["Assists"].astype(str) + " - " + top["Joueur"]
        st.bar_chart(top.set_index("label")["Assists"])


elif page == "Contributions":
    st.subheader("Contributions (buts + passes)")

    df = load_df(f"""
        SELECT
          COALESCE(s.player_name, a.player_name) AS "Joueur",
          COALESCE(s.goals, 0) AS "Buts",
          COALESCE(a.assists, 0) AS "Assists",
          (COALESCE(s.goals, 0) + COALESCE(a.assists, 0)) AS "Contributions"
        FROM scorers s
        FULL OUTER JOIN assists a
          ON s.season = a.season AND s.player_name = a.player_name
        WHERE COALESCE(s.season, a.season) = '{SEASON}'
        ORDER BY "Contributions" DESC, "Buts" DESC, "Assists" DESC, "Joueur" ASC;
    """)

    q = st.text_input("Recherche joueur", "")
    if q:
        df = df[df["Joueur"].str.lower().str.contains(q.lower(), na=False)]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df, use_container_width=True, height=650)
    with col2:
        st.metric("Joueurs", len(df))
        st.write("Top 10 (contributions)")
        top = df.head(10).copy()
        top["label"] = top["Contributions"].astype(int).astype(str) + " - " + top["Joueur"]
        st.bar_chart(top.set_index("label")["Contributions"])
