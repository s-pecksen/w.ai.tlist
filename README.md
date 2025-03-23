# w.AI.tlist

w.AI.tlist is a smart waitlist management system for clinics that automatically matches patients on waitlists with newly available appointments.

## What It Does

w.AI.tlist helps clinic managers save time by:
- Managing patient waitlists automatically
- Finding the best patient match when appointments open up
- Considering appointment types, clinician preferences, and urgency
- Streamlining the rescheduling process when cancellations occur

## How It Works

When an appointment becomes available, w.AI.tlist:
1. Analyzes the appointment type, duration, and assigned clinician
2. Searches the waitlist for appropriate patient matches
3. Considers patient preferences, appointment urgency, and waitlist position
4. Presents the best-matched patient profile to the clinic manager

## Technology

Built with:
- Python 
- Flask web framework
- SQLite database (for development)
- PostgreSQL (for production)

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation
1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the development server: `python app.py`
6. Open your browser and go to `http://127.0.0.1:5000`

## Project Structure
```
waitlist/
  ├── __init__.py      # Flask application factory
  ├── routes.py        # Application routes and API endpoints
  ├── models/          # Database models
  ├── static/          # CSS, JavaScript, and other static files
  │   ├── css/         
  │   └── js/          
  └── templates/       # HTML templates
app.py                 # Application entry point
requirements.txt       # Python dependencies
```

## Roadmap

Future enhancements:
- Email/SMS notifications to patients
- Calendar integration with popular practice management systems
- Machine learning to optimize matching algorithms
- Mobile app for on-the-go management

## License

[MIT License](LICENSE)

