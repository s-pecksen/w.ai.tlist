# Waitlist Management Frontend

This is the Next.js frontend for the Waitlist Management application.

## Features

- **Dashboard**: View and manage patient waitlist
- **Patient Management**: Add, view, and remove patients
- **Provider Management**: Manage healthcare providers
- **Slot Management**: Manage open appointment slots
- **Matching System**: Find and propose slots to patients
- **Authentication**: JWT-based authentication with cookies

## Tech Stack

- Next.js 14 with App Router
- TypeScript
- Tailwind CSS
- React Hook Form
- Axios for API calls
- Lucide React icons

## Getting Started

### Prerequisites

- Node.js 18 or later
- Backend API running (see main README)

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
cp env.local.example .env.local
```

3. Update the API URL in `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Docker

### Build and run with Docker:

```bash
docker build -t waitlist-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 waitlist-frontend
```

### Run with docker-compose:

From the root directory:

```bash
docker-compose up
```

This will start both the backend and frontend services.

## API Integration

The frontend communicates with the FastAPI backend through:

- **Authentication**: JWT tokens stored in HTTP-only cookies
- **API Calls**: Axios client with automatic token refresh
- **Error Handling**: Centralized error handling with user feedback

## Pages

- `/` - Dashboard with patient waitlist
- `/login` - User authentication
- `/register` - User registration
- `/providers` - Provider management
- `/slots` - Open slot management

## Components

- `Layout` - Main layout with navigation
- `PatientForm` - Add new patients
- `PatientTable` - Display patient waitlist
- Various page-specific components

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL (required)

## Development Notes

- The app uses client-side rendering with API calls
- Authentication state is managed through cookies
- Forms use React Hook Form for validation
- Styling uses Tailwind CSS utility classes
- Icons from Lucide React

## Deployment

1. Set `NEXT_PUBLIC_API_URL` to your production API URL
2. Build the application: `npm run build`
3. Deploy using your preferred platform (Vercel, Docker, etc.)

For Docker deployment, the Dockerfile uses multi-stage builds for optimization.
