---
title: W.AI.TLIST
emoji: 📃
colorFrom: blue
colorTo: indigo
sdk: docker
sdk_version: "28.1.1"
app_file: app.py
pinned: false
---

# Waitlist Management Application

A comprehensive waitlist management system for healthcare providers, built with FastAPI backend and Next.js frontend.

## Features

- **Patient Waitlist Management**: Add, view, update, and remove patients from the waitlist
- **Provider Management**: Manage healthcare provider information
- **Appointment Slot Management**: Track cancelled appointments and open slots
- **Smart Matching**: Automatically match patients to available slots based on preferences
- **User Authentication**: Secure JWT-based authentication system
- **Modern UI**: Responsive React-based frontend with Tailwind CSS
- **Real-time Updates**: Live updates for waitlist status and slot availability

## Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with SQLAlchemy ORM (Supabase recommended)
- **Authentication**: JWT tokens with secure cookie storage
- **Migration**: Alembic for database migrations
- **API Documentation**: Auto-generated OpenAPI/Swagger docs

### Frontend (Next.js)
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Forms**: React Hook Form with validation
- **HTTP Client**: Axios with interceptors
- **Icons**: Lucide React

## Quick Start

### Development Commands (Makefile)

For convenience, common development tasks are available via Makefile:

```bash
make help          # Show all available commands
make install-dev   # Install development dependencies  
make dev           # Start development server
make test          # Run tests
make format        # Format code (black + isort)
make lint          # Run linting (ruff)
make type-check    # Run type checking (mypy)
make check         # Run all checks (format + lint + type + test)
```

### Option 1: Supabase + Cloud Deployment (Recommended)

This option uses Supabase for the database and cloud platforms for hosting.

1. **Set up Supabase**:
   - Create account at [Supabase](https://supabase.com)
   - Create new project
   - Copy database connection string

2. **Deploy Backend** (choose one):
   - [Railway](https://railway.app) (recommended)
   - [Vercel](https://vercel.com) (serverless)

3. **Deploy Frontend**:
   - [Vercel](https://vercel.com) (recommended)

4. **Detailed Instructions**: See [DEPLOYMENT.md](DEPLOYMENT.md)

### Option 2: Local Development with Supabase

1. Set up Supabase project (see DEPLOYMENT.md)

2. Update `docker-compose.yml` with your Supabase credentials

3. Run with Supabase:
```bash
docker-compose up
```

### Option 3: Manual Setup

#### Backend Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
# Production dependencies
pip install -e .

# Development dependencies (optional)
pip install -e ".[dev]"

# Testing dependencies (optional)
pip install -e ".[test]"

# Or use the Makefile
make install-dev
```

3. Set up PostgreSQL database (Supabase or local) and update `.env` file

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the FastAPI server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the Makefile
make dev
```

#### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Update environment file:
```bash
cp env.local.example .env.local
# Edit .env.local with your API URL
```

4. Start development server:
```bash
npm run dev
```

## API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `POST /logout` - User logout
- `GET /me` - Get current user info

### Patients
- `GET /patients` - Get all patients
- `POST /patients` - Add new patient
- `DELETE /patients/{id}` - Remove patient

### Providers
- `GET /providers` - Get all providers
- `POST /providers` - Add new provider
- `DELETE /providers` - Remove provider

### Slots
- `GET /slots` - Get all open slots
- `POST /slots` - Add new slot
- `DELETE /slots/{id}` - Remove slot
- `POST /slots/{slot_id}/propose/{patient_id}` - Propose slot to patient
- `POST /slots/{slot_id}/confirm/{patient_id}` - Confirm booking
- `POST /slots/{slot_id}/cancel/{patient_id}` - Cancel proposal

## Database Schema

### Users
- User authentication and profile information
- Clinic details and preferences

### Patients
- Patient contact information
- Appointment preferences and availability
- Wait time tracking and urgency levels

### Providers
- Healthcare provider information
- Name and identification details

### Slots (Cancelled Appointments)
- Open appointment slot details
- Provider, date, time, and duration
- Status tracking (available/pending)

## Development

### Backend Development

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Code formatting and linting:
```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Lint with ruff (modern, fast linter)
ruff check .

# Type checking with mypy
mypy .
```

3. Run tests:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

4. Database migrations for changes:
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

5. The FastAPI server will auto-reload with `--reload` flag

### Frontend Development

1. Make changes to React components
2. Next.js will hot-reload changes automatically
3. TypeScript will provide compile-time error checking

### Adding New Features

1. **Backend**: Add new endpoints in `main.py`, models in `src/models.py`, and database operations in `src/db_managers.py`
2. **Frontend**: Add new pages in `src/app/`, components in `src/components/`, and API calls in `src/lib/api.ts`

## Deployment Options

### 🚀 Production Deployment (Recommended)

**Database**: Supabase PostgreSQL (free tier: 500MB)
**Backend**: Railway ($5/month) or Vercel (serverless)
**Frontend**: Vercel (free tier)

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

### 🐳 Self-Hosted with Docker

```bash
# Development with Supabase
docker-compose up
```

### Environment Variables

#### Backend (.env)
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:3000"]
```

#### Frontend (frontend/.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
├── main.py                 # FastAPI application
├── pyproject.toml         # Python dependencies and project config
├── Makefile               # Development commands
├── Dockerfile             # Backend container
├── docker-compose.yml     # Development with Supabase
├── env.example            # Environment variables template
├── alembic/               # Database migrations
├── src/                   # Source code
│   ├── __init__.py       # Package version info
│   ├── auth.py           # Authentication logic
│   ├── database.py       # Database configuration
│   ├── models.py         # SQLAlchemy models
│   └── db_managers.py    # Database operations
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/         # Next.js pages
│   │   ├── components/  # React components
│   │   ├── lib/         # API client
│   │   └── types/       # TypeScript types
│   ├── Dockerfile       # Frontend container
│   └── package.json     # Node.js dependencies
├── vercel.json          # Vercel deployment config
├── railway.toml         # Railway deployment config
└── DEPLOYMENT.md        # Deployment guide
```

## Deployment Configurations

The project includes configuration files for various deployment platforms:

- `vercel.json` - Vercel deployment (serverless)
- `railway.toml` - Railway deployment
- `docker-compose.yml` - Development with Supabase

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues, please:
1. Check the API documentation at `/docs` when running the backend
2. Review the README files in both root and frontend directories
3. Check the [DEPLOYMENT.md](DEPLOYMENT.md) guide for deployment issues
4. Create an issue in the repository

## Tech Stack Summary

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, React Hook Form
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, JWT Authentication  
- **Database**: PostgreSQL (Supabase recommended)
- **Deployment**: Vercel (frontend), Railway/Vercel (backend)
- **Development**: Docker, Hot reload, Auto-migrations
- **Python Tooling**: pyproject.toml, Black, isort, Ruff, MyPy, Pytest
