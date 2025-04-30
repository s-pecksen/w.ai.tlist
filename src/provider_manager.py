from typing import List, Optional, Dict
import os
import csv

class ProviderManager:
    def __init__(self, provider_file: str = 'provider.csv'):
        """
        Initialize the Provider Manager.

        Args:
            provider_file (str): Path to the CSV file storing provider names.
        """
        self.provider_file = provider_file
        # Store providers as a list of dictionaries {'name': 'Provider Name'}
        self.providers: List[Dict[str, str]] = self._load_providers()

    def _load_providers(self) -> List[Dict[str, str]]:
        """
        Load existing providers from the CSV file.
        Only loads the 'name' column.

        Returns:
            List of provider dictionaries [{'name': 'Provider Name'}].
        """
        providers = []
        if not os.path.exists(self.provider_file):
            # Create the file with a header if it doesn't exist
            try:
                with open(self.provider_file, 'w', newline='') as file:
                     writer = csv.writer(file)
                     writer.writerow(['name']) # Write only the name header
                return []
            except IOError as e:
                 print(f"Error creating provider file {self.provider_file}: {e}")
                 return [] # Return empty list if creation fails

        try:
            with open(self.provider_file, 'r', newline='') as file:
                # Use DictReader, expecting only the 'name' field
                # Use restval='' to handle rows with potentially fewer columns gracefully
                # Use ignore_missing_fieldnames=True if library supports it or handle manually
                reader = csv.DictReader(file, fieldnames=['name'], restval='') # Explicitly define expected fieldname
                header = next(reader, None) # Skip header row
                if header and header.get('name', '').lower() != 'name':
                    # If the first row doesn't look like a header, reset and process it
                    # This handles files without headers or with unexpected first rows
                    file.seek(0)
                    reader = csv.DictReader(file, fieldnames=['name'], restval='')

                for row in reader:
                    # Ensure 'name' key exists and has a non-empty, non-whitespace value
                    provider_name = row.get('name', '').strip()
                    if provider_name:
                        # Avoid adding duplicates (case-insensitive check)
                        if not any(p['name'].lower() == provider_name.lower() for p in providers):
                            providers.append({'name': provider_name})
                        else:
                            print(f"Skipping duplicate provider name found during load: {provider_name}")
                    # else: # Optionally log skipped blank rows
                    #    print(f"Skipping blank provider name found during load: {row}")

        except Exception as e:
            print(f"Error loading providers from {self.provider_file}: {e}")
            return [] # Return empty list on error

        return providers


    def _save_providers(self):
        """
        Save current provider list (only names) to CSV file.
        """
        try:
            with open(self.provider_file, 'w', newline='') as file:
                # Define fieldnames for the writer
                fieldnames = ['name']
                writer = csv.DictWriter(file, fieldnames=fieldnames)

                writer.writeheader() # Write the header row
                # Sort by name before writing
                for provider_dict in sorted(self.providers, key=lambda x: x.get('name', '')):
                     # Write only the 'name' field
                     writer.writerow({'name': provider_dict.get('name')})
        except IOError as e:
            print(f"Error saving providers to {self.provider_file}: {e}")


    def add_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """
        Add a new provider to the list.

        Args:
            first_name (str): First name of the provider.
            last_initial (str, optional): Last initial to differentiate similar names.

        Returns:
            bool: True if added successfully, False if already exists.
        """
        # Validate input
        if not first_name or not first_name.strip():
            print("Error: Provider first name cannot be blank.") # Changed from raise
            return False

        # Construct full name with optional last initial
        full_name = first_name.strip()
        if last_initial and last_initial.strip(): # Ensure last_initial is not just whitespace
            full_name += f" {last_initial.strip()}"

        # Check for duplicates (case-insensitive)
        if any(p['name'].lower() == full_name.lower() for p in self.providers):
            print(f"Provider '{full_name}' already exists.")
            return False

        # Add provider
        self.providers.append({'name': full_name})
        self._save_providers()
        print(f"Provider '{full_name}' added.")
        return True

    def get_provider_list(self) -> List[Dict[str, str]]:
        """
        Get the full list of provider dictionaries (containing just 'name').

        Returns:
            The list of provider dictionaries [{'name': 'Provider Name'}].
        """
        # Return a copy to prevent external modification
        return [p.copy() for p in self.providers]

    def remove_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """
        Remove a provider from the list.

        Args:
            first_name (str): First name of the provider.
            last_initial (str, optional): Last initial to differentiate similar names.

        Returns:
            bool: True if removed successfully, False if not found.
        """
        # Construct full name with optional last initial
        full_name = first_name.strip()
        if last_initial and last_initial.strip(): # Ensure last_initial is not just whitespace
            full_name += f" {last_initial.strip()}"

        initial_length = len(self.providers)
        # Filter out the provider (case-insensitive)
        self.providers = [p for p in self.providers if p.get('name', '').lower() != full_name.lower()]

        if len(self.providers) < initial_length:
            self._save_providers()
            print(f"Provider '{full_name}' removed.")
            return True
        else:
            print(f"Provider '{full_name}' not found for removal.")
            return False