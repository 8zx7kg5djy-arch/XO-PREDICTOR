import pandas as pd
import numpy as np
import random
from datetime import datetime

DATA_FILE = "E0_combined.csv"

def fetch_finished_matches(api_token, local_df):
    import requests
    from datetime import datetime
    
    url = "https://api.football-data.org/v4/competitions/PL/matches?status=FINISHED"
    headers = {"X-Auth-Token": api_token}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
    except Exception as e:
        print(f"Error fetching finished matches: {e}")
        return local_df
    
    # Convert API matches to DataFrame
    new_rows = []
    for m in matches:
        match_date = datetime.fromisoformat(m["utcDate"].replace("Z", ""))
        new_rows.append({
            "Date": match_date.strftime("%Y-%m-%d"),
            "HomeTeam": m["homeTeam"]["name"],
            "AwayTeam": m["awayTeam"]["name"],
            "FTHG": m["score"]["fullTime"]["home"],
            "FTAG": m["score"]["fullTime"]["away"]
        })
    
    if not new_rows:
        return local_df
    
    new_df = pd.DataFrame(new_rows)
    
    # Append only new matches that are not already in local CSV
    combined_df = pd.concat([local_df, new_df]).drop_duplicates(
        subset=["Date", "HomeTeam", "AwayTeam"], keep="last"
    ).reset_index(drop=True)
    
    # Save updated CSV
    combined_df.to_csv("E0_combined.csv", index=False)
    
    return combined_df



def load_data(api_token=None):
    df = pd.read_csv(DATA_FILE)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    
    if api_token:
        df = fetch_finished_matches(api_token, df)
    
    return df



# ---------------- HELPERS ---------------- #
def get_last_matches(df, team, n=5, before_date=None):
    games = df[((df["HomeTeam"] == team) | (df["AwayTeam"] == team))]
    if before_date is not None:
        games = games[games["Date"] < before_date]
    return games.tail(n)

def goals_for_against(row, team):
    if row["HomeTeam"] == team:
        return row["FTHG"], row["FTAG"]
    else:
        return row["FTAG"], row["FTHG"]

def form_score(df, team, match_date):
    games = get_last_matches(df, team, 5, match_date)
    if games.empty:
        return 0.0

    score = 0
    for i, row in enumerate(games.itertuples()):
        decay = 1 - (0.12 * (4 - i))  # time decay
        gf, ga = goals_for_against(row._asdict(), team)

        if gf > ga:
            score += 1.0 * decay
        elif gf == ga:
            score += 0.4 * decay
        else:
            score -= 0.6 * decay
    return score

def avg_goals(df, team, match_date, for_goals=True):
    games = get_last_matches(df, team, 5, match_date)
    if games.empty:
        return 1.2
    goals = []
    for _, row in games.iterrows():
        gf, ga = goals_for_against(row, team)
        goals.append(gf if for_goals else ga)
    return np.mean(goals)

def h2h_score(df, home, away, match_date):
    h2h = df[
        (((df["HomeTeam"] == home) & (df["AwayTeam"] == away)) |
         ((df["HomeTeam"] == away) & (df["AwayTeam"] == home))) &
        (df["Date"] < match_date)
    ].tail(5)

    if h2h.empty:
        return 0, 0

    h_score, a_score = 0, 0
    for _, row in h2h.iterrows():
        if row["HomeTeam"] == home:
            if row["FTHG"] > row["FTAG"]:
                h_score += 1
            elif row["FTHG"] < row["FTAG"]:
                a_score += 1
        else:
            if row["FTAG"] > row["FTHG"]:
                h_score += 1
            elif row["FTAG"] < row["FTHG"]:
                a_score += 1

    return h_score, a_score

# ---------------- PREDICTION ---------------- #
def predict_match(home, away, match_date, gameweek=None):
    """
    Returns:
        home_goals, away_goals
    """
    match_date = pd.to_datetime(match_date)
    df = load_data()

    # --- Feature components ---
    home_form = form_score(df, home, match_date)
    away_form = form_score(df, away, match_date)

    home_attack = avg_goals(df, home, match_date, True)
    away_attack = avg_goals(df, away, match_date, True)

    home_defense = avg_goals(df, home, match_date, False)
    away_defense = avg_goals(df, away, match_date, False)

    h2h_home, h2h_away = h2h_score(df, home, away, match_date)

    # --- Weighted score ---
    home_score = 0.50*home_form + 0.25*home_attack - 0.15*away_defense + 0.10*h2h_home
    away_score = 0.50*away_form + 0.25*away_attack - 0.15*home_defense + 0.10*h2h_away

    # --- Base goals ---
    home_goals = 1.1 + home_score
    away_goals = 1.0 + away_score

    # --- Defense shield ---
    if away_defense < 1.0:
        home_goals -= 0.3
    if home_defense < 1.0:
        away_goals -= 0.3

    # --- Clamp before randomness ---
    home_goals = max(0, round(home_goals))
    away_goals = max(0, round(away_goals))

    # --- Deterministic Randomness ---
    if gameweek is not None:
        seed = hash(f"{gameweek}-{home}-{away}")
        rnd = random.Random(seed)
        # 50% chance to add 1 goal to a random team
        if rnd.random() < 0.5:
            if rnd.random() < 0.5:
                home_goals += 1
            else:
                away_goals += 1
        # Deduct 1 goal from up to 3 teams with >=1 goal
        teams_goals = [("home", home_goals), ("away", away_goals)]
        rnd.shuffle(teams_goals)
        deducted = 0
        for idx, (team_name, goals) in enumerate(teams_goals):
            if goals >= 1 and deducted < 3:
                if team_name == "home":
                    home_goals -= 1
                else:
                    away_goals -= 1
                deducted += 1

    # --- Final clamp ---
    home_goals = max(0, home_goals)
    away_goals = max(0, away_goals)

    return home_goals, away_goals
