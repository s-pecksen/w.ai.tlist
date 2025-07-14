#!/usr/bin/env python3
"""
W.AI.TLIST Universal Launcher
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
import platform
from contextlib import closing
import requests
from urllib.parse import urljoin

# Add the current directory to Python path so we can import the app
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def safe_print(*args, **kwargs):
    """Safe print function that works in both console and windowed modes with proper encoding."""
    try:
        # Convert all arguments to strings and handle encoding
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                # Replace Unicode characters with ASCII-safe alternatives
                safe_str = arg.replace('🔧', '[STARTING]')
                safe_str = safe_str.replace('✅', '[OK]')
                safe_str = safe_str.replace('❌', '[ERROR]')
                safe_str = safe_str.replace('⚠', '[WARNING]')
                safe_str = safe_str.replace('🚀', '[LAUNCH]')
                safe_str = safe_str.replace('🌐', '[WEB]')
                safe_str = safe_str.replace('⏳', '[WAIT]')
                safe_str = safe_str.replace('🏥', '[APP]')
                safe_str = safe_str.replace('📋', '[INFO]')
                safe_str = safe_str.replace('⌨️', '[KEY]')
                safe_str = safe_str.replace('👋', '[STOP]')
                safe_str = safe_str.replace('🔄', '[SHUTDOWN]')
                safe_args.append(safe_str)
            else:
                safe_args.append(str(arg))
        
        # Try to print with UTF-8 encoding first
        try:
            print(*safe_args, **kwargs)
        except UnicodeEncodeError:
            # If UTF-8 fails, encode to ASCII with replacement
            ascii_args = []
            for arg in safe_args:
                if isinstance(arg, str):
                    ascii_args.append(arg.encode('ascii', 'replace').decode('ascii'))
                else:
                    ascii_args.append(str(arg))
            print(*ascii_args, **kwargs)
    except (OSError, AttributeError, UnicodeEncodeError):
        # If we can't print at all (windowed mode), just continue silently
        pass

def show_error_dialog(message):
    """Show error dialog in GUI mode if possible."""
    try:
        if platform.system() == 'Windows':
            import ctypes
            # Clean the message of any problematic characters
            clean_message = message.replace('❌', '[ERROR]').replace('🔧', '[STARTING]')
            ctypes.windll.user32.MessageBoxW(0, clean_message, "W.AI.TLIST Error", 1)
        else:
            # For other platforms, try to use desktop notifications or fallback
            safe_print(f"ERROR: {message}")
    except:
        safe_print(f"ERROR: {message}")

class WaitlystLauncher:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 7860
        self.url = f"http://{self.host}:{self.port}"
        self.flask_process = None
        self.server_thread = None
        self.running = False
        self.system = platform.system().lower()
        self.is_console_mode = self._detect_console_mode()
        
    def _detect_console_mode(self):
        """Detect if we're running in console mode or windowed mode."""
        try:
            # Try to get console info on Windows
            if self.system == 'windows':
                import ctypes
                try:
                    kernel32 = ctypes.windll.kernel32
                    # If we can get console info, we have a console
                    return kernel32.GetConsoleWindow() != 0
                except:
                    return False
            else:
                # On Unix-like systems, check if stdout is a TTY
                return sys.stdout.isatty()
        except:
            return False
    
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
                app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
            except Exception as e:
                safe_print(f"Flask server error: {e}")
                if not self.is_console_mode:
                    show_error_dialog(f"Failed to start server: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def open_browser(self):
        """Open the web browser to the application URL."""
        def try_open_browser():
            time.sleep(2)  # Give the server a moment to fully start
            
            browsers_to_try = []
            
            if self.system == 'windows':
                browsers_to_try = [
                    'windows-default',
                    'chrome',
                    'firefox',
                    'edge'
                ]
            elif self.system == 'darwin':  # macOS
                browsers_to_try = [
                    'macosx',
                    'chrome',
                    'firefox',
                    'safari'
                ]
            else:  # Linux
                browsers_to_try = [
                    'xdg-open',
                    'google-chrome',
                    'chrome',
                    'chromium',
                    'firefox'
                ]
            
            for browser_name in browsers_to_try:
                try:
                    if browser_name == 'windows-default':
                        # Use Windows default browser
                        os.startfile(self.url)
                        safe_print(f"[OK] Opened {self.url} in default browser")
                        return True
                    elif browser_name == 'xdg-open':
                        # Use Linux default browser
                        subprocess.run(['xdg-open', self.url], check=True)
                        safe_print(f"[OK] Opened {self.url} via xdg-open")
                        return True
                    else:
                        # Try specific browsers
                        browser = webbrowser.get(browser_name)
                        browser.open(self.url)
                        safe_print(f"[OK] Opened {self.url} in {browser_name}")
                        return True
                except (webbrowser.Error, OSError, subprocess.CalledProcessError):
                    continue
            
            # Fallback to default browser
            try:
                webbrowser.open(self.url)
                safe_print(f"[OK] Opened {self.url} in default browser")
                return True
            except Exception as e:
                safe_print(f"[ERROR] Failed to open browser: {e}")
                if not self.is_console_mode:
                    show_error_dialog(f"Could not open browser. Please manually navigate to {self.url}")
                return False
        
        browser_thread = threading.Thread(target=try_open_browser, daemon=True)
        browser_thread.start()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            safe_print("\n[SHUTDOWN] Shutting down gracefully...")
            self.running = False
        
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        except:
            pass  # Signal handling might not be available in all environments
    
    def shutdown(self):
        """Shutdown the application."""
        self.running = False
        safe_print("[STOP] W.AI.TLIST stopped")
    
    def print_banner(self):
        """Print the application banner."""
        if self.is_console_mode:
            banner = """
================================================================
                    W.AI.TLIST LAUNCHER                      
              Dental Appointment Optimization                
================================================================
"""
            safe_print(banner)
    
    def wait_for_user(self):
        """Wait for user input to keep the application running."""
        try:
            if self.is_console_mode:
                safe_print("\n" + "="*60)
                safe_print("[APP] W.AI.TLIST is now running!")
                safe_print(f"[WEB] Web interface: {self.url}")
                safe_print("[INFO] Use the web interface to manage your dental appointments")
                safe_print("\n[KEY] Press Ctrl+C or close this window to stop the application")
                safe_print("="*60 + "\n")
            
            # In windowed mode, just keep running in background
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def launch(self):
        """Main launch sequence."""
        try:
            self.running = True
            
            if self.is_console_mode:
                self.print_banner()
                safe_print("[LAUNCH] Starting W.AI.TLIST...")
            
            # Check if port is available, find alternative if needed
            try:
                with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
                    sock.bind((self.host, self.port))
            except OSError:
                new_port = self.find_available_port(self.port + 1)
                safe_print(f"[WARNING] Port {self.port} is busy, using port {new_port}")
                self.port = new_port
                self.url = f"http://{self.host}:{self.port}"
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Start Flask server
            safe_print("[STARTING] Starting Flask server...")
            self.start_flask_server()
            
            # Wait for server to be ready
            safe_print("[WAIT] Waiting for server to start...")
            if self.is_server_ready():
                safe_print("[OK] Server is ready!")
                
                # Open browser
                safe_print("[WEB] Opening web browser...")
                self.open_browser()
                
                # Wait for user
                self.wait_for_user()
            else:
                error_msg = "Server failed to start within timeout period"
                safe_print(f"[ERROR] {error_msg}")
                if not self.is_console_mode:
                    show_error_dialog(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error launching W.AI.TLIST: {e}"
            safe_print(f"[ERROR] {error_msg}")
            if not self.is_console_mode:
                show_error_dialog(error_msg)
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