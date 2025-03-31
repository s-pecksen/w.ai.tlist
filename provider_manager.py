from typing import List, Optional
import os
import csv

class ProviderManager:
    def __init__(self, provider_file: str = 'provider.csv'):
        """
        Initialize the Provider Manager with extended functionality
        
        Args:
            provider_file (str): Path to the CSV file storing provider names
        """
        self.provider_file = provider_file
        self.providers: List[dict] = self._load_providers()

    def _load_providers(self) -> List[dict]:
        """
        Load existing providers with additional metadata
        
        Returns:
            List of provider dictionaries
        """
        if not os.path.exists(self.provider_file):
            return []
        
        try:
            with open(self.provider_file, 'r') as file:
                reader = csv.DictReader(file, fieldnames=['name', 'is_active'])
                providers = []
                for row in reader:
                    if row['name'] and row['name'].strip():
                        # Handle case where is_active might be None
                        is_active = False
                        if row.get('is_active'):
                            is_active = row['is_active'].lower() == 'true'
                        
                        providers.append({
                            'name': row['name'].strip(),
                            'is_active': is_active
                        })
                return providers
        except Exception as e:
            print(f"Error loading providers: {str(e)}")
            # Return empty list if there's an error
            return []

    def _save_providers(self):
        """
        Save current provider list to CSV file
        """
        with open(self.provider_file, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=['name', 'is_active'])
            for provider in sorted(self.providers, key=lambda x: x['name']):
                writer.writerow(provider)

    def add_provider(self, first_name: str, last_initial: Optional[str] = None, is_active: bool = True) -> bool:
        """
        Add a new provider to the list
        
        Args:
            first_name (str): First name of the provider
            last_initial (str, optional): Last initial to differentiate similar names
            is_active (bool): Whether provider is available for appointments
        
        Returns:
            bool: True if added successfully, False if already exists
        """
        # Validate input
        if not first_name or not first_name.strip():
            raise ValueError("Provider first name cannot be blank")
        
        # Construct full name with optional last initial
        full_name = first_name.strip()
        if last_initial:
            full_name += f" {last_initial.strip()}"
        
        # Check for duplicates (case-insensitive)
        if any(p['name'].lower() == full_name.lower() for p in self.providers):
            return False
        
        # Add provider
        self.providers.append({
            'name': full_name,
            'is_active': is_active
        })
        self._save_providers()
        return True

    def is_provider_match(self, cancelled_provider: str, patient_preference: str) -> bool:
        """
        Determine if a patient is eligible for a cancelled appointment
        
        Args:
            cancelled_provider (str): Name of the provider for the cancelled appointment
            patient_preference (str): Patient's provider preference
        
        Returns:
            bool: True if patient is eligible, False otherwise
        """
        # Check if cancelled provider exists and is active
        cancelled_provider_exists = any(
            p['name'].lower() == cancelled_provider.lower() and p['is_active'] 
            for p in self.providers
        )
        
        # If no preference or preference matches cancelled provider
        if not patient_preference or patient_preference.lower() == cancelled_provider.lower():
            return cancelled_provider_exists
        
        # If patient has a specific preference
        return False

    def get_active_providers(self) -> List[str]:
        """
        Retrieve the current list of active providers
        
        Returns:
            List of active provider names
        """
        return [p['name'] for p in self.providers if p['is_active']]

    def get_provider_list(self) -> List[dict]:
        """
        Get the full list of providers
        
        Returns:
            The list of provider dictionaries
        """
        return self.providers
        
    def remove_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """
        Remove a provider from the list
        
        Args:
            first_name (str): First name of the provider
            last_initial (str, optional): Last initial to differentiate similar names
            
        Returns:
            bool: True if removed successfully, False if not found
        """
        # Construct full name with optional last initial
        full_name = first_name.strip()
        if last_initial:
            full_name += f" {last_initial.strip()}"
        
        # Search for the provider
        for i, provider in enumerate(self.providers):
            if provider['name'].lower() == full_name.lower():
                self.providers.pop(i)
                self._save_providers()
                return True
        
        return False

    def toggle_provider_active(self, provider_name: str) -> bool:
        """
        Toggle a provider's active status
        
        Args:
            provider_name (str): Name of the provider to toggle
        
        Returns:
            bool: True if toggled successfully, False if not found
        """
        for provider in self.providers:
            if provider['name'] == provider_name:
                provider['is_active'] = not provider['is_active']
                self._save_providers()
                return True
        return False

# Example usage in matching algorithm
def find_replacement_patient(cancelled_appointment, patient_waitlist, provider_manager):
    """
    Find a suitable replacement patient for a cancelled appointment
    
    Args:
        cancelled_appointment: Details of the cancelled appointment
        patient_waitlist: List of patients waiting for appointments
        provider_manager: Instance of ProviderManager
    
    Returns:
        Eligible patient or None
    """
    for patient in patient_waitlist:
        if provider_manager.is_provider_match(
            cancelled_appointment.provider, 
            patient.provider_preference
        ):
            return patient
    
    return None