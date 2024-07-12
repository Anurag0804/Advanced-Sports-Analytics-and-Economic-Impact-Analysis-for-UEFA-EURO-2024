# A competing risk survival analysis of the impacts of team formation on goals in professional football

### Progress
![](https://geps.dev/progress/50)

The folder contains an implementation of the method for investigating the influence of team formation on goal-scoring efficiency through analysing the time required for a goal to be scored in elite football matches.
The exact process is described in the paper https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1323930/full

## 1. Dataset

The project is using the open data provided by Statsbomb.
The dataset is available at https://github.com/statsbomb/open-data.

## 2. Project structure

* [datasets](./datasets)
  * [data_points.csv](./datasets/data_points.csv)  - match information segmented into data points based on events such as halftime, goals, red cards and team formation modifications. 
   * [match_kpi.csv](./datasets/match_kpi.csv) - KPIs for each match such as the number of shots, passes, scores, offensive and defensive actions etc.
* [extract_data.py](./extract_data.py) - extracts important information for each match and stores it in the data_points.csv and match_kpi.csv files.  
* [team_formation_impact_to_match_outcome_analysis.ipynb](./team_formation_impact_to_match_outcome_analysis.ipynb) - analysis of effects of team formation to match outcome.  
 * [visualize_formations_correspondance_table.ipynb](./visualize_formations_correspondance_table.ipynb) - visualization of various information such as total percentage of team formations used in matches, team formations correspondance table etc.


## 3. Data extraction process

Data is extracted using the [extract_data.py](./extract_data.py) script. The script by default uses multiple processes in order to speed up the data extraction process. The extracted data is stored in [datasets/data_points.csv](./datasets/data_points.csv) and [datasets/match_kpi.csv](./datasets/match_kpi.csv) files.

## 4. Match KPIs data format

The file [datasets/match_kpi.csv](./datasets/match_kpi.csv) with match key performance indicators contains following data:

| Column name   |  Data type     |  Description  |
| ------------- | ------------- | ------------- 
| match_id | int | match identifier |
| team | string | name of the team |
| formation | int | team formation type |
| opposing_team_formation | int | opposing team formation type |
| shot | int | number of shots in a match related to the team formation |
| pass | int | number of passes in a match related to the team formation |
| under_pressure | int | events which are naturally performed under pressure like duels, dribbles etc
| score | int | number of scores related to the current team and the team formation |
| counterpress | int | various defensive events, including: pressure, dribbled past, 50-50, duel, block, interception, and foul committed (not offensive) |
| formation_play_duration | timedelta | play duration with the current team formation |
| formation_play_duration_ratio | float | ratio between the match full time duration and the formation play duration in the match, used only for calculating the extrapolated values for other KPIs |
| shot_mean | float | extrapolated value for shots for the team formations played in a match less than the full time | 
| pass_mean | float | extrapolated value for passes for the team formations played in a match less than the full time |
| under_pressure_mean | float | extrapolated value for under pressure events for the team formations played in a match less than the full time |
| counterpress_mean |  float | extrapolated value for counter pressure events for the team formations played in a match less than the full time |
| home_or_away | int | 1 if the team is a home team otherwise 0 |
| goals | int | total goals in the match |

## 5. Data points data format

The file [datasets/data_points.csv](./datasets/data_points.csv) with the data for events of interest such as match start, half time, tactical shift and red card, contains following data:

| Column name   |  Data type     |  Description  |
| ------------- | ------------- | ------------- 
| team | string | the team name |
| timestamp | timedelta | time of the event measured from the start of the match. |
| shot_outcome | string | can have only the "Goal" value and it's related to the "Shot" event |
| type | string | the type of the event |
| formation | int | team formation type |
| opposing_team_formation | int | opposing team formation |
| formation_play_duration | timedelta | play duration with the current team formation |
| goal_difference | int | the goal difference at the start of the event |
| number_of_goals | int | the total number of goals at the start of the event |
| match_id | int | match identifier |
| mean_expected_goals_per_game | float | the mean expected goals per game for the current formation |

## 4. ML model

## 5. Conclusion