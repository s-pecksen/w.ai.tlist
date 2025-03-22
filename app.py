from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# In-memory storage for the patient waitlist
waitlist = []

@app.route('/')
def index():
    # Sort waitlist: emergencies first, then by timestamp
    sorted_waitlist = sorted(
        waitlist,
        key=lambda x: (
            x['status'] == 'scheduled',  # Scheduled patients last
            x['appointment_type'] != 'emergency',  # Emergencies first
            x['timestamp']  # Then by timestamp
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

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=7776)
