import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
from pyvirtualdisplay import Display
import time

def initialize_headless_display():
    """Initialize headless display."""
    display = Display(visible=0, size=(800, 600))
    display.start()

def setup_chromedriver():
    """Set up Chromedriver for Selenium."""
    chromedriver_autoinstaller.install()
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,1200")
    return webdriver.Chrome(options=options)

def setup_credentials_and_spreadsheet():
    """Set up credentials and spreadsheet access."""
    print("Setting up credentials and spreadsheet...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Copy of Currency Manipulation Feb 19")
    return spreadsheet

def fetch_currency_data(driver, currency_code, transaction_type):
    """Fetch currency data using Selenium."""
    try:
        print(f"Fetching {transaction_type} data for currency: {currency_code}")
        driver.get('https://p2p.binance.com/en')
        currency_button = driver.find_element(By.CSS_SELECTOR, "svg.css-1nlwvj5")
        currency_button.click()
        time.sleep(0.5)
        currency_input = driver.find_element(By.CLASS_NAME, "css-jl5e70")
        currency_input.send_keys(currency_code)
        time.sleep(0.5)
        li_element = driver.find_element(By.ID, currency_code)
        li_element.click()
        time.sleep(1)
        transaction_button = driver.find_element(By.XPATH, f"//*[text()='{transaction_type.capitalize()}']")
        transaction_button.click()
        time.sleep(3)
        div_elements = driver.find_elements(By.CLASS_NAME, "css-onyc9z")
        extracted_data = [div.text for div in div_elements[:5]]
        print(extracted_data)
        data_floats = [float(i.replace(',', '')) for i in extracted_data if i.replace('.', '', 1).replace(',', '').isdigit()]
        return np.median(data_floats) if data_floats else None
    except Exception as e:
        print(f"Error fetching data for {currency_code}: {e}")
        return None

def col_num_to_letters(col_num):
    """Convert column number to spreadsheet letters."""
    letters = ''
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters

def update_spreadsheet(spreadsheet, currencies, transaction_types):
    """Update spreadsheet with fetched currency data."""
    today_date = datetime.now().strftime('%Y-%m-%d')
    driver = setup_chromedriver()
    
    for sheet_name, transaction_type in transaction_types:
        worksheet = spreadsheet.worksheet(sheet_name)
        first_empty_col = find_first_empty_column(worksheet) + 1  # Adjust for 0-index
        col_letter = col_num_to_letters(first_empty_col)
        
        worksheet.update_cell(1, first_empty_col, today_date)
        
        for currency in currencies:
            print(f"Processing {sheet_name} sheet for {currency}...")
            median_price = fetch_currency_data(driver, currency, transaction_type)
            
            if median_price is not None:
                try:
                    currency_cell = worksheet.find(currency)
                    worksheet.update_cell(currency_cell.row, first_empty_col, median_price)
                    print(f"Updated {currency} with median price {median_price}.")
                except gspread.exceptions.CellNotFound:
                    print(f"Currency {currency} not found in the {sheet_name} sheet.")
            else:
                print(f"No valid data to update for {currency}.")
    
    driver.quit()
    print("Data retrieval and update process complete.")

def find_first_empty_column(worksheet):
    """Find the first empty column in a worksheet."""
    all_values = worksheet.get_all_values()
    if not all_values:
        return 0
    return next((i for i, column in enumerate(zip(*all_values)) if all(cell == '' for cell in column)), len(all_values[0]))

def main():
    initialize_headless_display()
    spreadsheet = setup_credentials_and_spreadsheet()
    currencies = ["ETB", "EGP", "MZN", "TZS", "NGN", "RWF", "ZAR", "ZMW", "GHS", "UGX", "KES"]
    transaction_types = [("BUY", "buy"), ("SELL", "sell")]
    update_spreadsheet(spreadsheet, currencies, transaction_types)

if __name__ == "__main__":
    main()
