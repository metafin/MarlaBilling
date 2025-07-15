# Marla's Billing Tool

A Flask web application to help match therapy appointments from Google Calendar with Venmo payments.

## Features

- Download therapy appointments from Google Calendar (filters by keywords and Zoom links)
- Import Venmo transaction history from CSV files
- Side-by-side view of appointments and transactions
- Mark items as "cleared" when matched
- Toggle to show/hide cleared items
- Duplicate protection for both appointments and transactions

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google Calendar API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click on it and press "Enable"
4. Configure OAuth consent screen (required first time):
   - Go to "APIs & Services" > "OAuth consent screen"
   - Choose "External" (this is safe - it does NOT make your calendar public)
     - Note: "External" just means you're not using Google Workspace. Your app stays in testing mode, accessible only to emails you explicitly add
   - Fill in required fields:
     - App name: "Marla's Billing Tool" (or any name)
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue" through the Scopes screen
   - On the "Test users" screen:
     - Click "+ ADD USERS" button
     - Enter the exact email address you'll use to log in (e.g., brianjnorton@gmail.com)
     - Add Marla's email if different from yours
     - Click "SAVE"
     - IMPORTANT: Without this step, you'll get "Error 403: access_denied" when trying to connect
5. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop application"
   - Name it (e.g., "Marla Billing Desktop")
   - Click "Create"
   - Download the JSON file
   - Rename it to `credentials.json` and place it in the project root directory

### 3. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:8000`

## Usage

### First Time Setup

1. **Google Calendar Authentication**: When you first click "Download Calendar", you'll be prompted to authenticate with Google in your browser
2. **Set Start Date**: Choose a date to start downloading appointments from
3. **Download Appointments**: Click "Download Calendar" to fetch therapy sessions from Google Calendar

### Importing Venmo Data

1. Log into your Venmo account
2. Go to Settings > Privacy > Export Data
3. Download your transaction history as a CSV file
4. In the app, click "Import Venmo CSV" and upload the file

### Matching Process

1. **Left Panel**: Shows calendar appointments with checkboxes
2. **Right Panel**: Shows Venmo transactions with checkboxes
3. **Manual Matching**: Look for appointments without corresponding payments
4. **Mark as Cleared**: Check off items when you've verified they match
5. **Toggle Cleared**: Use the "Show/Hide Cleared" buttons to focus on unmatched items

## How It Works

### Therapy Session Detection

The app identifies therapy sessions by looking for:
- Keywords: "therapy", "session", "appointment", "zoom", "meet", "client"
- Zoom links in the event description
- Other configurable patterns

### Data Storage

- Appointments are stored in `appointments.json`
- Transactions are stored in `transactions.json`
- Both files are automatically created and updated
- Duplicate protection prevents re-importing the same data

### File Structure

```
MarlaBilling/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Main UI template
├── requirements.txt      # Python dependencies
├── credentials.json      # Google API credentials (you create this)
├── token.pickle         # Google auth token (auto-generated)
├── appointments.json    # Stored appointments (auto-generated)
├── transactions.json    # Stored transactions (auto-generated)
└── README.md           # This file
```

## Security Notes

- The `credentials.json` file contains sensitive information - don't commit it to version control
- The `token.pickle` file contains your authentication token - also keep it secure
- All data is stored locally on your machine

## Troubleshooting

### Google Calendar API Issues

- **"Error 403: access_denied"**: You need to add your email as a test user in the OAuth consent screen
  - Go to Google Cloud Console > APIs & Services > OAuth consent screen
  - Find "Test users" section and click "+ ADD USERS"
  - Add the exact email you're using to log in
- Make sure you've enabled the Google Calendar API in the Google Cloud Console
- Check that your `credentials.json` file is in the correct location
- If you get authentication errors, delete `token.pickle` and re-authenticate

### Venmo CSV Import Issues

- Make sure the CSV file is from Venmo's official export feature
- Check that the CSV has the expected columns (ID, Datetime, Type, Status, Note, From, To, Amount)
- Large CSV files may take a moment to process

### General Issues

- Check the browser console for JavaScript errors
- Look at the Flask debug output in the terminal
- Make sure all dependencies are installed correctly