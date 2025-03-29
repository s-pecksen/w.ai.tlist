class HygienistManager:
    def __init__(self, hygienist_file: str = 'hygienists.csv'):
        """
        Initialize the Hygienist Manager with extended functionality
        
        Args:
            hygienist_file (str): Path to the CSV file storing hygienist names
        """
        self.hygienist_file = hygienist_file
        self.hygienists: List[dict] = self._load_hygienists()

    def _load_hygienists(self) -> List[dict]:
        """
        Load existing hygienists with additional metadata
        
        Returns:
            List of hygienist dictionaries
        """
        if not os.path.exists(self.hygienist_file):
            return []
        
        with open(self.hygienist_file, 'r') as file:
            reader = csv.DictReader(file, fieldnames=['name', 'is_active'])
            return [
                {
                    'name': row['name'].strip(), 
                    'is_active': row['is_active'].lower() == 'true'
                } 
                for row in reader if row['name'].strip()
            ]

    def _save_hygienists(self):
        """
        Save current hygienist list to CSV file
        """
        with open(self.hygienist_file, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['name', 'is_active'])
            for hygienist in sorted(self.hygienists, key=lambda x: x['name']):
                writer.writerow(hygienist)

    def add_hygienist(self, first_name: str, last_initial: Optional[str] = None, is_active: bool = True) -> bool:
        """
        Add a new hygienist to the list
        
        Args:
            first_name (str): First name of the hygienist
            last_initial (str, optional): Last initial to differentiate similar names
            is_active (bool): Whether hygienist is available for appointments
        
        Returns:
            bool: True if added successfully, False if already exists
        """
        # Validate input
        if not first_name or not first_name.strip():
            raise ValueError("Hygienist first name cannot be blank")
        
        # Construct full name with optional last initial
        full_name = first_name.strip()
        if last_initial:
            full_name += f" {last_initial.strip()}"
        
        # Check for duplicates (case-insensitive)
        if any(h['name'].lower() == full_name.lower() for h in self.hygienists):
            return False
        
        # Add hygienist
        self.hygienists.append({
            'name': full_name,
            'is_active': is_active
        })
        self._save_hygienists()
        return True

    def is_hygienist_match(self, cancelled_hygienist: str, patient_preference: str) -> bool:
        """
        Determine if a patient is eligible for a cancelled appointment
        
        Args:
            cancelled_hygienist (str): Name of the hygienist for the cancelled appointment
            patient_preference (str): Patient's hygienist preference
        
        Returns:
            bool: True if patient is eligible, False otherwise
        """
        # Check if cancelled hygienist exists and is active
        cancelled_hygienist_exists = any(
            h['name'].lower() == cancelled_hygienist.lower() and h['is_active'] 
            for h in self.hygienists
        )
        
        # If no preference or preference matches cancelled hygienist
        if not patient_preference or patient_preference.lower() == cancelled_hygienist.lower():
            return cancelled_hygienist_exists
        
        # If patient has a specific preference
        return False

    def get_active_hygienists(self) -> List[str]:
        """
        Retrieve the current list of active hygienists
        
        Returns:
            List of active hygienist names
        """
        return [h['name'] for h in self.hygienists if h['is_active']]

# Example usage in matching algorithm
def find_replacement_patient(cancelled_appointment, patient_waitlist, hygienist_manager):
    """
    Find a suitable replacement patient for a cancelled appointment
    
    Args:
        cancelled_appointment: Details of the cancelled appointment
        patient_waitlist: List of patients waiting for appointments
        hygienist_manager: Instance of HygienistManager
    
    Returns:
        Eligible patient or None
    """
    for patient in patient_waitlist:
        if hygienist_manager.is_hygienist_match(
            cancelled_appointment.hygienist, 
            patient.hygienist_preference
        ):
            return patient
    
    return None