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
        host=os.environ.get("POSTGRES_HOST", "localhost"),
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
    [
        "Accueil",
        "Classement",
        "Buteurs",
        "Passeurs",
        "Contributions",
        "Palmarès",
    ],
)

# ========================
# ACCUEIL
# ========================
if page == "Accueil":

    st.subheader("Aperçu Ligue 1")

    standings = load_df(f"""
        SELECT team, points
        FROM standings
        WHERE season='{SEASON}'
        ORDER BY rank LIMIT 1;
    """)

    scorers = load_df(f"""
        SELECT player_name, goals
        FROM scorers
        WHERE season='{SEASON}'
        ORDER BY goals DESC LIMIT 1;
    """)

    assists = load_df(f"""
        SELECT player_name, assists
        FROM assists
        WHERE season='{SEASON}'
        ORDER BY assists DESC LIMIT 1;
    """)

    k1, k2, k3 = st.columns(3)

    if len(standings):
        k1.metric("Leader", standings.iloc[0]["team"],
                  f"{int(standings.iloc[0]['points'])} pts")

    if len(scorers):
        k2.metric("Meilleur buteur",
                  scorers.iloc[0]["player_name"],
                  f"{int(scorers.iloc[0]['goals'])} buts")

    if len(assists):
        k3.metric("Meilleur passeur",
                  assists.iloc[0]["player_name"],
                  f"{int(assists.iloc[0]['assists'])} passes")

# ========================
# CLASSEMENT
# ========================
elif page == "Classement":

    st.subheader("Classement")

    df = load_df(f"""
        SELECT
            rank,
            logo_url AS "Logo",
            team AS "Equipe",
            played AS "Matchs",
            wins AS "Victoires",
            draws AS "Nuls",
            losses AS "Défaites",
            goals_for AS "BP",
            goals_against AS "BC",
            goal_diff AS "Diff",
            points AS "Points"
        FROM standings
        WHERE season='{SEASON}'
        ORDER BY rank;
    """)

    st.dataframe(
        df,
        use_container_width=True,
        height=650,
        column_config={
            "Logo": st.column_config.ImageColumn(width="small")
        },
    )

    st.markdown("### Top 6 équipes (points)")

    if len(df) >= 6:
        top6 = df.head(6)
        chart = alt.Chart(top6).mark_bar().encode(
            y=alt.Y("Equipe:N", sort="-x"),
            x="Points:Q",
        )
        st.altair_chart(chart, use_container_width=True)

# ========================
# BUTEURS
# ========================
elif page == "Buteurs":

    st.subheader("⚽ Classement des Buteurs")

    df = load_df(f"""
        SELECT 
            photo_url AS " ",
            player_name AS "Joueur",
            logo_url AS "Club",
            goals AS "Buts",
            penalties AS "Penaltys"
        FROM scorers
        WHERE season='{SEASON}'
        ORDER BY goals DESC, rank ASC;
    """)

    # Recherche
    q = st.text_input("🔍 Rechercher un buteur")
    if q:
        df = df[df["Joueur"].str.contains(q, case=False)]

    # Affichage avec images
    st.dataframe(
        df, 
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Club": st.column_config.ImageColumn("Équipe", width="small"),
            "Buts": st.column_config.NumberColumn("Buts", format="%d ⚽"),
            "Penaltys": st.column_config.NumberColumn("Pénalty 🥅")
        },
        use_container_width=True, 
        height=650,
        hide_index=True
    )

    st.markdown("### Top 10 des buteurs")
    chart = alt.Chart(df.head(10)).mark_bar().encode(
        y=alt.Y("Joueur:N", sort="-x"),
        x="Buts:Q",
        color=alt.value("#e74c3c")
    )
    st.altair_chart(chart, use_container_width=True)

# ========================
# PASSEURS
# ========================
elif page == "Passeurs":

    st.subheader("🎯 Classement des Passeurs")

    df = load_df(f"""
        SELECT 
            photo_url AS " ",
            player_name AS "Joueur",
            logo_url AS "Club",
            assists AS "Passes"
        FROM assists
        WHERE season='{SEASON}'
        ORDER BY assists DESC, rank ASC;
    """)

    # Recherche
    q = st.text_input("🔍 Rechercher un joueur")
    if q:
        df = df[df["Joueur"].str.contains(q, case=False)]

    # Affichage
    st.dataframe(
        df, 
        column_config={
            " ": st.column_config.ImageColumn(" ", width="small"),
            "Club": st.column_config.ImageColumn("Club", width="small"),
            "Passes": st.column_config.NumberColumn("Passes", format="%d 🎯")
        },
        use_container_width=True, 
        height=650,
        hide_index=True
    )

# ========================
# CONTRIBUTIONS
# ========================
elif page == "Contributions":

    st.subheader("Contributions")

    df = load_df(f"""
        SELECT
          COALESCE(s.player_name,a.player_name) AS "Joueur",
          COALESCE(s.goals,0) AS "Buts",
          COALESCE(a.assists,0) AS "Passes",
          (COALESCE(s.goals,0)+COALESCE(a.assists,0)) AS "Contributions"
        FROM scorers s
        FULL JOIN assists a
        ON s.player_name=a.player_name
        WHERE COALESCE(s.season,a.season)='{SEASON}'
        ORDER BY "Contributions" DESC;
    """)

    st.dataframe(df, use_container_width=True, height=650)

    st.markdown("### Top contributions")

    chart = alt.Chart(df.head(10)).mark_bar().encode(
        y=alt.Y("Joueur:N", sort="-x"),
        x="Contributions:Q",
    )
    st.altair_chart(chart, use_container_width=True)
    

# ========================
# PALMARES 
# ========================
elif page == "Palmarès":
    st.subheader("Palmarès Ligue 1")

    # 1. TOP CLUBS
    clubs = load_df("""
        SELECT logo_url AS "Logo", team AS "Equipe", titles AS "Titres"
        FROM palmares_clubs WHERE titles < 30 ORDER BY titles DESC;
    """)

    # 2. HISTORIQUE
    history = load_df("""
        SELECT season AS "Saison", 
               winner_logo AS " ", winner AS "Champion", 
               runner_up_logo AS "  ", runner_up AS "Finaliste"
        FROM palmares_history ORDER BY season DESC;
    """)

    st.markdown("### Clubs les plus titrés")
    st.dataframe(clubs, column_config={
        "Logo": st.column_config.ImageColumn("Logo", width="small"),
        "Titres": st.column_config.NumberColumn("Titres", format="%d 🏆")
    }, use_container_width=True, hide_index=True)

    st.markdown("### Historique des saisons")
    st.dataframe(history, column_config={
        " ": st.column_config.ImageColumn(" ", width="small"),
        "  ": st.column_config.ImageColumn("  ", width="small")
    }, use_container_width=True, hide_index=True)