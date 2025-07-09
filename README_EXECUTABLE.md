# W.AI.TLIST - Cross-Platform Executable

🏥 **W.AI.TLIST** is an intelligent dental appointment management system that helps optimize clinic scheduling through smart patient-slot matching.

## ✨ Features

- **🚀 One-Click Launch**: Double-click to start - no Python installation required
- **🌐 Browser Interface**: Automatically opens in your preferred web browser
- **🔒 Secure & Local**: All data stored locally, no cloud dependencies
- **🖥️ Cross-Platform**: Works on Windows, Linux, and macOS
- **📱 Modern UI**: Responsive web interface accessible from any device on your network

## 🎯 Quick Start

### For End Users

1. **Download & Extract**: Unzip the application folder to your desired location
2. **Run the Application**:
   - **Windows**: Double-click `Waitlyst.exe`
   - **Linux**: Double-click `Waitlyst` or run `./Waitlyst` in terminal
   - **macOS**: Double-click `Waitlyst` (see security notes below)
3. **Access the App**: Your browser will automatically open to the application

### What You'll See

```
╔══════════════════════════════════════════════════════════════╗
║                    W.AI.TLIST LAUNCHER                      ║
║              Dental Appointment Optimization                ║
╚══════════════════════════════════════════════════════════════╝

🚀 Starting W.AI.TLIST...
🔧 Starting Flask server...
⏳ Waiting for server to start...
✅ Server is ready!
🌐 Opening web browser...
✓ Opened application in Chrome: http://127.0.0.1:7860

===============================================
🏥 W.AI.TLIST is now running!
🌐 Web interface: http://127.0.0.1:7860
📋 Use the web interface to manage your dental appointments

⌨️  Press Ctrl+C or close this window to stop the application
===============================================
```

## 🔧 System Requirements

### Minimum Requirements
- **OS**: Windows 7+, Ubuntu 18.04+, macOS 10.14+
- **RAM**: 1GB available memory
- **Storage**: 500MB free disk space
- **Browser**: Any modern web browser (Chrome, Firefox, Safari, Edge)

### Recommended Setup
- **RAM**: 2GB+ available memory
- **Storage**: 1GB+ free disk space
- **Browser**: Google Chrome (for best compatibility)

## 🛠️ Platform-Specific Notes

### 🪟 Windows
- **First Run**: Windows may show a security warning - click "More info" → "Run anyway"
- **Antivirus**: Some antivirus software may flag the executable - this is a false positive
- **Compatibility**: Works on Windows 7, 8, 10, and 11

### 🐧 Linux
- **Permissions**: Make sure the file is executable: `chmod +x Waitlyst`
- **Dependencies**: No additional packages required - everything is bundled
- **Desktop Integration**: You can create a desktop shortcut to the executable

### 🍎 macOS
- **Security**: macOS may block unsigned applications
  - **Method 1**: Right-click → "Open" → Confirm in dialog
  - **Method 2**: System Preferences → Security & Privacy → "Allow"
- **Location**: Best to place in Applications folder for system integration

## 🔒 Security & Privacy

- ✅ **Fully Local**: No data transmitted to external servers
- ✅ **Encrypted Sessions**: All user sessions are encrypted
- ✅ **SQLite Database**: Lightweight, file-based database storage
- ✅ **No Network Access Required**: Works completely offline

## 📁 Application Structure

```
Waitlyst/
├── Waitlyst.exe (Windows) or Waitlyst (Linux/macOS)
├── _internal/
│   ├── templates/          # Web interface templates
│   ├── static/            # CSS, JS, images
│   ├── data/              # Database and user data
│   └── [Python runtime]   # Bundled Python and dependencies
└── [Other system files]
```

## 🚨 Troubleshooting

### Application Won't Start
- **Check**: Ensure you have at least 1GB RAM available
- **Check**: Verify 500MB+ free disk space
- **Try**: Run as administrator (Windows) or with sudo (Linux/macOS)
- **Check**: No other application is using port 7860

### Browser Doesn't Open
- **Manual**: Open browser and go to `http://127.0.0.1:7860`
- **Try**: Different browsers (Chrome, Firefox, Safari, Edge)
- **Check**: Firewall settings aren't blocking local connections

### Security Warnings
- **Windows**: "Windows protected your PC" → Click "More info" → "Run anyway"
- **macOS**: "Cannot be opened" → Right-click → "Open" → Confirm
- **Antivirus**: Add to whitelist if detected as false positive

### Performance Issues
- **Close**: Other memory-intensive applications
- **Restart**: The application if it becomes slow
- **Check**: Available system resources

## 🔄 Updates & Maintenance

### Updating the Application
1. **Backup**: Copy your `data/` folder to preserve patient information
2. **Download**: New version of the application
3. **Replace**: Old executable with new one
4. **Restore**: Your `data/` folder if needed

### Data Backup
**Important**: Regularly backup your data!

- **Full Backup**: Copy the entire application folder
- **Data Only**: Copy just the `data/` folder
- **Recommended**: Daily backups to external drive or cloud storage

## 🏥 Using W.AI.TLIST

### Core Features
- **Patient Management**: Add, edit, and organize patient records
- **Appointment Scheduling**: Create and manage dental appointments
- **Waitlist Optimization**: Automatically match patients with cancelled slots
- **Provider Management**: Manage dentist schedules and availability
- **Reports & Analytics**: Track appointment utilization and efficiency

### Getting Started
1. **First Login**: Follow the setup wizard in your browser
2. **Add Providers**: Enter your dental practitioners
3. **Import Patients**: Add patient information
4. **Schedule Appointments**: Start booking appointments
5. **Use Waitlist**: Let the system optimize cancellations

## 📞 Support

### Documentation
- **Built-in Help**: Access help system through the web interface
- **User Guide**: See `USER_GUIDE.md` for detailed instructions
- **Build Guide**: See `BUILD_INSTRUCTIONS.md` for technical details

### Common Questions
- **Q**: Can I access this from other computers?
  **A**: Currently configured for local access only for security
- **Q**: Is my data safe?
  **A**: Yes, all data is stored locally on your computer
- **Q**: Do I need internet?
  **A**: No, the application works completely offline

## 📄 License & Legal

- **License**: See `LICENSE` file for complete terms
- **Privacy**: No data collection or transmission to external servers
- **Security**: Local encryption for all sensitive data

---

### 🚀 Quick Commands

- **Start**: Double-click the executable
- **Stop**: Press `Ctrl+C` in the console window or close it
- **Access**: Open browser to `http://127.0.0.1:7860`
- **Backup**: Copy the entire application folder

---

*W.AI.TLIST v1.0.0 - Optimizing dental appointments with intelligent technology*

**Built with**: Python, Flask, SQLAlchemy, SQLite  
**Packaged with**: PyInstaller for cross-platform compatibility 