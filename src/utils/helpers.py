import re
from datetime import datetime

def wait_time_to_days(wait_time_str):
    """Convert wait time string to number of days."""
    if not wait_time_str:
        return 0
    match = re.match(r'(\d+)\s*days?', wait_time_str.lower())
    if match:
        return int(match.group(1))
    return 0

def wait_time_to_minutes(wait_time_str):
    """Convert wait time string to number of minutes."""
    if not wait_time_str:
        return 0
    match = re.match(r'(\d+)\s*minutes?', wait_time_str.lower())
    if match:
        return int(match.group(1))
    return 0

def generate_proposal_message(user, patient, slot):
    """Generate proposal message using user's template."""
    template = user.proposal_message_template or 'Hi {patient_name}, we have an opening with {provider_name} on {date} at {time}. Would you like to take this slot? Please call us at {clinic_phone} to confirm.'
    
    # Format date for display
    slot_date = datetime.fromisoformat(slot['date']).strftime('%A, %B %d')
    
    # Format time for display (convert 24-hour to 12-hour)
    time_obj = datetime.strptime(slot['start_time'], '%H:%M')
    display_time = time_obj.strftime('%I:%M %p')
    
    return template.format(
        patient_name=patient['name'],
        provider_name=slot['provider'],
        date=slot_date,
        time=display_time,
        clinic_phone=user.clinic_name or 'our office',
        appointment_type=patient['appointment_type'],
        duration=patient['duration']
    ) 