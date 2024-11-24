from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import pandas as pd

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Load credentials
SERVICE_ACCOUNT_FILE = 'tirzhelpbot-56fa11612518.json'
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

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


