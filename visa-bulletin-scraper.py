import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime
import hashlib

def fetch_or_cache(url, folder="cache"):
    """
    Fetch data from the URL or load from cache if it already exists.

    Args:
        url (str): The URL to fetch data from.
        folder (str): The folder to save cached data.

    Returns:
        str: The content of the URL (from cache or web).
    """
    # Ensure the cache folder exists
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Create a unique filename for the URL
    url_hash = hashlib.md5(url.encode()).hexdigest()
    file_path = os.path.join(folder, f"{url_hash}.html")

    # Check if the file exists in the cache
    if os.path.exists(file_path):
        print(f"Loading cached data for {url}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    # Otherwise, fetch the data and save it to the cache
    print(f"Fetching data from {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch {url}: {response.status_code}")
        return None
    content = response.text

    # Save the content to the file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content

# def fetch_url_data(url):
#     response = requests.get(url)
#     if response.status_code != 200:
#         print(f"Failed to fetch {url}")
#         return None
#     return response

# Function to fetch table data from the webpage
def fetch_table_data(content, table_identifier):
    soup = BeautifulSoup(content, 'html.parser')
    tables = soup.find_all('table')
    
    for table in tables:
        # Collect headers from the first row(s) of the table
        headers = []
        for header_row in table.find_all('tr'):
            row_headers = [cell.get_text(strip=True).replace('\n', ' ') for cell in header_row.find_all(['th', 'td'])]
            if row_headers:
                headers.extend(row_headers)
        
        # Check if table_identifier is in the flattened headers
        headers_text = " ".join(headers).strip()
        if table_identifier.lower() in headers_text.lower():  # Match case-insensitively
            rows = table.find_all('tr')
            data = []
            for row in rows[1:]:  # Skip header row(s)
                cells = row.find_all(['td', 'th'])
                data.append([cell.get_text(strip=True).replace('\n', ' ') for cell in cells])
            df = pd.DataFrame(data, columns=headers[:len(data[0])])
            return df  # Return the DataFrame
    
    print(f"Table with identifier '{table_identifier}' not found.")
    return None

# Function to parse date and calculate lag
def calculate_lag(df, column, base_date):
    if column not in df.columns:
        print(f"Column '{column}' not found in table for {base_date}")
        print(f"This was a good year for {column}")
        column = "All Chargeability Areas Except Those Listed"
        if column not in df.columns:
            print(f"Something is really wrong because even {column} isn't present in Table")
            return None
        
    
    lags = {}
    for index, value in df[column].items():
        print(f"Index: {index}, value: {value}")
        if value == "C":  # 'Current' means zero backlog
            lags[df.iloc[index, 0]] = 0
        else:
            try:
                backlog_date = datetime.strptime(value, "%d%b%y")  # Parse date like '01JAN20'
                lag = (base_date - backlog_date).days
                lags[df.iloc[index, 0]] = lag
            except ValueError:
                lags[df.iloc[index, 0]] = None  # Handle invalid/missing data gracefully
    return lags

# Plotting function
def plot_lag(data, months, title):
    plt.figure(figsize=(12, 6))
    for row, lags in data.items():
        plt.plot(months, lags, label=row)
    plt.title(title)
    plt.xlabel("Month")
    plt.ylabel("Lag (Days)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    base_url = "https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin"  # Base URL
    years = range(2002, 2024)  # Years to process
    months = ["january", "february", "march", "april", "may", "june",
              "july", "august", "september", "october", "november", "december"]

    table_identifier = "Employment-based"  # Header to identify the table
    column_of_interest = "INDIA" # input("Enter the column of interest (or press Enter to fetch full table): ")
    lag_data = {}
    month_labels = []

    for year in years:
        for month in months:
            if month in ["october", "november", "december"]:
                url = f"{base_url}/{year+1}/visa-bulletin-for-{month}-{year}.html"
            else:
                url = f"{base_url}/{year}/visa-bulletin-for-{month}-{year}.html"
            # fetch data from url
            response = fetch_or_cache(url)

            if response is None:
                print(f"Let's try removing the 'for' in the url")
                if month in ["october", "november", "december"]:
                    url = f"{base_url}/{year+1}/visa-bulletin-{month}-{year}.html"
                else:
                    url = f"{base_url}/{year}/visa-bulletin-{month}-{year}.html" 
                response = fetch_or_cache(url)

            if response is None:
                print(f"Let's try swapping the years!")
                if month in ["october", "november", "december"]:
                    url = f"{base_url}/{year}/visa-bulletin-for-{month}-{year}.html"
                else:
                    url = f"{base_url}/{year+1}/visa-bulletin-for-{month}-{year}.html"
                response = fetch_or_cache(url)
                            
            if response is None:
                print("unable to fetch data from {url}; skipping")
                continue

            table = fetch_table_data(response, table_identifier)
            
            if table is not None:  # Ensure table exists
                base_date = datetime.strptime(f"01{month[:3]}{year}", "%d%b%Y")
                lags = calculate_lag(table, column_of_interest, base_date)
                if lags:
                    # Add data to lag_data
                    for row, lag in lags.items():
                        if row not in lag_data:
                            lag_data[row] = [None] * len(month_labels)  # Fill missing months with None
                        lag_data[row].append(lag)
                    # Add placeholders for rows not in lags
                    for row in lag_data:
                        if row not in lags:
                            lag_data[row].append(None)
                    month_labels.append(f"{month[:3]} {year}")  # Append valid month-year
            else:
                # If no table, append None for all rows
                for row in lag_data:
                    lag_data[row].append(None)
                print(f"No table found for {month} {year}. Skipping.")

    # Ensure all rows have the same length as month_labels
    for row in lag_data:
        if len(lag_data[row]) < len(month_labels):
            lag_data[row].extend([None] * (len(month_labels) - len(lag_data[row])))

    # Validate data and plot
    if lag_data and all(len(lags) == len(month_labels) for lags in lag_data.values()):
        plot_lag(lag_data, month_labels, f"Lag Trends for '{column_of_interest}' Column")
    else:
        print("Error: Data length mismatch.")
        print(f"Month labels length: {len(month_labels)}")
        for row, lags in lag_data.items():
            print(f"Row: {row}, Lag data length: {len(lags)}")

