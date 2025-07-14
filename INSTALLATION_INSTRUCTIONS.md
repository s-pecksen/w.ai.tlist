# W.AI.TLIST Installation Instructions

## Windows Security Warning - This is Normal!

When you first run `Waitlyst.exe`, Windows may show a security warning like:
**"Windows protected your PC"** or **"Microsoft Defender SmartScreen prevented an unrecognized app from starting"**

**This is completely normal and safe.** Here's why this happens and how to proceed:

## Why This Warning Appears

- Windows shows this warning for **all new/unsigned software**
- Our application is safe but doesn't yet have an expensive digital signature
- This is the same warning you'd see for many legitimate programs
- It's Windows being extra cautious, not detecting actual malware

## How to Install Safely

### Method 1: Run Anyway (Recommended)
1. **Click "More info"** on the warning dialog
2. **Click "Run anyway"** button that appears
3. The application will start normally
4. Windows will remember your choice for future runs

### Method 2: Temporary Disable (Advanced Users)
1. Open Windows Security (Windows Defender)
2. Go to App & browser control
3. Click "Reputation-based protection settings"
4. Temporarily turn off "Check apps and files"
5. Run the application
6. **Remember to turn protection back on**

## Verifying Safety

You can verify our application is safe by:

### 1. VirusTotal Scan
- Visit [VirusTotal.com](https://www.virustotal.com)
- Upload `Waitlyst.exe` for scanning
- View results from 70+ antivirus engines
- Should show 0 or minimal false positives

### 2. File Properties
- Right-click `Waitlyst.exe` → Properties
- Check file size and creation date match our release
- Verify it was downloaded from our official source

### 3. Digital Signature (Future)
- We're working on obtaining a digital certificate
- This will eliminate the warning completely
- Future versions will be digitally signed

## Installation Steps

1. **Download** `Waitlyst.exe` from our official source
2. **Save** to a permanent location (e.g., `C:\Program Files\Waitlyst\`)
3. **Right-click** → "Run as administrator" (recommended)
4. **Follow the security warning steps** above
5. **Allow** through Windows Firewall if prompted
6. **Wait** for the application to start (may take 30-60 seconds first time)
7. **Browser** will open automatically to the application

## Troubleshooting

### Application Won't Start
- Check Windows Event Viewer for error details
- Ensure you have administrator privileges
- Try running from Command Prompt to see error messages
- Check antivirus software hasn't quarantined the file

### Browser Doesn't Open
- Manually navigate to: `http://localhost:7860`
- Try different browsers (Chrome, Firefox, Edge)
- Check Windows Firewall settings
- Ensure port 7860 isn't blocked

### Performance Issues
- Close other applications to free memory
- Check system requirements (Windows 10/11, 4GB RAM minimum)
- Run antivirus scan to rule out system issues

## System Requirements

- **Operating System:** Windows 10 or Windows 11
- **Architecture:** 64-bit (x86_64)
- **Memory:** 4GB RAM minimum, 8GB recommended
- **Storage:** 100MB free space
- **Network:** Internet connection required for full functionality

## Support & Contact

- **GitHub Issues:** [Your GitHub repository]
- **Email:** [Your support email]
- **Documentation:** See included README files

## Security Statement

- **No malware:** This application contains no viruses or malicious code
- **No data collection:** We don't collect or transmit personal data without consent
- **Open source:** Source code is available for inspection
- **Local operation:** Application runs entirely on your computer
- **Privacy focused:** Your data stays on your machine

## Why We're Not Yet Signed

Digital code signing certificates cost $85-$800/year and require:
- Business verification process (1-2 weeks)
- Legal entity registration
- Significant ongoing costs

We're working toward obtaining signing certificates as our user base grows. Until then:
- The warning is cosmetic only
- Your application is completely safe
- Functionality is identical to signed versions

---

**Thank you for your understanding and for using W.AI.TLIST!**

*For technical users: This executable was built with PyInstaller and contains the Python runtime and all dependencies bundled together, which is why some antivirus engines may flag it as suspicious.* 