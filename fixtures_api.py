import requests
import pandas as pd
from datetime import datetime

API_TOKEN = "6f4e186a1162460eb33694f338553c71"
url = "https://api.football-data.org/v4/competitions/PL/matches"
headers = {"X-Auth-Token": API_TOKEN}

response = requests.get(url, headers=headers)
data = response.json()

matches = []
today = datetime.now()

for match in data.get("matches", []):
    match_time = datetime.fromisoformat(match["utcDate"][:-1])
    if match_time >= today:  # keep any future match
        matches.append({
            "HomeTeam": match["homeTeam"]["name"],
            "AwayTeam": match["awayTeam"]["name"],
            "MatchTime": match_time.strftime("%Y-%m-%d %H:%M"),
            "Status": match["status"]  # optional, useful for debugging
        })

df_upcoming = pd.DataFrame(matches)
print(df_upcoming)

#"6f4e186a1162460eb33694f338553c71"