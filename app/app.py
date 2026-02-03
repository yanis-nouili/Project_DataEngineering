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

page = st.sidebar.radio("Navigation", ["Classement", "Buteurs", "Passeurs"])

if page == "Classement":
    st.subheader("Classement")
    df = load_df(f"""
        SELECT rank, team, played, wins, draws, losses, goals_for, goals_against, goal_diff, points
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
            st.metric("Leader", df.iloc[0]["team"])
            st.metric("Points leader", int(df.iloc[0]["points"]))
        st.write("Top 6 (points)")
        if len(df) >= 6:
            top6 = df.head(6).set_index("team")["points"]
            st.bar_chart(top6)

elif page == "Buteurs":
    st.subheader("Buteurs")
    df = load_df(f"""
        SELECT rank, player_name, goals, penalties
        FROM scorers
        WHERE season='{SEASON}'
        ORDER BY goals DESC, rank ASC, player_name ASC;
    """)

    q = st.text_input("Recherche joueur", "")
    if q:
        df = df[df["player_name"].str.lower().str.contains(q.lower(), na=False)]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df, use_container_width=True, height=650)
    with col2:
        st.metric("Joueurs", len(df))
        st.write("Top 10 (buts)")
        if len(df) >= 10:
            top = df.head(10).set_index("player_name")["goals"]
            st.bar_chart(top)

elif page == "Passeurs":
    st.subheader("Passeurs")
    df = load_df(f"""
        SELECT rank, player_name, assists
        FROM assists
        WHERE season='{SEASON}'
        ORDER BY assists DESC, rank ASC, player_name ASC;
    """)

    q = st.text_input("Recherche joueur", "")
    if q:
        df = df[df["player_name"].str.lower().str.contains(q.lower(), na=False)]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df, use_container_width=True, height=650)
    with col2:
        st.metric("Joueurs", len(df))
        st.write("Top 10 (passes décisives)")
        if len(df) >= 10:
            top = df.head(10).set_index("player_name")["assists"]
            st.bar_chart(top)
