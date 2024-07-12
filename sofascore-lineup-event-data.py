import json
import pandas as pd
import requests
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Define standard columns
standard_columns = [
    'shirtNumber', 'jerseyNumber', 'position', 'substitute',
    'player.slug', 'player.position', 'player.jerseyNumber', 'player.country.name',
    'statistics.totalPass', 'statistics.accuratePass', 'statistics.totalLongBalls',
    'statistics.goalAssist', 'statistics.minutesPlayed', 'statistics.touches', 
    'statistics.rating', 'statistics.possessionLostCtrl', 'statistics.accurateLongBalls',
    'statistics.totalCross', 'statistics.accurateCross', 'statistics.duelLost',
    'statistics.duelWon', 'statistics.challengeLost', 'statistics.totalContest',
    'statistics.blockedScoringAttempt', 'statistics.totalClearance', 
    'statistics.totalTackle', 'statistics.expectedGoals', 'statistics.keyPass',
    'statistics.expectedAssists', 'statistics.aerialLost', 'statistics.aerialWon', 
    'statistics.onTargetScoringAttempt', 'statistics.ownGoals', 'statistics.fouls',
    'statistics.wasFouled', 'statistics.totalOffside', 'statistics.shotOffTarget',
    'statistics.interceptionWon', 'statistics.dispossessed', 'statistics.wonContest',
    'statistics.goals', 'captain', 'statistics.penaltyWon'
]

def get_match_data(driver, match_url, headers):
    """
    Fetch match data from the provided URL using Selenium and requests.

    Args:
    - driver: Selenium WebDriver instance.
    - match_url: URL of the match.
    - headers: Headers for the requests.

    Returns:
    - DataFrame containing the match lineup data.
    """
    try:
        driver.get(match_url)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        logs_raw = driver.get_log('performance')
        logs = [json.loads(lr["message"])["message"] for lr in logs_raw]

        for x in logs:
            if 'lineups' in x['params'].get('headers', {}).get(':path', ''):
                lineups_url = x['params'].get('headers', {}).get(':path')
                break

        r = requests.get(urljoin("https://sofascore.com", lineups_url), headers=headers)
        if r.status_code == 200:
            data = r.json()
        else:
            return pd.DataFrame()

        home_lineups = pd.json_normalize(data['home']['players']).reindex(columns=standard_columns)
        away_lineups = pd.json_normalize(data['away']['players']).reindex(columns=standard_columns)

        for df in [home_lineups, away_lineups]:
            df.columns = df.columns.str.replace('statistics.', '')
            df.columns = df.columns.str.replace('player.', '')
            df.columns = df.columns.str.replace('slug', 'player_name')

        return pd.concat([home_lineups, away_lineups], ignore_index=True)
    except Exception as e:
        print(f"Error fetching match data: {e}")
        return pd.DataFrame()

def main():
    options = Options()
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(20)

    headers = {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }

    matches = pd.read_csv('Datasets/matches.csv')
    match_list = matches['matches'].to_list()
    id_list = matches['match_id'].to_list()

    base_url = 'https://www.sofascore.com'
    for match, match_id in zip(match_list, id_list):
        match_url = f'{base_url}/{match}/{match_id}'
        lineups = get_match_data(driver, match_url, headers)
        # if not lineups.empty:
        lineups.to_csv('Datasets/lineups.csv', mode='a', index=False, header=False)

    driver.quit()

if __name__ == "__main__":
    main()
