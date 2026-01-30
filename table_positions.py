# table_positions.py
import pandas as pd

class TablePositions:
    def __init__(self, csv_file):
        """
        Initializes the table calculator with the combined CSV.
        Calculates positions for all dates in the season.
        """
        self.df = pd.read_csv(csv_file)
        # Ensure Date is datetime
        self.df["Date"] = pd.to_datetime(self.df["Date"], dayfirst=True, errors="coerce")
        # Sort matches by date
        self.df.sort_values("Date", inplace=True)
        # Initialize position history
        self.position_history = self._calculate_positions()

    def _calculate_positions(self):
        """
        Calculates cumulative points, goal difference, and positions after each match.
        Returns a dataframe: Date | Team | Points | GoalDiff | Position
        """
        teams = self.df["HomeTeam"].unique()
        standings = {team: {"Points": 0, "GD": 0, "GF": 0, "GA": 0} for team in teams}
        history = []

        for idx, row in self.df.iterrows():
            date = row["Date"]
            home = row["HomeTeam"]
            away = row["AwayTeam"]
            home_goals = row["FTHG"]
            away_goals = row["FTAG"]

            # Update goals for GD
            standings[home]["GF"] += home_goals
            standings[home]["GA"] += away_goals
            standings[home]["GD"] = standings[home]["GF"] - standings[home]["GA"]

            standings[away]["GF"] += away_goals
            standings[away]["GA"] += home_goals
            standings[away]["GD"] = standings[away]["GF"] - standings[away]["GA"]

            # Update points
            if home_goals > away_goals:
                standings[home]["Points"] += 3
            elif away_goals > home_goals:
                standings[away]["Points"] += 3
            else:
                standings[home]["Points"] += 1
                standings[away]["Points"] += 1

            # Sort teams by Points, GD, GF
            sorted_teams = sorted(
                standings.items(),
                key=lambda x: (x[1]["Points"], x[1]["GD"], x[1]["GF"]),
                reverse=True
            )

            # Assign positions
            for pos, (team, stats) in enumerate(sorted_teams, start=1):
                history.append({
                    "Date": date,
                    "Team": team,
                    "Points": stats["Points"],
                    "GD": stats["GD"],
                    "GF": stats["GF"],
                    "GA": stats["GA"],
                    "Position": pos
                })

        history_df = pd.DataFrame(history)
        return history_df

    def get_team_position(self, team, date):
        """
        Returns the position of the team on a given date.
        If no matches have been played yet, returns None.
        """
        df_team = self.position_history[self.position_history["Team"] == team]
        df_team = df_team[df_team["Date"] <= pd.to_datetime(date)]
        if df_team.empty:
            return None
        return df_team.iloc[-1]["Position"]

    def get_team_stats(self, team, date):
        """
        Returns Points, GD, GF, GA of a team as of a given date.
        """
        df_team = self.position_history[self.position_history["Team"] == team]
        df_team = df_team[df_team["Date"] <= pd.to_datetime(date)]
        if df_team.empty:
            return None
        last = df_team.iloc[-1]
        return {
            "Points": last["Points"],
            "GD": last["GD"],
            "GF": last["GF"],
            "GA": last["GA"],
            "Position": last["Position"]
        }

# --- Usage example ---
# table = TablePositions("E0_combined.csv")
# pos = table.get_team_position("Arsenal", "2025-12-01")
# stats = table.get_team_stats("Man City", "2025-10-15")
# print(pos, stats)
