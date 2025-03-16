import requests
from bs4 import BeautifulSoup
import pandas as pd


# URL of the page to scrape
url = 'https://fbref.com/en/comps/676/2021/2021-European-Championship-Stats'


# Send a GET request to the URL
response = requests.get(url)


# Check if the request was successful
if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
   
    # Find the table containing the data
    table = soup.find('table', {'id': 'results20216760_overall'})


    if table:
        # Extract headers
        headers = [th.text.strip() for th in table.find('thead').find_all('th')]


        # Prepare a list to hold the data
        data = []


        # Extract all rows
        rows = table.find_all('tr')


        for row in rows:
            # Extract the data from each cell
            cells = row.find_all(['th', 'td'])
            row_data = [cell.text.strip() for cell in cells]
            # Ensure the row_data has the same length as headers
            if len(row_data) == len(headers):
                data.append(row_data)


        # Remove the first row (headers) from the data
        data = data[1:]


        # Convert the data into a DataFrame
        df = pd.DataFrame(data, columns=headers)


        # Save the DataFrame to a CSV file
        df.to_csv('euro_2021_stats.csv', index=False)


        print('Data has been successfully scraped and saved to euro_2021_stats.csv')
    else:
        print('Could not find the table with id "results20216760_overall".')


else:
    print(f'Failed to retrieve the webpage. Status code: {response.status_code}')






