import os
from pathlib import Path


OUTPUT_DIR_PATH = os.path.join(os.path.dirname(__file__), "..", "output")
DATASETS_DIR_PATH = os.path.join(os.path.dirname(__file__), "datasets")
APP_LOG_PATH = os.path.join(OUTPUT_DIR_PATH, "app.log")
STATSBOMB_OPEN_DATA_LOCAL_PATH = os.environ["OPEN_DATA_REPO_PATH"]
DATA_POINTS_FILE_PATH = os.path.join(DATASETS_DIR_PATH, "data_points.csv")
MATCH_KPI_FILE_PATH = os.path.join(DATASETS_DIR_PATH, "match_kpi.csv")