import os
import sys
import math
import queue
import consts
import logging
import numpy as np
import pandas as pd
from time import time
from pathlib import Path
import multiprocessing as mp
from statsbombpy_local import sb
from datetime import datetime, timedelta
from multiprocessing import current_process
from concurrent.futures import ProcessPoolExecutor


logger = logging.getLogger(__name__)
pd.options.mode.copy_on_write = True


def get_matches_ids(data_path: str, max_events=-1) -> list[int]:
    matches_ids = []

    for idx, data_file in enumerate(os.listdir(data_path)):
        match_id = int(data_file.split(".")[0])
        matches_ids.append(match_id)
        if max_events != -1 and idx+1 == max_events:
            break

    return matches_ids


def update_nan_timestamp(row, match_end_timestamp):
    if row["formation_play_duration"] is pd.NaT:
        return match_end_timestamp - row["timestamp"]

    return row["formation_play_duration"]


def set_formation_value(row):
    if isinstance(row, dict):
        return row["formation"]
    return ""

def normalize_action_data(df_data: pd.DataFrame, match_end_timestamp: timedelta) -> pd.DataFrame:
    df_data_normalized = df_data.copy()
    # If the formation_play_duration_ration value is 1 it means that the formation is being played for the entire match.
    # The value of 2 means that the formation is played either during the first or the second half of the match.
    df_data_normalized["formation_play_duration_ratio"] = ((match_end_timestamp-datetime(1900, 1, 1)).total_seconds() /
                                                            df_data["formation_play_duration"].dt.total_seconds())
    df_data_normalized["shot_mean"] = df_data["shot"] * df_data_normalized["formation_play_duration_ratio"]
    df_data_normalized["pass_mean"] = df_data["pass"] * df_data_normalized["formation_play_duration_ratio"]
    df_data_normalized["under_pressure_mean"] = df_data["under_pressure"] * df_data_normalized["formation_play_duration_ratio"]
    df_data_normalized["counterpress_mean"] = df_data["counterpress"] * df_data_normalized["formation_play_duration_ratio"]

    return df_data_normalized


def get_match_kpi(df_events: pd.DataFrame, df_data_points: pd.DataFrame, match_id: int) -> pd.DataFrame:
    actions_filter = ((df_events.under_pressure == True) | (df_events.counterpress == True) |
                      (df_events.type == "Shot") | (df_events.type == "Pass"))
    df_selected_actions = df_events.loc[actions_filter]
    df_selected_actions["timestamp"] = pd.to_datetime(df_selected_actions["timestamp"], format='%H:%M:%S.%f')
    for index, row in df_data_points.iterrows():
        df_selected_actions.loc[((df_selected_actions["team"] == row["team"]) &
                                 (df_selected_actions.timestamp > row["timestamp"])), "formation"] = row["formation"]
        df_selected_actions.loc[((df_selected_actions["team"] != row["team"]) &
                                 (df_selected_actions.timestamp > row["timestamp"])), "opposing_team_formation"] = row["formation"]
    df_selected_actions["pass"] = 0
    df_selected_actions["shot"] = 0
    df_selected_actions["score"] = 0
    df_selected_actions.loc[df_selected_actions.type == "Pass", "pass"] = 1
    df_selected_actions.loc[df_selected_actions.type == "Shot", "shot"] = 1
    df_selected_actions.loc[df_selected_actions.shot_outcome == "Goal", "score"] = 1
    df_selected_actions["counterpress"] = df_selected_actions["counterpress"].fillna(0)
    df_selected_actions["under_pressure"] = df_selected_actions["under_pressure"].fillna(0)
    df_selected_actions.loc[df_selected_actions.counterpress == True, "counterpress"] = 1
    df_selected_actions["match_id"] = match_id

    return df_selected_actions


def get_match_end_timestamp(df_events: pd.DataFrame, period: int = 1) -> timedelta:
    str_half_end_timestamp = df_events.loc[(df_events.type == "Half End") & (df_events.period == 1)]["timestamp"].tolist()[0]
    half_end_timestamp = datetime.strptime(str_half_end_timestamp, "%H:%M:%S.%f")
    if period == 1:
        return half_end_timestamp
    half_end_timestamp_delta = timedelta(minutes=half_end_timestamp.minute,
                                         seconds=half_end_timestamp.second,
                                         microseconds=half_end_timestamp.microsecond)
    str_match_end_timestamp = df_events.loc[(df_events.type == "Half End") & (df_events.period == 2)]["timestamp"].tolist()[0]
    match_end_timestamp = datetime.strptime(str_match_end_timestamp, "%H:%M:%S.%f")
    match_end_total_timestamp = match_end_timestamp + half_end_timestamp_delta

    return match_end_total_timestamp


def set_opposing_team_formation(row, df_data_points):
    df_opposing_team = df_data_points.loc[(df_data_points.team != row["team"]) & (df_data_points.timestamp < row["timestamp"])]
    if df_opposing_team is None or len(df_opposing_team) == 0:
        df_opposing_team = df_data_points.loc[df_data_points.team != row["team"]].iloc[0]
        opposing_team_formation = df_opposing_team.formation
    else:
        opposing_team_formation = df_opposing_team.iloc[-1].formation
    return opposing_team_formation


def get_data_points(df_events: pd.DataFrame, match_id: int) -> pd.DataFrame:
    data_points_filter = ((df_events.type == "Starting XI") | (df_events.type == "Tactical Shift") |
                          ((df_events.type == "Half End") & (df_events.period == 1)) |
                          (df_events.shot_outcome == "Goal") |
                          ((df_events.type == "Bad Behaviour") & (df_events.get("bad_behaviour_card") == "Red Card")) |
                          ((df_events.type == "Foul Committed") & (df_events.get("foul_committed_card") == "Red Card"))
                          )
    df_data_points = df_events.loc[data_points_filter]
    df_data_points.reset_index(drop=True, inplace=True)
    df_data_points["timestamp"] = pd.to_datetime(df_data_points["timestamp"], format="%H:%M:%S.%f")
    # Change timestamp to range from 0 to 90 minutes.
    half_end_timestamp = get_match_end_timestamp(df_events)
    df_data_points.loc[df_data_points.period == 2, "timestamp"] += timedelta(minutes=half_end_timestamp.minute,
                                                                             seconds=half_end_timestamp.second,
                                                                             microseconds=half_end_timestamp.microsecond)
    df_red_card_events = df_data_points.loc[
        ((df_data_points.type == "Bad Behaviour") & (df_data_points.get("bad_behaviour_card") == "Red Card")) |
        ((df_data_points.type == "Foul Committed") & (df_data_points.get("foul_committed_card") == "Red Card"))
        ]
    match_end_timestamp = None
    if df_red_card_events is not None and len(df_red_card_events.index) > 0:
        logger.debug(f"There are {len(df_red_card_events.index)} red cards in the match with in ID {match_id}.")
        # Select just the first red card event. We are not interested in the rest of the events because the
        # first red card event will mark the end of the match.
        first_red_card_event_timestamp = df_red_card_events.iloc[0]["timestamp"]
        df_data_points_filtered = df_data_points.loc[df_data_points["timestamp"] <= first_red_card_event_timestamp].reset_index()
        logger.debug(f"Number of change events prior to the red card event: {len(df_data_points_filtered)}")
        logger.debug(f"Total number of tactics change events: {len(df_data_points)}")
        df_data_points = df_data_points_filtered
        if df_data_points is None or len(df_data_points) == 0:
            return None
        # Match events collection should end with the first red card event.
        match_end_timestamp = first_red_card_event_timestamp
    df_data_points = df_data_points[["team", "tactics", "timestamp", "shot_outcome", "type", "period"]]
    #df_data_points[df_data_points["tactics"].isna() == False, "formation"] = df_data_points["tactics"].apply(lambda row: row["formation"]).astype(str)
    df_data_points["formation"] = df_data_points["tactics"].apply(set_formation_value).astype(str)
    # Set the formation value for the events that are not related to the changes in tactics.
    # Use the value for the formation from the last row that is related to the change in tactics event.
    while "" in df_data_points["formation"].unique():
        teams = df_data_points.team.unique()
        for team in teams:
            df_team = df_data_points.loc[df_data_points["team"] == team]
            df_team.loc[((df_team["formation"] == "") & (df_data_points["team"] == team)), "formation"] = df_team["formation"].shift(1)
            df_data_points.loc[df_data_points["team"] == team] = df_team
    df_data_points["opposing_team_formation"] = df_data_points.apply(set_opposing_team_formation, args=(df_data_points,), axis=1)
    # Prior calculating the timestamps diff values the data points DataFrame needs to be sorted by the timestamp
    # column in the asceding order.
    df_data_points.sort_values(by="timestamp", inplace=True)
    df_data_points.reset_index(inplace=True)
    df_data_points["diffs"] = df_data_points.groupby(by=["team"])["timestamp"].diff()
    # Shift values in colums with timestamp differences up one row
    df_data_points["formation_play_duration"] = df_data_points.groupby(by=["team"])["diffs"].transform(lambda r: r.shift(-1))
    if match_end_timestamp is None:
        match_end_timestamp = get_match_end_timestamp(df_events, period=2)
    df_data_points["formation_play_duration"] = df_data_points.apply(update_nan_timestamp, args=(match_end_timestamp,), axis=1)
    df_data_points.drop(columns=["tactics", "diffs", "period"], inplace=True)
    home_team = df_events.iloc[0]["team"]
    away_team = df_events.iloc[1]["team"]
    df_data_points["goal_difference"] = 0
    df_data_points["number_of_goals"] = 0
    for index, row in df_data_points.iloc[2:].iterrows():
        if row["shot_outcome"] == "Goal":
            df_data_points.loc[df_data_points["timestamp"] > row["timestamp"], "number_of_goals"] += 1
            df_data_points.loc[(df_data_points["team"] == row["team"]) &
                               (df_data_points["timestamp"] > row["timestamp"]), "goal_difference"] += 1
            df_data_points.loc[(df_data_points["team"] != row["team"]) &
                               (df_data_points["timestamp"] > row["timestamp"]), "goal_difference"] -= 1

    return df_data_points


def extract_data_worker(matches_queue: queue.Queue, fetched_data_queue: queue.Queue) -> None:
    pd.options.mode.copy_on_write = True
    matches_ids = matches_queue.get()
    df_data_points_total = None
    df_match_kpi_total = None

    logger = logging.getLogger()
    # log all messages, debug and up
    logger.setLevel(logging.DEBUG)
    process = current_process()
    logger.debug(f"{process.name} | matches size {len(matches_ids)}")

    for match_id in matches_ids:
        df_events = sb.events(match_id=match_id)
        df_data_points = get_data_points(df_events, match_id)
        if df_data_points is None or len(df_data_points) == 0:
            continue
        df_data_points["match_id"] = match_id
        df_match_kpi = get_match_kpi(df_events, df_data_points, match_id)
        df_match_kpi_groupped = df_match_kpi[
            ["match_id", "team", "formation", "opposing_team_formation",
             "shot", "pass", "under_pressure", "score", "counterpress"]].groupby(
            by=["match_id", "team", "formation", "opposing_team_formation"]).sum().reset_index()
        df_data_points_groupped = (df_data_points[["team", "formation", "formation_play_duration"]]
                                   .groupby(by=["team", "formation"])).sum().reset_index()
        df_match_kpi_groupped = df_match_kpi_groupped.merge(df_data_points_groupped, how="inner",
                                                            on=["team", "formation"])
        match_end_timestamp = get_match_end_timestamp(df_events, period=2)
        df_match_kpi_groupped = normalize_action_data(df_match_kpi_groupped, match_end_timestamp)
        home_team = df_events.iloc[0]["team"]
        away_team = df_events.iloc[1]["team"]
        df_match_kpi_groupped["home_or_away"] = 1
        df_match_kpi_groupped.loc[df_match_kpi_groupped["team"] == away_team, "home_or_away"] = 0
        df_goals = df_events.loc[df_events.shot_outcome == "Goal"]
        df_match_kpi_groupped["goals"] = len(df_goals)
        df_data_points_total = df_data_points.copy() if df_data_points_total is None else pd.concat(
            [df_data_points_total, df_data_points])
        df_match_kpi_total = df_match_kpi_groupped.copy() if df_match_kpi_total is None else pd.concat(
            [df_match_kpi_total, df_match_kpi_groupped])

    df_shots_and_goals = df_match_kpi_total[["match_id", "formation", "shot", "goals"]].groupby(
        by=["match_id", "formation"]).max().reset_index()
    df_shots_and_goals_per_formation = df_shots_and_goals[["formation", "shot", "goals"]].groupby(
        "formation").sum().reset_index()
    df_shots_and_goals_per_formation["mean_expected_goals_per_game"] = \
        df_shots_and_goals_per_formation["goals"] / df_shots_and_goals_per_formation["shot"]
    df_shots_and_goals_per_formation.drop(columns=["shot", "goals"], inplace=True)
    df_data_points_total = df_data_points_total.merge(df_shots_and_goals_per_formation, on="formation", validate="m:1")

    fetched_data_queue.put((df_match_kpi_total, df_data_points_total))
    matches_queue.task_done()


def extract_data_single_proc(matches_ids: list[int]) -> pd.DataFrame:
    df_data_points_total = None
    df_match_kpi_total = None

    for match_id in matches_ids:
        df_events = sb.events(match_id=match_id)
        df_data_points = get_data_points(df_events, match_id)
        if df_data_points is None or len(df_data_points) == 0:
            continue
        df_data_points["match_id"] = match_id
        df_match_kpi = get_match_kpi(df_events, df_data_points, match_id)
        df_match_kpi_groupped = df_match_kpi[
            ["match_id", "team", "formation", "opposing_team_formation",
             "shot", "pass", "under_pressure", "score", "counterpress"]].groupby(
            by=["match_id", "team", "formation", "opposing_team_formation"]).sum().reset_index()
        df_data_points_groupped = (df_data_points[["team", "formation", "formation_play_duration"]]
                                   .groupby(by=["team", "formation"])).sum().reset_index()
        df_match_kpi_groupped = df_match_kpi_groupped.merge(df_data_points_groupped, how="inner",
                                                            on=["team", "formation"])
        match_end_timestamp = get_match_end_timestamp(df_events, period=2)
        df_match_kpi_groupped = normalize_action_data(df_match_kpi_groupped, match_end_timestamp)
        home_team = df_events.iloc[0]["team"]
        away_team = df_events.iloc[1]["team"]
        df_match_kpi_groupped["home_or_away"] = 1
        df_match_kpi_groupped.loc[df_match_kpi_groupped["team"] == away_team, "home_or_away"] = 0
        df_goals = df_events.loc[df_events.shot_outcome == "Goal"]
        df_match_kpi_groupped["goals"] = len(df_goals)
        df_data_points_total = df_data_points.copy() if df_data_points_total is None else pd.concat(
            [df_data_points_total, df_data_points])
        df_match_kpi_total = df_match_kpi_groupped.copy() if df_match_kpi_total is None else pd.concat(
            [df_match_kpi_total, df_match_kpi_groupped])

    df_shots_and_goals = df_match_kpi_total[["match_id", "formation", "shot", "goals"]].groupby(
        by=["match_id", "formation"]).max().reset_index()
    df_shots_and_goals_per_formation = df_shots_and_goals[["formation", "shot", "goals"]].groupby(
        "formation").sum().reset_index()
    df_shots_and_goals_per_formation["mean_expected_goals_per_game"] = \
        df_shots_and_goals_per_formation["goals"] / df_shots_and_goals_per_formation["shot"]
    df_shots_and_goals_per_formation.drop(columns=["shot", "goals"], inplace=True)
    df_data_points_total = df_data_points_total.merge(df_shots_and_goals_per_formation, on="formation", validate="m:1")

    return (df_match_kpi_total, df_data_points_total)


def extract_data(matches_ids: list[int], parallel_processes_count=os.cpu_count()) -> pd.DataFrame:
    matches_count = len(matches_ids)
    matches_slice_size = round(len(matches_ids) / parallel_processes_count)

    with mp.Manager() as manager:
        fetched_data_queue = manager.Queue()
        matches_queue = manager.Queue()
        for i in range(parallel_processes_count):
            start = i * matches_slice_size
            end = (i + 1) * matches_slice_size
            logger.debug(f"Start slice: {start}, end slice: {end}")
            matches_queue.put(matches_ids[start:end])
        logger.debug(f"Queue size: {matches_queue.qsize()}")
        with ProcessPoolExecutor(max_workers=parallel_processes_count) as executor:
            executor.map(extract_data_worker,
                         [matches_queue]*parallel_processes_count,
                         [fetched_data_queue]*parallel_processes_count)
        matches_queue.join()
        logger.debug(f"Fecthed data queue size: {fetched_data_queue.qsize()}")
        df_match_kpi_total = None
        df_data_points_total = None
        while not fetched_data_queue.empty():
            df_match_kpi, df_data_points = fetched_data_queue.get()
            df_data_points_total = df_data_points.copy() if df_data_points_total is None else pd.concat(
                [df_data_points_total, df_data_points])
            df_match_kpi_total = df_match_kpi.copy() if df_match_kpi_total is None else pd.concat(
                [df_match_kpi_total, df_match_kpi])

    return (df_match_kpi_total, df_data_points_total)


if __name__ == "__main__":
    start_time = time()
    Path(consts.OUTPUT_DIR_PATH).mkdir(parents=True, exist_ok=True)
    Path(consts.DATASETS_DIR_PATH).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.FileHandler(consts.APP_LOG_PATH), logging.StreamHandler(sys.stdout)])
    matches_ids = get_matches_ids(os.path.join(consts.STATSBOMB_OPEN_DATA_LOCAL_PATH, "data", "events"))
    logger.debug(f"Matches count: {len(matches_ids)}")
    df_match_kpi_total, df_data_points_total = extract_data(matches_ids, parallel_processes_count=6)
    #df_match_kpi_total, df_data_points_total = extract_data_single_proc(matches_ids[:4])
    #df_match_kpi_total.sort_values(by="match_id", inplace=True)
    df_data_points_total.sort_values(by="match_id", inplace=True)
    df_match_kpi_total.reset_index(drop=True, inplace=True)
    df_match_kpi_total.to_csv(consts.MATCH_KPI_FILE_PATH, index=False)
    df_data_points_total.reset_index(drop=True, inplace=True)
    df_data_points_total.to_csv(consts.DATA_POINTS_FILE_PATH, index=False)
    elapsed_time = time() - start_time
    logger.debug(f"Elapsed time: {elapsed_time}")
    print(len(df_match_kpi_total), len(df_data_points_total))