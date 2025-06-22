---
title: W.AI.TLIST - Dental Clinic Management
emoji: 🦷
colorFrom: blue
colorTo: teal
sdk: docker
app_port: 7860
pinned: false
---

# W.AI.TLIST - Dental Appointment Optimization

An intelligent dental clinic management system that helps front desk staff maximize appointment utilization by automatically matching patients with cancellation slots.

## Purpose

W.AI.TLIST transforms how dental offices handle appointment cancellations by:

- **Intelligent Patient Matching**: Automatically identifies and matches suitable patients with available appointment slots
- **Revenue Recovery**: Helps dental offices recover thousands in revenue from what would otherwise be empty appointment slots
- **Staff Efficiency**: Streamlines the cancellation filling process, saving front desk staff significant time and effort
- **Optimized Scheduling**: Ensures maximum appointment book utilization through smart patient-slot matching algorithms

## Target Users

Designed specifically for dental office front desk staff and practice managers who need to:
- Quickly fill last-minute cancellations
- Maximize daily appointment schedules
- Reduce administrative burden of manual patient calling
- Increase practice revenue through better slot utilization

## Architecture

- **Frontend**: Flask with Jinja2 templating
- **Backend**: Python with Flask
- **Database**: Supabase (PostgreSQL)
- **Session Management**: Flask-Session
- **Authentication**: Flask-Login

## Features

- User authentication and session management
- Supabase database integration
- Secure encrypted sessions
- SQLAlchemy ORM integration

## Configuration

This application requires the following environment variables to be set in your Hugging Face Space secrets:

- `FLASK_APP_ENCRYPTION_KEY`: Encryption key for Flask application data
- `FLASK_SESSION_SECRET_KEY`: Secret key for Flask session management
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public API key

### Database Setup

This application uses Supabase as the backend database. The app connects to Supabase using the Python client library and handles:

- User data storage and retrieval
- Session persistence
- Real-time database operations

Make sure your Supabase project is configured with the appropriate tables and RLS (Row Level Security) policies for your application.

## Local Development

To run locally:

1. Create a `.env` file with the required environment variables
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python app.py
   ```

The app will be available at `http://localhost:7860`

## Deployment

This app is configured to run on Hugging Face Spaces using Docker. The Dockerfile handles all system dependencies and Python package installations automatically.