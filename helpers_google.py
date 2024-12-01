from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
RANGE_NAME = "raw_data!A:J"  # Adjust as per your sheet structure
SPREADSHEET_COLS = ["Vendor", "Test Date", "Batch", "Expected Mass mg", "Mass mg", "Purity %", "TFA", "Test Lab", "File Name"]


# Function to append data to Google Sheets
def append_to_sheet(data):
    global service
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
    global service
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()
    values = result.get("values", [])
    
    if not values:
        return pd.DataFrame(columns=SPREADSHEET_COLS)
    
    return pd.DataFrame(values[1:], columns=values[0])  # Exclude header row for data

def calculate_statistics(vendor_name, peptide):
    global service
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
        (df['Vendor'].str.lower() == vendor_name.lower()) &
        (df['Peptide'].str.lower()== peptide.lower())
    ]

    # Group by 'Expected Mass mg' and calculate stats for each group
    grouped_data = recent_data.groupby('Expected Mass mg')

    group_stats = {}
    for group, data in grouped_data:        
        # Calculate percentage differences
        mass_diff_percent = (data['Mass mg'].std() / group) * 100

        group_stats[group] = {
            "test_count": data['Vendor'].count(),
            "average_mass": data['Mass mg'].mean(),
            "average_purity": data['Purity %'].mean(),
            "std_mass": data['Mass mg'].std(),
            "std_purity": data['Purity %'].std(),
            "mass_diff_percent": mass_diff_percent
        }

    return group_stats
