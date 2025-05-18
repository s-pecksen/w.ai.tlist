from cryptography.fernet import Fernet

# Generate a key
key = Fernet.generate_key()
print("Your new Fernet key (store this securely!):")
print(key.decode())  # Print the key as a string