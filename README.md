# W.AI.TLIST

## Description
This project aims to streamline clinic operations by automating client/patient scheduling. It offers an easy-to-use solution that reduces the burden on receptionists and enhances patient experience, while keeping data secure and private by avoiding cloud-based storage. This project is in active development, and your feedback and collaboration are welcome.

## Features
- Patient scheduling automation
- Secure local data handling (no cloud-based storage)
- Integration with existing clinic systems

## Getting Started

### Prerequisites
Ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package manager)

### Installation
# SETUP INSTRUCTIONS
# Run all commands below in your terminal/command prompt.

# 1. Download the application
git clone https://github.com/yourusername/your-project.git
cd your-project
# You are now in the project directory

# 2. Create a virtual environment
python -m venv venv
# This creates an isolated Python environment for this project

# 3. Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
# Your prompt should change to show (venv) at the beginning

# 4. Install dependencies
pip install -r requirements.txt
# This installs all required packages for the application

# 5. Generate your encryption key
python -m pip install cryptography
python -c "from cryptography.fernet import Fernet; key = Fernet.generate_key(); print(f'Your encryption key: {key.decode()}')"
# IMPORTANT: Save this key somewhere secure - you'll need it for the next step

# 6. Set up the encryption key permanently

# For Windows:
# Option 1: Through System Properties GUI
# a. Search for "Edit the system environment variables" in Windows search
# b. Click "Environment Variables"
# c. Under "User variables", click "New"
# d. Variable name: FLASK_APP_ENCRYPTION_KEY
# e. Variable value: [paste your generated key]
# f. Click OK on all windows

# Option 2: Using PowerShell (requires admin)
# [System.Environment]::SetEnvironmentVariable('FLASK_APP_ENCRYPTION_KEY', 'your_generated_key_here', 'User')

# For macOS/Linux:
# Add this line to your shell profile file (~/.bash_profile, ~/.zshrc, or ~/.profile)
# export FLASK_APP_ENCRYPTION_KEY="your_generated_key_here"
# Then run:
# source ~/.bash_profile  # or ~/.zshrc or ~/.profile depending on your shell

# For current session only (if you just want to test quickly)
# On Windows (Command Prompt):
set FLASK_APP_ENCRYPTION_KEY=your_generated_key_here
# On Windows (PowerShell):
$env:FLASK_APP_ENCRYPTION_KEY="your_generated_key_here"
# On macOS/Linux:
export FLASK_APP_ENCRYPTION_KEY="your_generated_key_here"

# 7. Run the application
flask run
# The application should now be running at http://127.0.0.1:5000/

---

## Collaboration and Feedback

I welcome contributions and input from others who are passionate about this project. If you have ideas, suggestions, or feedback that could improve the app, please feel free to share them. I’m genuinely interested in collaborating with others to enhance the functionality, design, or usability of this project.

That said, because I have a specific vision and goal for the app, I will carefully consider any input to ensure it aligns with the overall direction. If a suggestion resonates with the project’s core mission, I’d be happy to explore its implementation together. If not, I may respectfully choose to leave the current course of action as is, but I’ll always value the time and effort you’ve taken to contribute.

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

