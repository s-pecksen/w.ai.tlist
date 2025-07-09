# W.AI.TLIST - User Guide

Welcome to W.AI.TLIST, your intelligent dental appointment management system!

## Quick Start

### 🚀 Running the Application

1. **Download and Extract**: Unzip the W.AI.TLIST folder to your desktop or preferred location

2. **Run the Application**:
   - **Windows**: Double-click `Waitlyst.exe`
   - **Linux**: Double-click `Waitlyst` or run `./Waitlyst` in terminal
   - **macOS**: Double-click `Waitlyst` (see macOS notes below)

3. **First Time Setup**: The application will:
   - Start the dental management system
   - Automatically open your web browser to the application
   - Show a welcome screen in your browser

4. **Access the Application**: Your browser will open to `http://127.0.0.1:7860`

### 🖥️ What Happens When You Start

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

## Platform-Specific Instructions

### 🪟 Windows Users

1. **First Time Running**: Windows may show a security warning
   - Click "More info" → "Run anyway"
   - This is normal for new applications

2. **Running**: Simply double-click `Waitlyst.exe`

3. **Stopping**: 
   - Close the browser tab (optional)
   - Press `Ctrl+C` in the console window
   - Or close the console window

### 🐧 Linux Users

1. **Make Executable** (if needed):
   ```bash
   chmod +x Waitlyst
   ```

2. **Running**:
   ```bash
   ./Waitlyst
   ```
   Or double-click in file manager

3. **Stopping**: Press `Ctrl+C` in the terminal

### 🍎 macOS Users

1. **First Time Running**: macOS may block the application
   - Right-click the `Waitlyst` file
   - Select "Open"
   - Click "Open" in the security dialog
   
   **OR**
   - Go to System Preferences → Security & Privacy
   - Click "Allow" next to the blocked application

2. **Subsequent Runs**: Double-click `Waitlyst`

3. **Stopping**: Press `Cmd+C` in the terminal

## Using the Web Interface

### 🏥 Main Features

Once the application opens in your browser, you can:

- **Patient Management**: Add, edit, and manage patient information
- **Appointment Scheduling**: Schedule and manage dental appointments
- **Waitlist Management**: Optimize appointment utilization with intelligent patient matching
- **Provider Management**: Manage dental practitioners and their schedules
- **Reports**: Generate reports on appointment utilization and patient flow

### 🔐 Login and Security

- The application uses secure, encrypted sessions
- Data is stored locally in a SQLite database
- No data is transmitted to external servers

### 💾 Data Storage

- All data is stored locally on your computer
- Database location: `data/` folder within the application directory
- Automatic backups are recommended for production use

## Troubleshooting

### ❌ Application Won't Start

**Problem**: Console shows errors or closes immediately
**Solutions**:
1. Ensure no other application is using port 7860
2. Check that you have sufficient disk space
3. Try running as administrator (Windows) or with sudo (Linux/macOS)
4. Check antivirus software isn't blocking the application

### 🌐 Browser Doesn't Open

**Problem**: Application starts but browser doesn't open automatically
**Solutions**:
1. Manually open your browser and go to: `http://127.0.0.1:7860`
2. Try a different browser (Chrome, Firefox, Safari, Edge)
3. Check if your firewall is blocking the connection

### 🔒 Security Warnings

**Problem**: Windows/macOS shows security warnings
**Solutions**:
1. **Windows**: Click "More info" → "Run anyway"
2. **macOS**: Right-click → "Open" → Confirm
3. **Antivirus**: Add the application to your antivirus whitelist

### 🐌 Slow Performance

**Problem**: Application loads slowly
**Solutions**:
1. Close other applications to free up memory
2. Ensure you have at least 1GB free RAM
3. Check available disk space
4. Restart the application

### 📱 Can't Access from Other Devices

**Problem**: Want to access the application from tablets/phones on the same network
**Note**: The application is configured for local access only for security. To enable network access, contact your system administrator.

## Getting Help

### 📞 Support Contacts

- **Technical Issues**: Check the troubleshooting section above
- **Feature Requests**: Document your needs for future updates
- **Training**: Refer to the built-in help system in the web interface

### 🔄 Updates

- Check for application updates periodically
- Backup your data before installing updates
- New versions will include bug fixes and feature improvements

### 🗂️ Data Backup

**Important**: Regularly backup your data!

1. **Manual Backup**: Copy the entire application folder
2. **Data Only**: Copy the `data/` folder
3. **Recommended**: Daily backups to a separate drive or cloud storage

## System Requirements

### Minimum Requirements
- **RAM**: 1GB available memory
- **Storage**: 500MB free disk space
- **Network**: Local network access for browser connectivity
- **Browser**: Any modern web browser (Chrome, Firefox, Safari, Edge)

### Recommended Setup
- **RAM**: 2GB+ available memory
- **Storage**: 1GB+ free disk space
- **Browser**: Google Chrome (for best compatibility)
- **Backup**: Regular data backup solution

---

**Need Help?** The application includes built-in help documentation accessible through the web interface menu.

**Version**: 1.0.0  
**Last Updated**: 2024

---

*W.AI.TLIST - Optimizing dental appointments with intelligent technology* 