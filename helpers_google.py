from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env-dev')

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Load credentials
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

# Parse the JSON string into a dictionary
credentials_info = json.loads(GOOGLE_SERVICE_ACCOUNT_FILE)
credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)

# Connect to Google Sheets
service = build('sheets', 'v4', credentials=credentials)

# Define your spreadsheet ID
SPREADSHEET_ID = '1S6OucgSjVmgWXWwGeBH31mxdtfkfH4u3omGQpLEWy-Y'  # Found in the URL of your spreadsheet
RANGE_NAME = "raw_data!A:G"  # Adjust as per your sheet structure


# Function to append data to Google Sheets
def append_to_sheet(data):
    body = {"values": [data]}
    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

# Function to read data from Google Sheets
def read_sheet():
    """
    Reads all data from the 'raw_data' sheet.

    Returns:
    - pd.DataFrame: A DataFrame containing all rows, with column names taken from the first row of the sheet.
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    values = result.get("values", [])
    
    if not values:
        return pd.DataFrame(columns=["Vendor", "Test Date", "Batch", "Expected Mass mg", "Mass mg", "Purity %", "Test Lab"])
    
    return pd.DataFrame(values[1:], columns=values[0])  # Exclude header row for data

def calculate_statistics(vendor_name):
    # Read data from Google Sheets
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    values = result.get("values", [])
    df = pd.DataFrame(values[1:], columns=values[0])

    # Process columns
    df['Test Date'] = pd.to_datetime(df['Test Date'])
    df['Expected Mass mg'] = pd.to_numeric(df['Expected Mass mg'], errors='coerce')
    df['Mass mg'] = pd.to_numeric(df['Mass mg'], errors='coerce')
    df['Purity %'] = pd.to_numeric(df['Purity %'], errors='coerce')

    # Filter for the Vendor in last 3 months
    three_months_ago = datetime.now() - pd.DateOffset(months=3)
    recent_data = df[
        (df['Test Date'] >= three_months_ago) &
        (df['Vendor'].str.lower() == vendor_name.lower())
    ]

    # Group by 'Expected Mass mg' and calculate stats for each group
    grouped_data = recent_data.groupby('Expected Mass mg')

    group_stats = {}
    for group, data in grouped_data:
        group_stats[group] = {
            "average_mass": data['Mass mg'].mean(),
            "average_purity": data['Purity %'].mean(),
            "std_mass": data['Mass mg'].std(),
            "std_purity": data['Purity %'].std()
        }

    return group_stats


if __name__=='__main__':
    vendor = 'VendorB'
    grouped_stats = calculate_statistics(vendor)

    # Initialize the message text
    message_text = f"📊 <b>{vendor.upper()} Analysis for the last 3 months:</b>\n\n"

    # Iterate through each group and append stats to the message
    for expected_mass, stats in grouped_stats.items():
        message_text += (
            f"🔹 <b>Expected Mass: {expected_mass} mg</b>\n"
            f"   • Avg Tested Mass: {stats['average_mass']:.2f} mg\n"
            f"   • Avg Tested Purity: {stats['average_purity']:.2f}%\n"
            f"   • Std Dev Mass: {stats['std_mass']:.2f} mg\n"
            f"   • Std Dev Purity: {stats['std_purity']:.2f}%\n\n"
        )
    print(message_text)