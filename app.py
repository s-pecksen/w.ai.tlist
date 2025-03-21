from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# In-memory storage for the patient waitlist
waitlist = []

@app.route('/')
def index():
    return render_template('index.html', waitlist=waitlist)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    reason = request.form.get('reason')
    urgency = request.form.get('urgency')
    
    if name and phone:  # Basic validation
        patient = {
            'id': len(waitlist) + 1,
            'name': name,
            'phone': phone,
            'email': email,
            'reason': reason,
            'urgency': urgency,
            'status': 'waiting'
        }
        waitlist.append(patient)
    
    return redirect(url_for('index'))

@app.route('/schedule_patient/<int:patient_id>', methods=['POST'])
def schedule_patient(patient_id):
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
