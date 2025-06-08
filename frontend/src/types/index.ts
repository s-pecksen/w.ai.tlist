export interface User {
  id: string;
  username: string;
  clinic_name?: string;
  user_name_for_message?: string;
  appointment_types?: string[];
  appointment_types_data?: AppointmentTypeData[];
}

export interface AppointmentTypeData {
  appointment_type: string;
  durations: number[];
}

export interface Patient {
  id: string;
  name: string;
  phone: string;
  email?: string;
  reason?: string;
  urgency: 'low' | 'medium' | 'high';
  appointment_type?: string;
  duration: string;
  provider: string;
  status: 'waiting' | 'pending' | 'confirmed' | 'cancelled';
  timestamp?: string;
  wait_time?: string;
  availability?: Record<string, string[]>;
  availability_mode?: 'available' | 'unavailable';
  proposed_slot_id?: string;
  proposed_slot_details?: string;
}

export interface Provider {
  id: number;
  name: string;
  first_name: string;
  last_initial?: string;
}

export interface Slot {
  id: string;
  provider: string;
  slot_date: string;
  slot_time: string;
  slot_period: 'AM' | 'PM';
  duration: number;
  status: 'available' | 'pending' | 'confirmed';
  proposed_patient_id?: string;
  proposed_patient_name?: string;
  notes?: string;
}

export interface PatientFormData {
  name: string;
  phone: string;
  email?: string;
  reason?: string;
  urgency: 'low' | 'medium' | 'high';
  appointment_type?: string;
  duration: number;
  provider: string;
  availability_mode: 'available' | 'unavailable';
  availability: Record<string, string[]>;
}

export interface ProviderFormData {
  first_name: string;
  last_initial?: string;
}

export interface SlotFormData {
  provider: string;
  slot_date: string;
  slot_time: string;
  duration: number;
  notes?: string;
}

export interface LoginFormData {
  username: string;
  password: string;
}

export interface RegisterFormData {
  username: string;
  password: string;
  clinic_name?: string;
  user_name?: string;
} 