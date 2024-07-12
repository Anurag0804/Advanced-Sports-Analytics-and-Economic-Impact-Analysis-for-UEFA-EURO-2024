import os
import consts
import pandas as pd


if __name__ == "__main__":
    df_match_kpi = pd.read_csv(consts.MATCH_KPI_FILE_PATH)
    df_attack_formations_scores = df_match_kpi.loc[df_match_kpi["home_or_away"] == 1][
        ["formation", "opposing_team_formation", "score"]].groupby(
        ["formation", "opposing_team_formation"]).sum().reset_index()
    df_defense_formations_scores = df_match_kpi.loc[df_match_kpi["home_or_away"] == 0][
        ["formation", "opposing_team_formation", "score"]].groupby(
        ["formation", "opposing_team_formation"]).sum().reset_index()
    df_attack_defense_scores_pivot_table = pd.pivot_table(
        df_attack_formations_scores, index=["formation"], columns=["opposing_team_formation"],
        values="score", aggfunc="sum", margins=True, margins_name='Sum')
    df_defense_attack_scores_pivot_table = pd.pivot_table(
        df_defense_formations_scores, index=["formation"], columns=["opposing_team_formation"],
        values="score", aggfunc="sum", margins=True, margins_name='Sum')

