import streamlit as st
import pandas as pd
import io
from datetime import datetime

# ---------------------- Page config ----------------------
st.set_page_config(
    page_title="Fund Raiser Leaderboard",
    page_icon="🏆",
    layout="wide"
)

# ---------------------- Constants ------------------------
SHEET_ID = "1W6KceOOBmnGxblXell3gvTC4vZ7LwHaOYQPZESYGxXQ"
# If your leaderboard is on the first sheet, this CSV export works as-is.
# If it's on another tab, append &gid=<tab_gid> to the URL.
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

REQUIRED_COLUMNS = [
    "Team_Name", "Game_1", "Game_2", "Game_3", "Game_4", "Column 6", "Total_points"
]

GAME_COLUMNS = ["Game_1", "Game_2", "Game_3", "Game_4"]

# ---------------------- Helpers --------------------------
def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Try to coerce similar column names to the required schema.
    e.g. 'Team Name' -> 'Team_Name', 'Column6' -> 'Column 6'
    """
    mapping_candidates = {
        "team name": "Team_Name",
        "team_name": "Team_Name",
        "team": "Team_Name",
        "game1": "Game_1",
        "game 1": "Game_1",
        "game2": "Game_2",
        "game 2": "Game_2",
        "game3": "Game_3",
        "game 3": "Game_3",
        "game4": "Game_4",
        "game 4": "Game_4",
        "column6": "Column 6",
        "column_6": "Column 6",
        "bonus": "Column 6",
        "total": "Total_points",
        "total points": "Total_points",
        "total_points": "Total_points",
    }

    new_cols = {}
    for c in df.columns:
        key = str(c).strip().lower()
        new_cols[c] = mapping_candidates.get(key, c)
    df = df.rename(columns=new_cols)
    return df


def _ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    If any required columns are missing, create them with zeros.
    Cast numeric columns to numbers.
    """
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    # Numeric coercion (non-numeric become NaN -> fill 0)
    for col in GAME_COLUMNS + ["Column 6", "Total_points"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Team names as strings
    df["Team_Name"] = df["Team_Name"].astype(str)
    return df


def _compute_totals_and_rank(df: pd.DataFrame) -> pd.DataFrame:
    # If Total_points looks empty/zero, compute it.
    if (df["Total_points"].fillna(0) == 0).all():
        df["Total_points"] = df[GAME_COLUMNS].sum(axis=1) + df["Column 6"]

    # Rank (dense) by Total_points, descending
    df["Rank"] = df["Total_points"].rank(method="dense", ascending=False).astype(int)
    df = df.sort_values(["Total_points", "Team_Name"], ascending=[False, True]).reset_index(drop=True)

    # Reorder
    ordered_cols = ["Rank", "Team_Name", *GAME_COLUMNS, "Column 6", "Total_points"]
    df = df[ordered_cols]
    return df


# ---------------------- Data loaders ---------------------
@st.cache_data(show_spinner=False)
def load_base_data() -> pd.DataFrame:
    data = {
        'Team_Name': [f'Team_{i}' for i in range(1, 9)],
        'Game_1': [0]*8,
        'Game_2': [0]*8,
        'Game_3': [0]*8,
        'Game_4': [0]*8,
        'Column 6': [0]*8,
        'Total_points': [0]*8
    }
    return pd.DataFrame(data)


@st.cache_data(ttl=60*60, show_spinner=True)
def load_from_gsheet(csv_url: str) -> pd.DataFrame:
    df = pd.read_csv(csv_url)
    df = _normalize_columns(df)
    df = _ensure_required_columns(df)
    df = _compute_totals_and_rank(df)
    return df


# ---------------------- UI -------------------------------
st.title("🏆 Fund Raiser Competition Leaderboard")
st.markdown("---")

# Create main layout: leaderboard (col1) + controls (col2)
col1, col2 = st.columns([3, 1])

# ------------- Controls (col2) -------------
with col2:
    st.subheader("⚙️ Controls")

    # Optional auto-refresh (every 2 minutes)
    auto_refresh = st.toggle("Auto-refresh (every 2 min)", value=True, help="Reloads the app periodically")
    if auto_refresh:
        try:
            from streamlit_autorefresh import st_autorefresh
            # Every 120000 ms (2 minutes)
            st_autorefresh(interval=5_000, key="auto_refresh_tick")
        except Exception:
            st.info("Install `streamlit-autorefresh` to enable auto-refresh: `pip install streamlit-autorefresh`")

    # Manual refresh button
    do_refresh = st.button("🔄 Refresh now", help="Force re-download of Sheet")

# Load data (live from  Sheet)
try:
    if do_refresh:
        load_from_gsheet.clear()
    df = load_from_gsheet(CSV_URL)
    load_ok = True
except Exception as e:
    df = load_base_data()
    load_ok = False
    with col2:
        st.error(f"Could not load Sheet: {e}")

# Show status & last updated
with col2:
    now_txt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if load_ok and do_refresh:
        st.success(f"Data refreshed at {now_txt}")
    elif load_ok:
        st.caption(f"Last loaded at: {now_txt}")

# ------------- Leaderboard (col1) -------------
with col1:
    st.subheader("📊 Fund Raiser Leaderboard")

    column_config = {
        "Team_Name": st.column_config.TextColumn("🏅 Team Name", help="Team participating in the fund raiser"),
        "Game_1": st.column_config.NumberColumn("🎮 Game 1", help="Points from Game 1", format="%d"),
        "Game_2": st.column_config.NumberColumn("🎯 Game 2", help="Points from Game 2", format="%d"),
        "Game_3": st.column_config.NumberColumn("🎲 Game 3", help="Points from Game 3", format="%d"),
        "Game_4": st.column_config.NumberColumn("🏃 Game 4", help="Points from Game 4", format="%d"),
        "Column 6": st.column_config.NumberColumn("⭐ Bonus", help="Bonus points", format="%d"),
        "Total_points": st.column_config.NumberColumn("🏆 Total Points", help="Sum of all points", format="%d"),
        "Rank": st.column_config.NumberColumn("🥇 Rank", help="Current ranking position", format="%d"),
    }

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )

# ---------------- Statistics (below both cols) ----------------
st.markdown("---")
st.subheader("📈 Competition Statistics")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Total Teams", len(df))

with c2:
    st.metric("Highest Score", f"{int(df['Total_points'].max()) if len(df) else 0}")

with c3:
    st.metric("Average Score", f"{df['Total_points'].mean():.0f}" if len(df) else "0")

with c4:
    if len(df) and df['Total_points'].max() > 0:
        leader = df.sort_values('Total_points', ascending=False).iloc[0]['Team_Name']
    else:
        leader = "TBD"
    st.metric("Leading Team", leader)

# Top 3 cards
if len(df) and df["Total_points"].sum() > 0:
    st.markdown("---")
    st.subheader("🥇 Top 3 Teams")
    top_3 = df.sort_values('Total_points', ascending=False).head(3)
    cols = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]

    for i, (_, team) in enumerate(top_3.iterrows()):
        # find best game index
        game_vals = [team[g] for g in GAME_COLUMNS]
        best_idx = int(pd.Series(game_vals).idxmax())  # 0..3
        best_game_label = GAME_COLUMNS[best_idx].replace("_", " ")

        with cols[i]:
            st.markdown(f"""
            <div style="text-align: center; padding: 20px; border-radius: 10px; 
                       background-color: rgba(68, 114, 196, 0.08); border: 2px solid #4472C4;">
                <h2>{medals[i]}</h2>
                <h3>{team['Team_Name']}</h3>
                <p><strong>Total Points:</strong> {int(team['Total_points'])}</p>
                <p><strong>Best Game:</strong> {best_game_label}</p>
            </div>
            """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style="text-align: center; color: gray; font-size: 12px;">
        🏆 Fund Raiser Competition Dashboard | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    """,
    unsafe_allow_html=True
)
