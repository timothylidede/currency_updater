import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import numpy as np
import json
import os

def col_num_to_letters(col_num):
    letters = ''
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters

def setup_credentials_and_spreadsheet():
    print("Setting up credentials and spreadsheet...")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_json = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("Copy of Currency Manipulation Feb 19")
    return client, spreadsheet

def fetch_currency_data(currency_code, transaction_type):
    print(f"Fetching {transaction_type} data for currency: {currency_code}")
    url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
    payload = {
        "page": 1,
        "rows": 5,
        "asset": "USDT",
        "tradeType": transaction_type.upper(),
        "fiat": currency_code,
        "merchantCheck": False
    }
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if data and 'data' in data and len(data['data']) > 0:
        prices = [float(adv['adv']['price']) for adv in data['data']]
        print(f"Fetched data for {currency_code} - {transaction_type}: {prices}")
        return np.median(prices)
    else:
        print("No data available or the response structure is unexpected.")
        return None

def find_first_empty_column(worksheet):
    all_values = worksheet.get_all_values()
    if not all_values:
        return 1
    for col_index in range(1, len(all_values[0]) + 2):  # +2 to go beyond the last filled column
        col_values = [row[col_index - 1] if col_index <= len(row) else '' for row in all_values]
        if all(value.strip() == '' for value in col_values):
            return col_index
    return len(all_values[0]) + 1  # Next column if all are somehow filled

def main():
    client, spreadsheet = setup_credentials_and_spreadsheet()

    currencies = ["ETB", "EGP", "MZN", "TZS", "NGN", "RWF", "ZAR", "ZMW", "GHS", "UGX", "KES"]
    today_date = datetime.now().strftime('%Y-%m-%d')

    for sheet_name, transaction_type in [("BUY", "buy"), ("SELL", "sell")]:
        worksheet = spreadsheet.worksheet(sheet_name)
        first_empty_col = find_first_empty_column(worksheet)
        col_letter = col_num_to_letters(first_empty_col)

        # Update the date at the top of the first empty column
        worksheet.update_cell(1, first_empty_col, today_date)

        for currency in currencies:
            print(f"Processing {sheet_name} sheet for {currency}...")
            median_price = fetch_currency_data(currency, transaction_type)
            
            if median_price is not None:
                # Assuming currency codes are in the first column
                try:
                    currency_cell = worksheet.find(currency)
                    worksheet.update_cell(currency_cell.row, first_empty_col, median_price)
                    print(f"Updated {currency} with median price {median_price}.")
                except gspread.exceptions.CellNotFound:
                    print(f"Currency {currency} not found in the {sheet_name} sheet.")
            else:
                print(f"No valid data to update for {currency}.")
    
    print("Data retrieval and update process complete.")

if __name__ == "__main__":
    main()

def scheduled_job(request):
    """
    This function is the entry point for Cloud Function.
    It will be triggered by Cloud Scheduler.
    """
    main()  # Call your main function

    # Must return a valid HTTP response
    return "Completed", 200