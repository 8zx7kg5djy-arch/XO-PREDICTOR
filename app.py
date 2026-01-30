import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from model import predict_match, load_data

# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(page_title="Premier League Predictions", layout="wide")
st.title("⚽ XO MODEL PREMIER LEAGUE PREDICTOR ⚽")

# ---------------- TEAM NAME MAP ---------------- #
TEAM_NAME_MAP = {
    "Arsenal FC": "Arsenal",
    "Aston Villa FC": "Aston Villa",
    "Bournemouth AFC": "Bournemouth",
    "AFC Bournemouth": "Bournemouth",
    "Brentford FC": "Brentford",
    "Brighton & Hove Albion FC": "Brighton",
    "Chelsea FC": "Chelsea",
    "Crystal Palace FC": "Crystal Palace",
    "Everton FC": "Everton",
    "Fulham FC": "Fulham",
    "Leeds United FC": "Leeds",
    "Liverpool FC": "Liverpool",
    "Manchester City FC": "Man City",
    "Manchester United FC": "Man United",
    "Newcastle United FC": "Newcastle",
    "Nottingham Forest FC": "Nott'm Forest",
    "Sunderland AFC": "Sunderland",
    "Tottenham Hotspur FC": "Tottenham",
    "West Ham United FC": "West Ham",
    "Wolverhampton Wanderers FC": "Wolves",
    "Burnley FC": "Burnley"
}

# ---------------- LOAD HISTORICAL DATA ---------------- #
df = load_data()
known_teams = set(df["HomeTeam"]).union(set(df["AwayTeam"]))

# ---------------- FETCH MATCHES ---------------- #
API_TOKEN = "6f4e186a1162460eb33694f338553c71"  # <-- your API token
url = "https://api.football-data.org/v4/competitions/PL/matches"
headers = {"X-Auth-Token": API_TOKEN}

try:
    response = requests.get(url, headers=headers)
    data = response.json()
    matches = data.get("matches", [])
except Exception as e:
    st.error(f"Error fetching matches: {e}")
    matches = []

# ---------------- GROUP BY GAMEWEEK ---------------- #
matchdays = {}
now = datetime.utcnow()

for m in matches:
    match_time = datetime.strptime(m["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
    if match_time.date() >= now.date():
        gw = m.get("matchday", 0)
        matchdays.setdefault(gw, []).append({
            "HomeTeam": m["homeTeam"]["name"],
            "AwayTeam": m["awayTeam"]["name"],
            "HomeLogo": m["homeTeam"]["crest"],
            "AwayLogo": m["awayTeam"]["crest"],
            "MatchTime": match_time.strftime("%Y-%m-%d %H:%M")
        })

if not matchdays:
    st.warning("No upcoming matches found.")
    st.stop()

# ---------------- GAMEWEEK NAVIGATION ---------------- #
sorted_gws = sorted(matchdays.keys())
current_gw = sorted_gws[0]  # show only the first upcoming gameweek

st.subheader(f"Gameweek {current_gw}")

#if "gw_index" not in st.session_state:
#    st.session_state.gw_index = 0

#col1, col2 = st.columns(2)
#with col1:
#    if st.button("⬅ Previous Week") and st.session_state.gw_index > 0:
#        st.session_state.gw_index -= 1
#with col2:
 #   if st.button("Next Week ➡") and st.session_state.gw_index < len(sorted_gws) - 1:
 #       st.session_state.gw_index += 1

#current_gw = sorted_gws[st.session_state.gw_index]
#st.subheader(f"Gameweek {current_gw}") 

# ---------------- DISPLAY MATCHES ---------------- #
for i, game in enumerate(matchdays[current_gw]):
    cols = st.columns([2,1,2,2])
    with cols[0]:
        st.image(game["HomeLogo"], width=50)
        st.write(f"**{game['HomeTeam']}**")
    with cols[1]:
        st.write("VS")
    with cols[2]:
        st.image(game["AwayLogo"], width=50)
        st.write(f"**{game['AwayTeam']}**")
    with cols[3]:
        st.write(f"🕒 {game['MatchTime']}")

    home = TEAM_NAME_MAP.get(game["HomeTeam"], game["HomeTeam"])
    away = TEAM_NAME_MAP.get(game["AwayTeam"], game["AwayTeam"])
    match_date = datetime.strptime(game["MatchTime"], "%Y-%m-%d %H:%M")

    if st.button("See Prediction", key=f"pred-{current_gw}-{i}"):

        if home not in known_teams or away not in known_teams:
            st.error(f"Team not found in historical data: {home} / {away}")
        else:
            try:
                hg, ag = predict_match(home, away, match_date)

                # Determine winner
                winner_home = winner_away = ""
                if hg > ag:
                    winner_home = "🏆"
                elif ag > hg:
                    winner_away = "🏆"

                # Display fancy match card
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; justify-content:center; font-size:24px; padding:10px; border:2px solid #1f77b4; border-radius:10px; margin-bottom:10px;">
                        <div style="text-align:center; margin-right:50px;">
                            <img src="{game['HomeLogo']}" width="60"><br>
                            <b>{home}</b><br>{winner_home}
                        </div>
                        <div style="font-size:32px; font-weight:bold; margin:0 20px;">
                            {hg} - {ag}
                        </div>
                        <div style="text-align:center; margin-left:50px;">
                            <img src="{game['AwayLogo']}" width="60"><br>
                            <b>{away}</b><br>{winner_away}
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Prediction error: {e}")
