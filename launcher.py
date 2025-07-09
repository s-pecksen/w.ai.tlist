#!/usr/bin/env python3
"""
W.AI.TLIST Application Launcher
Cross-platform launcher that starts the Flask app and opens it in the browser.
"""

import os
import sys
import time
import threading
import webbrowser
import socket
import subprocess
import signal
from contextlib import closing
import requests
from urllib.parse import urljoin

# Add the current directory to Python path so we can import the app
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

class WaitlystLauncher:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 7860
        self.url = f"http://{self.host}:{self.port}"
        self.flask_process = None
        self.server_thread = None
        self.running = False
        
    def find_available_port(self, start_port=7860):
        """Find an available port starting from the given port."""
        for port in range(start_port, start_port + 100):
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                try:
                    sock.bind((self.host, port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No available ports found")
    
    def is_server_ready(self, timeout=30):
        """Check if the Flask server is ready by making a request."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(self.url, timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False
    
    def start_flask_server(self):
        """Start the Flask server in a separate thread."""
        def run_server():
            try:
                # Import and run the Flask app
                from app import app
                # Disable Flask's debug mode and reloader for production
                app.run(host=self.host, port=self.port, debug=False, use_reloader=False, threaded=True)
            except Exception as e:
                print(f"Error starting Flask server: {e}")
                self.running = False
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
    
    def open_browser(self):
        """Open the application in the default browser, preferring Chrome."""
        browsers_to_try = [
            # Chrome variants
            'google-chrome',
            'chrome',
            'chromium',
            'chromium-browser',
            # Chrome on Windows
            'C:/Program Files/Google/Chrome/Application/chrome.exe',
            'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
            # Chrome on macOS
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            # Fallback to default browser
            None
        ]
        
        browser_opened = False
        for browser in browsers_to_try:
            try:
                if browser is None:
                    # Use default browser
                    webbrowser.open(self.url)
                    print(f"✓ Opened application in default browser: {self.url}")
                    browser_opened = True
                    break
                elif os.path.exists(browser) if browser.startswith('/') or browser.startswith('C:') else True:
                    # Try to register and use specific browser
                    if browser.startswith('/') or browser.startswith('C:'):
                        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(browser))
                        controller = webbrowser.get('chrome')
                    else:
                        controller = webbrowser.get(browser)
                    controller.open(self.url)
                    print(f"✓ Opened application in Chrome: {self.url}")
                    browser_opened = True
                    break
            except (webbrowser.Error, OSError):
                continue
        
        if not browser_opened:
            print(f"⚠ Could not open browser automatically. Please visit: {self.url}")
        
        return browser_opened
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print("\n⏹ Shutting down W.AI.TLIST...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """Gracefully shutdown the application."""
        self.running = False
        if self.flask_process:
            self.flask_process.terminate()
        print("✓ W.AI.TLIST has been shut down")
    
    def print_banner(self):
        """Print the application banner."""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                    W.AI.TLIST LAUNCHER                      ║
║              Dental Appointment Optimization                ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    def wait_for_user(self):
        """Wait for user input to keep the application running."""
        try:
            print("\n" + "="*60)
            print("🏥 W.AI.TLIST is now running!")
            print(f"🌐 Web interface: {self.url}")
            print("📋 Use the web interface to manage your dental appointments")
            print("\n⌨️  Press Ctrl+C or close this window to stop the application")
            print("="*60 + "\n")
            
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def launch(self):
        """Main launch sequence."""
        try:
            self.print_banner()
            
            print("🚀 Starting W.AI.TLIST...")
            
            # Check if port is available, find alternative if needed
            try:
                with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                    sock.bind((self.host, self.port))
            except OSError:
                new_port = self.find_available_port(self.port + 1)
                print(f"⚠ Port {self.port} is busy, using port {new_port}")
                self.port = new_port
                self.url = f"http://{self.host}:{self.port}"
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Start Flask server
            print("🔧 Starting Flask server...")
            self.start_flask_server()
            
            # Wait for server to be ready
            print("⏳ Waiting for server to start...")
            if self.is_server_ready():
                print("✅ Server is ready!")
                
                # Open browser
                print("🌐 Opening web browser...")
                self.open_browser()
                
                # Wait for user
                self.wait_for_user()
            else:
                print("❌ Server failed to start within timeout period")
                return False
                
        except Exception as e:
            print(f"❌ Error launching W.AI.TLIST: {e}")
            return False
        finally:
            self.shutdown()
        
        return True

def main():
    """Main entry point."""
    launcher = WaitlystLauncher()
    success = launcher.launch()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 