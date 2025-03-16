import os
import sys
import time
import traceback
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService


EURO2024_PLAYERS_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "Datasets", "euro2024_players.csv")
EURO2024_PLAYER_RANKINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", "Datasets", "euro2024_player_rankings.csv")
SITE_URL = "https://www.sofascore.com/"


class NoCompetitionOrSeasonData(Exception):
    pass
    

def get_drop_down_options(ddl_button, exclude_options = []):
    ddl_button.click()
    time.sleep(0.25)
    li_options = driver.find_elements(By.XPATH, "//li[@role='option' and contains(@class, 'DropdownItem')]")
    li_options = [li for li in li_options if li.get_attribute("innerText") not in exclude_options]

    return li_options


def get_average_rating(driver):
    div_average_rating = driver.find_element(By.XPATH, "//span[text()='Average Sofascore rating']/following-sibling::div")
    span_average_rating = div_average_rating.find_elements(By.TAG_NAME, "span")[1]
    average_rating = span_average_rating.get_attribute('innerText')

    return average_rating


def get_button_ddl_element(driver, index=1):
    buttons = driver.find_elements(By.XPATH, "//button[contains(@class, 'DropdownButton')]")
    if len(buttons) == 0:
        raise NoCompetitionOrSeasonData()
    print(f"Buttons count: {len(buttons)}, index: {index}")
    temp_index = index
    # In some cases there are just 2 drop down list buttons on the page.
    # In that case decrease the value for the button index by 1.
    if len(buttons) < 3:
        for btn in buttons:
            print(btn.get_attribute("outerHTML"))
        temp_index -= 1
    btn = buttons[temp_index]
    div = btn.find_element(By.CSS_SELECTOR, "div.Text")

    return div


def get_competitions_ddl_element(driver):
    return get_button_ddl_element(driver)


def get_seasons_ddl_element(driver):
    return get_button_ddl_element(driver, index=2)


def get_button_element(driver, elem_text):
    elem = driver.find_element(By.XPATH, f"//bdi[text()='{elem_text}")

    return elem


def get_ddl_item_names(li_options, excludeOption):
    item_names = [li.get_attribute("innerText")
                         for li in get_drop_down_options(button_competition)
                         if li.get_attribute("innerText") != excludeOption].reverse()

    return item_names


def full_stack():
    exc = sys.exc_info()[0]
    if exc is not None:
        f = sys.exc_info()[-1].tb_frame.f_back
        stack = traceback.extract_stack(f)
    else:
        stack = traceback.extract_stack()[:-1]  # last one would be full_stack()
    trc = 'Traceback (most recent call last):\n'
    stackstr = trc + ''.join(traceback.format_list(stack))
    if exc is not None:
        stackstr += '  ' + traceback.format_exc().lstrip(trc)
    return stackstr


def process_option(driver, option_element):
    print("option_element")
    print(option_element.get_attribute("outerHTML"))
    actions = ActionChains(driver)
    btn = option_element.find_element(By.TAG_NAME, "bdi")
    actions.move_to_element(btn).perform()
    btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(btn))
    btn.click()
    time.sleep(0.1)


if __name__ == "__main__":
    driver = None
    try:
        df_players = pd.read_csv(EURO2024_PLAYERS_FILE_PATH)
        # Uncomment following 2 lines to start from the specified player.
        #start_player_index = df_players.loc[df_players.Name == "Mojmír Chytil"].index.tolist()[0]
        #df_players = df_players.iloc[start_player_index:]
        #print(f"start_player_index: {start_player_index}")
        print(f"Players count: {len(df_players)}")

        data = np.array([], dtype=[("name", str), ("competition", str), ("season", str), ("average_rating", np.float32)])
        df_player_rankings = pd.DataFrame(data, columns=['name', 'competition', 'season', 'average_rating'])
        r_options = Options()
        r_options.add_argument("--disable-notifications")
        r_options.add_argument("--disable-extensions")
        r_options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(options=r_options)
        driver.get(SITE_URL)
        failed_processing = []

        for player_name in df_players.Name.tolist():
            try:
                print(f"Processing player {player_name} data ...")
                form = driver.find_element(By.CSS_SELECTOR, "header form.Box")
                input_placeholder = form.find_element(By.CSS_SELECTOR, "input")
                print(input_placeholder.get_attribute("value"))
                while input_placeholder.get_attribute("value") != "":
                    input_placeholder.clear()
                    time.sleep(1)
                input_placeholder.send_keys(player_name)
                time.sleep(2)
                div_drop_down = driver.find_element(By.XPATH, "//form[@display='flex']/following-sibling::div")
                a_player_links = div_drop_down.find_elements(By.CSS_SELECTOR, "a")
                if len(a_player_links) == 0:
                    print(f"Player {player_name} not found, skipping ...")
                    continue
                elif len(a_player_links) == 1:
                    a_player_links[0].click()
                else:
                    print(f"Links count: {len(a_player_links)}")
                    for anchor_elem in a_player_links:
                        spans = anchor_elem.find_elements(By.TAG_NAME, "span")
                        if spans[0].get_attribute("innerText") == player_name:
                            driver.execute_script("arguments[0].scrollIntoView(true);", anchor_elem) 
                            time.sleep(0.5)
                            anchor_elem.click()
                            break
                time.sleep(2)
                processed_competitions = []
                processed_seasons = []
                index_errors_counts = 0
                while True:
                    print("Getting button season")
                    button_season = get_seasons_ddl_element(driver)
                    print("Getting button competition")
                    button_competition = get_competitions_ddl_element(driver)
                    competition_name = button_competition.get_attribute("innerText")
                    season_name = button_season.get_attribute("innerText")
                    try:
                        average_rating = get_average_rating(driver)
                        df_player_rankings = df_player_rankings._append({
                            "name": player_name, "competition": competition_name,
                            "season": season_name, "average_rating": average_rating
                        }, ignore_index=True)
                        print(f"Competition name: {competition_name}, season_name: {season_name}, average rating: {average_rating}")
                    except (NoSuchElementException, IndexError) as ex:
                        print(f"Failed to process competition {competition_name}, season {season_name}.")
                        if isinstance(ex, NoSuchElementException) and ("Average Sofascore rating" not in str(ex)):
                            raise ex
                    processed_seasons.append(season_name)
                    print("Getting season drop down options ...")
                    season_options = get_drop_down_options(button_season, processed_seasons)
                    if len(season_options) > 0:
                        season_option = season_options.pop()
                        process_option(driver, season_option)
                    else:
                        processed_seasons.clear()
                        processed_competitions.append(competition_name)
                        competition_options = get_drop_down_options(button_competition, processed_competitions)
                        if len(competition_options) == 0:
                            break
                        competition_option = competition_options.pop()
                        process_option(driver, competition_option)
            except NoCompetitionOrSeasonData:
                print(f"No competition or season data found for player {player_name}")
                failed_processing.append(player_name)
            except Exception as ex:
                print(type(ex))
                if "stale element not found" in str(ex):
                    print(f"Player {player_name}, stale element error.")
                    driver.refresh()
                else:
                    raise ex
    except Exception as ex:
        print(ex)
        print(full_stack())
    finally:
        if len(failed_processing) > 0:
            print(f"Failed to process following players: {failed_processing}")
        df_player_rankings.to_csv(EURO2024_PLAYER_RANKINGS_FILE_PATH, index=False)
        if driver is not None:
            driver.close()
