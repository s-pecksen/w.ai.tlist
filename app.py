from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import keyring
import os
import pandas as pd
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Create Base before any classes that need to inherit from it
Base = declarative_base()

# In-memory storage for the patient waitlist
waitlist = []

# Database setup with encryption
class SecureDatabase:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.key)
        self.engine = create_engine('sqlite:///clinic_data.db')
        
    def _get_or_create_key(self):
        key = keyring.get_password("clinic_scheduler", "db_key")
        if not key:
            key = Fernet.generate_key()
            keyring.set_password("clinic_scheduler", "db_key", key)
        return key
    
    def encrypt_data(self, data):
        return self.cipher_suite.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data):
        return self.cipher_suite.decrypt(encrypted_data).decode()

# Patient data model
class Patient(Base):
    __tablename__ = 'patients'
    
    id = Column(String, primary_key=True)
    encrypted_data = Column(String)
    created_at = Column(DateTime)

# Add this helper function to convert wait time to minutes
def wait_time_to_minutes(wait_time_str):
    total_minutes = 0
    if 'days' in wait_time_str:
        days = int(wait_time_str.split('days')[0].strip())
        total_minutes += days * 24 * 60
        remaining = wait_time_str.split(',')[1].strip()
    else:
        remaining = wait_time_str
        
    if 'hours' in remaining:
        hours = int(remaining.split('hours')[0].strip())
        total_minutes += hours * 60
        if ',' in remaining:
            remaining = remaining.split(',')[1].strip()
    
    if 'minutes' in remaining:
        minutes = int(remaining.split('minutes')[0].strip())
        total_minutes += minutes
        
    return total_minutes

@app.route('/')
def index():
    # Update wait times first
    update_wait_times()
    
    # Sort waitlist: emergencies first, then by wait time (longest first), then scheduled last
    sorted_waitlist = sorted(
        waitlist,
        key=lambda x: (
            x['status'] == 'scheduled',  # Scheduled patients last
            x['appointment_type'] != 'emergency',  # Emergencies first
            -wait_time_to_minutes(x['wait_time'])  # Sort by wait time (negative for descending order)
        )
    )
    return render_template('index.html', waitlist=sorted_waitlist)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    reason = request.form.get('reason')
    urgency = request.form.get('urgency')
    appointment_type = request.form.get('appointment_type')
    duration = request.form.get('duration')
    hygienist = request.form.get('hygienist')
    needs_dentist = request.form.get('needs_dentist') == 'yes'
    
    if name and phone:  # Basic validation
        patient = {
            'id': len(waitlist) + 1,
            'name': name,
            'phone': phone,
            'email': email,
            'reason': reason,
            'urgency': urgency,
            'appointment_type': appointment_type,
            'duration': duration,
            'hygienist': hygienist,
            'needs_dentist': needs_dentist,
            'status': 'waiting',
            'timestamp': datetime.now(),  # Add timestamp
            'wait_time': '0 minutes'  # Initialize wait time
        }
        waitlist.append(patient)
    
    return redirect(url_for('index'))

# Function to update wait times
def update_wait_times():
    now = datetime.now()
    for patient in waitlist:
        if patient['status'] == 'waiting':
            delta = now - patient['timestamp']
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                patient['wait_time'] = f"{days} days, {hours} hours"
            elif hours > 0:
                patient['wait_time'] = f"{hours} hours, {minutes} minutes"
            else:
                patient['wait_time'] = f"{minutes} minutes"

# Update the existing routes to include wait time updates
@app.route('/schedule_patient/<int:patient_id>', methods=['POST'])
def schedule_patient(patient_id):
    update_wait_times()  # Update wait times before scheduling
    for patient in waitlist:
        if patient['id'] == patient_id:
            patient['status'] = 'scheduled'
            break
    return redirect(url_for('index'))

@app.route('/remove_patient/<int:patient_id>', methods=['POST'])
def remove_patient(patient_id):
    global waitlist
    waitlist = [p for p in waitlist if p['id'] != patient_id]
    return redirect(url_for('index'))

# Add these helper functions
def validate_appointment_type(value):
    valid_types = ['hygiene', 'recall', 'resto', 'spec exam', 'emerg exam', 'custom']
    return value.lower() if value.lower() in valid_types else 'hygiene'

def validate_duration(value):
    valid_durations = ['30', '45', '60', '90', '120']
    return value if str(value) in valid_durations else '30'

def validate_hygienist(value):
    valid_hygienists = ['no preference', '', 'sarah', 'michael', 'jessica', 'david']
    # Convert empty string or None to 'no preference'
    if not value or value.lower() == 'no preference':
        return 'no preference'
    return value.lower() if value.lower() in valid_hygienists else 'no preference'

def validate_urgency(value):
    valid_urgency = ['low', 'medium', 'high']
    return value.lower() if value.lower() in valid_urgency else 'medium'

def validate_needs_dentist(value):
    if isinstance(value, str):
        return value.lower() in ['yes', 'true', '1', 'y']
    return bool(value)

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        return redirect(url_for('index'))
    
    file = request.files['csv_file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file and file.filename.endswith('.csv'):
        try:
            # Read CSV file
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_data = pd.read_csv(stream)
            
            # Validate required columns
            required_columns = ['name', 'phone']
            if not all(col in csv_data.columns for col in required_columns):
                flash('CSV must contain at least name and phone columns')
                return redirect(url_for('index'))

            # Process each row
            for _, row in csv_data.iterrows():
                patient = {
                    'id': len(waitlist) + 1,
                    'name': row.get('name', ''),
                    'phone': row.get('phone', ''),
                    'email': row.get('email', ''),
                    'appointment_type': validate_appointment_type(row.get('appointment_type', 'consultation')),
                    'duration': validate_duration(row.get('duration', '30')),
                    'hygienist': validate_hygienist(row.get('hygienist', '')),
                    'needs_dentist': validate_needs_dentist(row.get('needs_dentist', False)),
                    'reason': row.get('reason', ''),
                    'urgency': validate_urgency(row.get('urgency', 'medium')),
                    'status': 'waiting',
                    'timestamp': datetime.now(),
                    'wait_time': '0 minutes'
                }
                waitlist.append(patient)

        except Exception as e:
            print(f"Error processing CSV: {str(e)}")
            flash('Error processing CSV file')
            
    return redirect(url_for('index'))

def load_initial_csv():
    try:
        csv_path = 'Tests/Sample CSV - Sheet1.csv'
        df = pd.read_csv(csv_path)
        
        for _, row in df.iterrows():
            # Parse the datetime from the CSV
            try:
                # Try multiple date formats to handle different possibilities
                for date_format in [
                    '%m/%d/%y %I:%M %p',    # 2/25/25 1:00 PM
                    '%m/%d/%Y %H:%M:%S %p'  # 2/25/2025 16:00:00 PM
                ]:
                    try:
                        entry_time = datetime.strptime(row['Date Time Entered'], date_format)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Error parsing date for {row['name']}: {str(e)}")
                entry_time = datetime.now()  # Fallback to current time if parsing fails
            
            patient = {
                'id': len(waitlist) + 1,
                'name': row.get('name', ''),
                'phone': row.get('phone', ''),
                'email': row.get('email', ''),
                'appointment_type': validate_appointment_type(row.get('appointment_type', 'consultation')),
                'duration': validate_duration(row.get('duration', '30')),
                'hygienist': validate_hygienist(row.get('hygienist', '')),
                'needs_dentist': validate_needs_dentist(row.get('needs_dentist', False)),
                'reason': row.get('reason', ''),
                'urgency': validate_urgency(row.get('urgency', 'medium')),
                'status': 'waiting',
                'timestamp': entry_time,  # Use the parsed datetime
                'wait_time': '0 minutes'  # This will be updated by update_wait_times()
            }
            waitlist.append(patient)
            
        # Update wait times for all loaded patients
        update_wait_times()
        print(f"Successfully loaded {len(df)} patients from CSV file")
    except Exception as e:
        print(f"Error loading initial CSV file: {str(e)}")

if __name__ == '__main__':
    # Load initial data before starting the server
    load_initial_csv()
    app.run(debug=True, host="0.0.0.0", port=7776)
