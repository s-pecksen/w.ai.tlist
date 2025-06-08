from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthHandler, get_current_user
from src.database import init_db, get_db
from src.models import User, Patient, Provider, CancelledSlot
from src.db_managers import DBProviderManager, DBPatientWaitlistManager, DBCancelledSlotManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create an instance of AuthHandler
auth_handler = AuthHandler()

# Database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down application...")

# Create FastAPI app
app = FastAPI(
    title="Waitlist Management API",
    description="A comprehensive waitlist management system for healthcare providers",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = []
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    try:
        origins = json.loads(cors_origins_env)
    except json.JSONDecodeError:
        origins = [cors_origins_env]  # Single origin as string
else:
    # Default origins for development
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
    ]

# Add Vercel deployment domains dynamically
environment = os.getenv("ENVIRONMENT", "development")
if environment == "production":
    # Allow all HTTPS origins in production (you can restrict this further)
    origins.append("https://*.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Waitlist Management API", 
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs": "/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Simple query to check database connectivity
        result = await db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# User registration
@app.post("/register")
async def register(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    
    username = data.get("username")
    password = data.get("password") 
    clinic_name = data.get("clinic_name", "")
    user_name_for_message = data.get("user_name_for_message", "")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    # Use AuthHandler to create user directly
    try:
        user = await auth_handler.create_user(
            db=db,
            username=username,
            password=password,
            clinic_name=clinic_name,
            user_name_for_message=user_name_for_message
        )
        return {"message": "User created successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

# User login
@app.post("/login") 
async def login(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
    
    # Use AuthHandler to authenticate user
    user = await auth_handler.authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token using AuthHandler
    access_token = auth_handler.create_access_token(data={"sub": user.username})
    
    # Set cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=os.getenv("ENVIRONMENT") == "production",
        samesite="lax",
        max_age=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 1440)) * 60
    )
    
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "clinic_name": user.clinic_name,
            "user_name_for_message": user.user_name_for_message
        }
    }

# User logout
@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}

# Get current user info
@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "clinic_name": current_user.clinic_name,
        "user_name_for_message": current_user.user_name_for_message
    }

# Patient endpoints
@app.get("/patients")
async def get_patients(current_user: User = Depends(get_current_user)):
    manager = DBPatientWaitlistManager(current_user.username)
    patients = await manager.get_all_patients()
    return patients

@app.post("/patients")
async def add_patient(request: Request, current_user: User = Depends(get_current_user)):
    data = await request.json()
    manager = DBPatientWaitlistManager(current_user.username)
    
    success = await manager.add_patient(
        name=data.get("name"),
        phone=data.get("phone"),
        email=data.get("email", ""),
        reason=data.get("reason", ""),
        urgency=data.get("urgency", "medium"),
        appointment_type=data.get("appointment_type", ""),
        duration=data.get("duration", 30),
        provider=data.get("provider", "no preference"),
        availability=data.get("availability", {}),
        availability_mode=data.get("availability_mode", "available")
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add patient")
    
    return {"message": "Patient added successfully"}

@app.delete("/patients/{patient_id}")
async def remove_patient(patient_id: str, current_user: User = Depends(get_current_user)):
    manager = DBPatientWaitlistManager(current_user.username)
    success = await manager.remove_patient(patient_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return {"message": "Patient removed successfully"}

# Provider endpoints
@app.get("/providers")
async def get_providers(current_user: User = Depends(get_current_user)):
    manager = DBProviderManager(current_user.username)
    providers = await manager.get_provider_list()
    return providers

@app.post("/providers")
async def add_provider(request: Request, current_user: User = Depends(get_current_user)):
    data = await request.json()
    manager = DBProviderManager(current_user.username)
    
    success = await manager.add_provider(
        first_name=data.get("first_name"),
        last_initial=data.get("last_initial", "")
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Provider already exists or invalid data")
    
    return {"message": "Provider added successfully"}

@app.delete("/providers")
async def remove_provider(request: Request, current_user: User = Depends(get_current_user)):
    data = await request.json()
    manager = DBProviderManager(current_user.username)
    
    success = await manager.remove_provider(
        first_name=data.get("first_name"),
        last_initial=data.get("last_initial", "")
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return {"message": "Provider removed successfully"}

# Slot endpoints
@app.get("/slots")
async def get_slots(current_user: User = Depends(get_current_user)):
    manager = DBCancelledSlotManager(current_user.username)
    slots = await manager.get_all_slots()
    return slots

@app.post("/slots")
async def add_slot(request: Request, current_user: User = Depends(get_current_user)):
    data = await request.json()
    manager = DBCancelledSlotManager(current_user.username)
    
    success = await manager.add_slot(
        provider=data.get("provider"),
        slot_date=data.get("slot_date"),
        slot_time=data.get("slot_time"),
        slot_period=data.get("slot_period"),
        duration=data.get("duration"),
        notes=data.get("notes", "")
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add slot")
    
    return {"message": "Slot added successfully"}

@app.delete("/slots/{slot_id}")
async def remove_slot(slot_id: str, current_user: User = Depends(get_current_user)):
    manager = DBCancelledSlotManager(current_user.username)
    success = await manager.remove_slot(slot_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    return {"message": "Slot removed successfully"}

# Matching endpoints
@app.get("/patients/{patient_id}/matching-slots")
async def find_matching_slots(patient_id: str, current_user: User = Depends(get_current_user)):
    patient_manager = DBPatientWaitlistManager(current_user.username)
    slot_manager = DBCancelledSlotManager(current_user.username)
    
    patient = await patient_manager.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    all_slots = await slot_manager.get_all_slots()
    available_slots = [slot for slot in all_slots if slot.get("status") == "available"]
    
    # Filter slots based on patient requirements
    matching_slots = []
    patient_duration = int(patient.get("duration", 0))
    patient_provider_pref = patient.get("provider", "no preference").lower()
    patient_availability = patient.get("availability", {})
    patient_availability_mode = patient.get("availability_mode", "available")
    
    for slot in available_slots:
        # Duration check
        slot_duration = int(slot.get("duration", 0))
        if patient_duration > slot_duration:
            continue
            
        # Provider check
        slot_provider = slot.get("provider", "").lower()
        if patient_provider_pref != "no preference" and patient_provider_pref != slot_provider:
            continue
            
        # Availability check (simplified)
        slot_date_str = slot.get("slot_date")
        slot_period = slot.get("slot_period", "").upper()
        
        if patient_availability:
            try:
                slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d")
                slot_weekday = slot_date.strftime("%A")
                day_periods = patient_availability.get(slot_weekday, [])
                
                if patient_availability_mode == "available":
                    if not day_periods or slot_period not in day_periods:
                        continue
                elif patient_availability_mode == "unavailable":
                    if day_periods and slot_period in day_periods:
                        continue
            except (ValueError, AttributeError):
                continue
        
        matching_slots.append(slot)
    
    return {"patient": patient, "matching_slots": matching_slots}

@app.post("/slots/{slot_id}/propose/{patient_id}")
async def propose_slot(slot_id: str, patient_id: str, current_user: User = Depends(get_current_user)):
    patient_manager = DBPatientWaitlistManager(current_user.username)
    slot_manager = DBCancelledSlotManager(current_user.username)
    
    # Get patient name for the proposal
    patient = await patient_manager.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    patient_name = patient.get("name", "Unknown")
    
    # Mark slot as pending
    slot_marked = await slot_manager.mark_as_pending(slot_id, patient_id, patient_name)
    if not slot_marked:
        raise HTTPException(status_code=400, detail="Failed to mark slot as pending")
    
    # Mark patient as pending
    patient_marked = await patient_manager.mark_as_pending(patient_id, slot_id)
    if not patient_marked:
        # Revert slot marking
        await slot_manager.cancel_proposal(slot_id)
        raise HTTPException(status_code=400, detail="Failed to mark patient as pending")
    
    return {"message": "Slot proposed successfully"}

@app.post("/slots/{slot_id}/confirm/{patient_id}")
async def confirm_booking(slot_id: str, patient_id: str, current_user: User = Depends(get_current_user)):
    patient_manager = DBPatientWaitlistManager(current_user.username)
    slot_manager = DBCancelledSlotManager(current_user.username)
    
    # Remove patient and slot
    patient_removed = await patient_manager.remove_patient(patient_id)
    slot_removed = await slot_manager.remove_slot(slot_id)
    
    if not (patient_removed and slot_removed):
        raise HTTPException(status_code=500, detail="Failed to confirm booking")
    
    return {"message": "Booking confirmed successfully"}

@app.post("/slots/{slot_id}/cancel/{patient_id}")
async def cancel_proposal(slot_id: str, patient_id: str, current_user: User = Depends(get_current_user)):
    patient_manager = DBPatientWaitlistManager(current_user.username)
    slot_manager = DBCancelledSlotManager(current_user.username)
    
    # Reset both slot and patient status
    slot_reset = await slot_manager.cancel_proposal(slot_id)
    patient_reset = await patient_manager.cancel_proposal(patient_id)
    
    if not (slot_reset and patient_reset):
        raise HTTPException(status_code=500, detail="Failed to cancel proposal")
    
    return {"message": "Proposal cancelled successfully"}

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") != "production"
    ) 