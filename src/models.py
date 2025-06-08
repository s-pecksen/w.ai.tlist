from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Dict, Any

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    clinic_name = Column(String(200), default="")
    user_name_for_message = Column(String(200), default="")
    appointment_types = Column(JSON, default=list)
    appointment_types_data = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    providers = relationship("Provider", back_populates="user", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="user", cascade="all, delete-orphan")
    slots = relationship("CancelledSlot", back_populates="user", cascade="all, delete-orphan")


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_initial = Column(String(1), default="")
    name = Column(String(200), nullable=False)  # Full name for display
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="providers")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(200), default="")
    reason = Column(Text, default="")
    urgency = Column(String(20), default="medium")  # high, medium, low
    appointment_type = Column(String(100), default="")
    duration = Column(Integer, default=30)  # in minutes
    provider = Column(String(200), default="no preference")
    status = Column(String(20), default="waiting")  # waiting, pending, confirmed, cancelled
    proposed_slot_id = Column(String(100), nullable=True)  # For pending status
    availability = Column(JSON, default=dict)  # Day/time preferences
    availability_mode = Column(String(20), default="available")  # available, unavailable
    wait_time = Column(String(50), default="0 minutes")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="patients")


class CancelledSlot(Base):
    __tablename__ = "cancelled_slots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot_id = Column(String(100), unique=True, nullable=False)  # UUID-like identifier
    provider = Column(String(200), nullable=False)
    slot_date = Column(String(20), nullable=False)  # YYYY-MM-DD format
    slot_time = Column(String(10), nullable=False)  # HH:MM format
    slot_period = Column(String(5), nullable=False)  # AM/PM
    duration = Column(Integer, nullable=False)  # in minutes
    status = Column(String(20), default="available")  # available, pending, confirmed
    proposed_patient_id = Column(String(100), nullable=True)  # For pending status
    proposed_patient_name = Column(String(200), nullable=True)  # For display
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="slots") 