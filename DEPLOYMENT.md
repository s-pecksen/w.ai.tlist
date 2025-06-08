# Deployment Guide - Supabase Integration

This guide covers deploying the Waitlist Management application using Supabase for the database and cloud platforms for hosting.

## Overview

- **Database**: Supabase PostgreSQL (free tier: 500MB)
- **Backend API**: Deploy to Railway (recommended) or Vercel (serverless)
- **Frontend**: Deploy to Vercel (recommended)

## Prerequisites

1. [Supabase](https://supabase.com) account
2. [Vercel](https://vercel.com) account (for frontend)
3. [Railway](https://railway.app) account (for backend, recommended)

## Step 1: Set Up Supabase Database

### 1.1 Create Supabase Project

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Click "New Project"
3. Choose your organization
4. Fill in project details:
   - **Name**: `waitlist-management`
   - **Database Password**: Generate a strong password
   - **Region**: Choose closest to your users
5. Click "Create new project"

### 1.2 Get Database Connection Details

Once your project is created:

1. Go to **Settings** → **Database**
2. Copy the connection string from **Connection string** → **URI**
3. It will look like: `postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres`

### 1.3 Set Up Database Schema

The application will automatically create tables using Alembic migrations on first startup.

## Step 2: Deploy Backend API

Choose one of the following deployment options:

### Option A: Railway (Recommended - $5/month)

1. **Connect Repository**:
   - Go to [Railway](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Configure Environment Variables**:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
   JWT_ALGORITHM=HS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ENVIRONMENT=production
   CORS_ORIGINS=["https://your-frontend-domain.vercel.app"]
   ```

3. **Deploy**: Railway will automatically deploy your application

### Option B: Vercel (Serverless - Free)

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Deploy**:
   ```bash
   vercel --prod
   ```

3. **Configure Environment Variables** in Vercel dashboard (same as above)

## Step 3: Deploy Frontend

### 3.1 Update Frontend Configuration

1. **Update API URL** in `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend-api-url.railway.app
   ```

### 3.2 Deploy to Vercel

1. **Connect Repository**:
   - Go to [Vercel Dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your GitHub repository
   - Set **Framework Preset** to "Next.js"
   - Set **Root Directory** to `frontend`

2. **Configure Environment Variables**:
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend-api-url.railway.app
   ```

3. **Deploy**: Vercel will automatically build and deploy

### 3.3 Update CORS Settings

After frontend deployment, update backend CORS settings:

```env
CORS_ORIGINS=["https://your-frontend-domain.vercel.app"]
```

## Step 4: Database Migration

The application will automatically run migrations on startup, but you can also run them manually:

### 4.1 Local Migration (if needed)

```bash
# Set DATABASE_URL to your Supabase connection string
export DATABASE_URL="postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run migrations
alembic upgrade head
```

## Step 5: Verification

### 5.1 Test API

Visit your backend URL: `https://your-backend-api-url.railway.app/docs`

You should see the FastAPI documentation.

### 5.2 Test Frontend

Visit your frontend URL: `https://your-frontend-domain.vercel.app`

Try to register and login to verify everything works.

## Configuration Reference

### Backend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Supabase PostgreSQL connection string | `postgresql+asyncpg://postgres:...` |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | `your-super-secret-key` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration time | `1440` |
| `ENVIRONMENT` | Environment setting | `production` |
| `CORS_ORIGINS` | Allowed frontend origins | `["https://yourapp.vercel.app"]` |

### Frontend Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://api.yourapp.com` |

## Cost Breakdown

### Free Tier Option
- **Supabase**: Free (up to 500MB database)
- **Vercel**: Free (frontend + serverless backend)
- **Total**: $0/month

### Recommended Production Setup
- **Supabase**: Free (up to 500MB database)
- **Railway**: $5/month (backend hosting)
- **Vercel**: Free (frontend hosting)
- **Total**: $5/month

## Troubleshooting

### Common Issues

1. **CORS Errors**: 
   - Ensure `CORS_ORIGINS` includes your frontend domain
   - Check that frontend is using correct API URL

2. **Database Connection Issues**:
   - Verify Supabase connection string is correct
   - Ensure database password is properly escaped in URL

3. **Authentication Issues**:
   - Check JWT_SECRET_KEY is set and consistent
   - Verify token expiration settings

4. **Migration Issues**:
   - Ensure database user has proper permissions
   - Check Alembic configuration

### Logs and Monitoring

- **Railway**: Check logs in Railway dashboard
- **Vercel**: Check function logs in Vercel dashboard
- **Supabase**: Monitor database activity in Supabase dashboard

## Security Considerations

1. **Environment Variables**: Never commit secrets to version control
2. **CORS**: Restrict origins to your actual domains
3. **JWT Secret**: Use a strong, unique secret key
4. **Database**: Use Supabase's built-in security features
5. **HTTPS**: All production deployments should use HTTPS

## Scaling Considerations

1. **Database**: Supabase can scale to larger plans as needed
2. **Backend**: Railway provides easy scaling options
3. **Frontend**: Vercel automatically scales globally
4. **Monitoring**: Set up alerts for performance and errors

## Next Steps

1. Set up monitoring and alerts
2. Configure backup strategies
3. Implement CI/CD pipelines
4. Add error tracking (e.g., Sentry)
5. Set up domain names and SSL certificates 