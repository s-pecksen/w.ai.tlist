#!/usr/bin/env python3
"""
VirusTotal Submission Script for W.AI.TLIST
Submits the executable to VirusTotal for public scanning and reputation building.
"""

import os
import sys
import hashlib
import requests
import json
import time
from pathlib import Path

class VirusTotalSubmitter:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://www.virustotal.com/vtapi/v2"
        self.web_url = "https://www.virustotal.com"
        
    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of the file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_file_info(self, file_path):
        """Get file information."""
        file_path = Path(file_path)
        if not file_path.exists():
            return None
        
        stat = file_path.stat()
        return {
            'name': file_path.name,
            'size': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'sha256': self.calculate_file_hash(file_path),
            'path': str(file_path)
        }
    
    def check_existing_report(self, file_hash):
        """Check if file already exists in VirusTotal database."""
        if not self.api_key:
            return None
            
        url = f"{self.base_url}/file/report"
        params = {
            'apikey': self.api_key,
            'resource': file_hash
        }
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def submit_file(self, file_path):
        """Submit file to VirusTotal."""
        if not self.api_key:
            print("⚠️  No API key provided. Using web submission method.")
            return self.submit_via_web(file_path)
        
        url = f"{self.base_url}/file/scan"
        
        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {'apikey': self.api_key}
            
            print("📤 Uploading file to VirusTotal...")
            response = requests.post(url, files=files, data=data)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Upload failed: {response.status_code}")
                return None
    
    def submit_via_web(self, file_path):
        """Provide instructions for manual web submission."""
        file_info = self.get_file_info(file_path)
        if not file_info:
            print("❌ File not found")
            return
        
        print("🌐 Manual VirusTotal Submission Instructions:")
        print(f"   1. Go to: {self.web_url}")
        print(f"   2. Click 'Choose file' and select: {file_info['path']}")
        print(f"   3. Click 'Scan it!'")
        print(f"   4. Wait for scan results")
        print(f"   5. Share the results URL with users")
        print()
        print(f"📊 File Information:")
        print(f"   Name: {file_info['name']}")
        print(f"   Size: {file_info['size_mb']} MB")
        print(f"   SHA256: {file_info['sha256']}")
        print()
        print(f"🔗 Direct upload link: {self.web_url}/gui/home/upload")
        
        return {
            'manual_submission': True,
            'file_info': file_info,
            'upload_url': f"{self.web_url}/gui/home/upload"
        }
    
    def get_scan_results_url(self, file_hash):
        """Get VirusTotal results URL for a file hash."""
        return f"{self.web_url}/gui/file/{file_hash}"

def main():
    """Main execution function."""
    print("=" * 60)
    print("  W.AI.TLIST VirusTotal Submission Tool")
    print("=" * 60)
    print()
    
    # Find the executable
    exe_path = Path("dist/Waitlyst.exe")
    if not exe_path.exists():
        print("❌ Waitlyst.exe not found in dist/ directory")
        print("   Please run the build script first.")
        sys.exit(1)
    
    # Initialize submitter
    api_key = os.environ.get('VIRUSTOTAL_API_KEY')
    submitter = VirusTotalSubmitter(api_key)
    
    # Get file information
    file_info = submitter.get_file_info(exe_path)
    print(f"📁 Found executable: {file_info['name']}")
    print(f"📏 Size: {file_info['size_mb']} MB")
    print(f"🔑 SHA256: {file_info['sha256']}")
    print()
    
    # Check for existing report
    if api_key:
        print("🔍 Checking for existing VirusTotal report...")
        existing_report = submitter.check_existing_report(file_info['sha256'])
        
        if existing_report and existing_report.get('response_code') == 1:
            print("✅ File already scanned by VirusTotal!")
            results_url = submitter.get_scan_results_url(file_info['sha256'])
            print(f"🔗 Results: {results_url}")
            
            # Show scan summary
            total_scans = existing_report.get('total', 0)
            positives = existing_report.get('positives', 0)
            print(f"📊 Scan Results: {positives}/{total_scans} engines detected issues")
            
            if positives == 0:
                print("✅ Clean scan - no threats detected!")
            elif positives <= 2:
                print("⚠️  Minimal detections (likely false positives)")
            else:
                print("❌ Multiple detections - please investigate")
            
            return
    
    # Submit file
    print("🚀 Submitting to VirusTotal...")
    result = submitter.submit_file(exe_path)
    
    if result:
        if result.get('manual_submission'):
            print("✅ Manual submission instructions provided above")
        else:
            print("✅ File submitted successfully!")
            if 'permalink' in result:
                print(f"🔗 Track progress: {result['permalink']}")
            print("⏳ Scan results will be available in 5-10 minutes")
    else:
        print("❌ Submission failed")
    
    print()
    print("📋 Next Steps:")
    print("   1. Wait for scan completion")
    print("   2. Review results for false positives")
    print("   3. Include VirusTotal link in your distribution")
    print("   4. Regular submissions help build reputation")
    print()
    print("💡 Tip: Get a free VirusTotal API key at:")
    print("   https://www.virustotal.com/gui/join-us")

if __name__ == "__main__":
    main() 