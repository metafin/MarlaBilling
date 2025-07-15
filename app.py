from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import os
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'marla-billing-secret-key'

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

# Data files
APPOINTMENTS_FILE = 'appointments.json'
TRANSACTIONS_FILE = 'transactions.json'

def get_calendar_service():
    """Get Google Calendar service instance"""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

def load_data(filename):
    """Load data from JSON file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def save_data(filename, data):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def is_therapy_session(event):
    """Check if event looks like a therapy session"""
    keywords = ['therapy', 'session', 'appointment', 'zoom', 'meet', 'client']
    description = event.get('description', '').lower()
    summary = event.get('summary', '').lower()
    
    # Check for keywords or zoom links
    for keyword in keywords:
        if keyword in description or keyword in summary:
            return True
    
    # Check for zoom links
    if 'zoom.us' in description or 'zoom.us' in summary:
        return True
    
    return False

@app.route('/')
def index():
    """Main page with dual windows"""
    appointments = load_data(APPOINTMENTS_FILE)
    transactions = load_data(TRANSACTIONS_FILE)
    return render_template('index.html', appointments=appointments, transactions=transactions)

@app.route('/download_appointments', methods=['POST'])
def download_appointments():
    """Download appointments from Google Calendar"""
    try:
        start_date = request.form.get('start_date')
        if not start_date:
            flash('Please provide a start date', 'error')
            return redirect(url_for('index'))
        
        service = get_calendar_service()
        
        # Convert start date to datetime
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.now()
        
        # Get events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_datetime.isoformat() + 'Z',
            timeMax=end_datetime.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Filter for therapy sessions
        therapy_events = []
        for event in events:
            if is_therapy_session(event):
                # Get attendees excluding the organizer (Marla)
                attendees = []
                if 'attendees' in event:
                    organizer_email = event.get('organizer', {}).get('email', '').lower()
                    for attendee in event['attendees']:
                        attendee_email = attendee.get('email', '').lower()
                        # Exclude organizer and declined attendees
                        if attendee_email != organizer_email and attendee.get('responseStatus') != 'declined':
                            name = attendee.get('displayName', attendee.get('email', ''))
                            attendees.append(name)
                
                therapy_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'attendees': attendees,
                    'cleared': False
                })
        
        # Load existing appointments and merge
        existing_appointments = load_data(APPOINTMENTS_FILE)
        existing_ids = {apt['id'] for apt in existing_appointments}
        
        # Add only new appointments
        new_appointments = [apt for apt in therapy_events if apt['id'] not in existing_ids]
        
        # Update existing appointments with attendee info if missing
        for existing_apt in existing_appointments:
            if 'attendees' not in existing_apt:
                # Find the corresponding event in therapy_events
                for new_apt in therapy_events:
                    if new_apt['id'] == existing_apt['id']:
                        existing_apt['attendees'] = new_apt['attendees']
                        break
                else:
                    # If not found in current download, set empty attendees
                    existing_apt['attendees'] = []
        
        all_appointments = existing_appointments + new_appointments
        
        # Save updated appointments
        save_data(APPOINTMENTS_FILE, all_appointments)
        
        flash(f'Downloaded {len(new_appointments)} new appointments', 'success')
        
    except Exception as e:
        flash(f'Error downloading appointments: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/import_venmo', methods=['POST'])
def import_venmo():
    """Import Venmo CSV data"""
    try:
        if 'venmo_csv' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(url_for('index'))
        
        file = request.files['venmo_csv']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('index'))
        
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        csv_lines = csv_content.splitlines()
        
        # Find the header row (contains "ID,Datetime,Type")
        header_index = -1
        for i, line in enumerate(csv_lines):
            if 'ID' in line and 'Datetime' in line and 'Type' in line and 'Status' in line:
                header_index = i
                break
        
        if header_index == -1:
            flash('Invalid CSV format - could not find header row', 'error')
            return redirect(url_for('index'))
        
        # Create a new CSV content starting from the header row
        cleaned_csv = '\n'.join(csv_lines[header_index:])
        csv_reader = csv.DictReader(StringIO(cleaned_csv))
        
        # Process transactions (only complete ones)
        transactions = []
        for row in csv_reader:
            # Skip empty rows or rows without required fields
            if not row.get('ID') or not row.get('Datetime'):
                continue
                
            # Only import complete transactions
            if row.get('Status', '').lower() == 'complete':
                transactions.append({
                    'id': row.get('ID', ''),
                    'datetime': row.get('Datetime', ''),
                    'type': row.get('Type', ''),
                    'status': row.get('Status', ''),
                    'note': row.get('Note', ''),
                    'from': row.get('From', ''),
                    'to': row.get('To', ''),
                    'amount': row.get('Amount (total)', ''),
                    'cleared': False
                })
        
        # Load existing transactions and merge
        existing_transactions = load_data(TRANSACTIONS_FILE)
        existing_ids = {txn['id'] for txn in existing_transactions}
        
        # Add only new transactions
        new_transactions = [txn for txn in transactions if txn['id'] not in existing_ids]
        all_transactions = existing_transactions + new_transactions
        
        # Save updated transactions
        save_data(TRANSACTIONS_FILE, all_transactions)
        
        flash(f'Imported {len(new_transactions)} new transactions', 'success')
        
    except Exception as e:
        flash(f'Error importing Venmo CSV: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/toggle_cleared', methods=['POST'])
def toggle_cleared():
    """Toggle cleared status for an item"""
    try:
        item_type = request.json.get('type')
        item_id = request.json.get('id')
        
        if item_type == 'appointment':
            appointments = load_data(APPOINTMENTS_FILE)
            for apt in appointments:
                if apt['id'] == item_id:
                    apt['cleared'] = not apt['cleared']
                    break
            save_data(APPOINTMENTS_FILE, appointments)
        
        elif item_type == 'transaction':
            transactions = load_data(TRANSACTIONS_FILE)
            for txn in transactions:
                if txn['id'] == item_id:
                    txn['cleared'] = not txn['cleared']
                    break
            save_data(TRANSACTIONS_FILE, transactions)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)