import os
import psycopg2
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# --- Database Schema ---
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.users (
    id uuid NOT NULL,
    username text NOT NULL,
    email text UNIQUE,
    password_hash text,
    clinic_name text NULL,
    user_name_for_message text NULL,
    appointment_types jsonb NULL DEFAULT '[]'::jsonb,
    appointment_types_data jsonb NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NULL DEFAULT now(),
    updated_at timestamptz NULL DEFAULT now(),
    CONSTRAINT users_pkey PRIMARY KEY (id),
    CONSTRAINT users_username_key UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS public.providers (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NULL,
    first_name text NOT NULL,
    last_initial text NULL,
    created_at timestamptz NULL DEFAULT now(),
    CONSTRAINT providers_pkey PRIMARY KEY (id),
    CONSTRAINT providers_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.patients (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id UUID NOT NULL,
    name character varying NOT NULL,
    phone character varying NOT NULL,
    email character varying,
    reason text,
    urgency character varying DEFAULT 'medium'::character varying,
    appointment_type character varying,
    duration integer DEFAULT 30,
    provider character varying,
    availability jsonb DEFAULT '{}'::jsonb,
    availability_mode character varying DEFAULT 'available'::character varying,
    status character varying DEFAULT 'waiting'::character varying,
    proposed_slot_id UUID,
    wait_time character varying DEFAULT '0 minutes'::character varying,
    timestamp timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT patients_pkey PRIMARY KEY (id),
    CONSTRAINT patients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.cancelled_slots (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    user_id uuid NULL,
    provider text NOT NULL,
    date date NOT NULL,
    start_time text NOT NULL,
    duration int4 NOT NULL,
    slot_period text NULL,
    notes text NULL,
    status text NULL DEFAULT 'available'::text,
    proposed_patient_id uuid NULL,
    proposed_patient_name text NULL,
    created_at timestamptz NULL DEFAULT now(),
    CONSTRAINT cancelled_slots_pkey PRIMARY KEY (id),
    CONSTRAINT cancelled_slots_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);
"""

def initialize_database():
    """Connects to the database and creates the tables if they don't exist."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logging.error("CRITICAL: DATABASE_URL environment variable not set!")
        logging.info("Please get it from your Supabase Dashboard: Settings > Database > Connection string > URI")
        return

    conn = None
    try:
        logging.info("Connecting to the database...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        logging.info("Executing schema setup script...")
        cur.execute(SCHEMA_SQL)
        
        conn.commit()
        cur.close()
        logging.info("Database schema initialized successfully.")
        
    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
        logging.error("Please ensure your DATABASE_URL is correct and that the database is running.")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    initialize_database() 