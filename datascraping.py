import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

def DownloadDatasetFromGitHubPage(url, rawfile_prefix):
    def DownloadFile(url, file_name):
        response = requests.get(url)
        if response.status_code == 200:
            with open(file_name, "wb") as file:
                file.write(response.content)
            print(f"{file_name} downloaded successfully!")
        else:
            print(f"Failed to download {file_name}. Status code: {response.status_code}")

    driver = requests.get(url)
    soup_source = BeautifulSoup(driver.text, "html.parser")
    data_source = soup_source.find_all(name="div", class_="react-directory-truncate")

    data = []
    for source in data_source:
        a_source = source.find("a")
        if a_source.attrs["aria-label"] == "goalscorers.csv, (File)":
            data.append(rawfile_prefix + a_source.attrs["href"])
        elif a_source.attrs["aria-label"] == "results.csv, (File)":
            data.append(rawfile_prefix + a_source.attrs["href"])
        elif a_source.attrs["aria-label"] == "shootouts.csv, (File)":
            data.append(rawfile_prefix + a_source.attrs["href"])
        else:
            continue

    csv_links = list(set(data))

    with tqdm(total=len(csv_links)) as pbar:
        for link in csv_links:
            file_name = link.split('/')[-1]
            pbar.set_description(f"Downloading {file_name}")
            DownloadFile(link.replace("/blob", ""), file_name)
            pbar.update(1)

# Direction of use

# prefix = "https://raw.githubusercontent.com"
# url = "https://github.com/martj42/international_results"

# DownloadDatasetFromGitHubPage(url=url, rawfile_prefix=prefix)

#  import pandas as apd
#  results_df = pd.read_csv("results.csv")
#  shootouts_df = pd;.read_csv("shootouts.csv")
#  goalscorers_df = pd.read_csv("goalscorers.csv")