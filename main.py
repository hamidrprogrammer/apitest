import os
import time
import uuid
import json
import requests
import win32print
import win32api
import firebase_admin
from firebase_admin import credentials, db
import customtkinter as ctk
from tkinter import messagebox
import threading
import queue
import socket
import platform
import logging
from concurrent.futures import ThreadPoolExecutor
import pystray
from PIL import Image
import sys
import subprocess

sumatra_path = os.path.join(os.path.dirname(__file__), "SumatraPDF.exe")
# Configure logging for detailed event tracking
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("printer_app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# ------------------ Firebase Initialization ------------------
def init_firebase():
    """Initialize Firebase connection using service account credentials."""
    try:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        cred_path = os.getenv("FIREBASE_CRED_PATH", os.path.join(base_path, "admin-panel-printer-firebase.json"))
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://admin-panel-printer-default-rtdb.europe-west1.firebasedatabase.app"
        })
        logging.info("Firebase initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Firebase: {e}")
        raise

# ------------------ Printer Management ------------------
def get_printers():
    """Retrieve list of installed printers (local and network)."""
    try:
        printers_local = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
        printers_network = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_NETWORK)]
        printers = list(set(printers_local + printers_network))
        if not printers:
            logging.warning("No printers found.")
        return printers
    except Exception as e:
        logging.error(f"Error retrieving printers: {e}")
        return []

def update_printer_list(user_id):
    """Update printer list in Firebase and return it."""
    try:
        printers = get_printers()
        users_ref = db.reference("users")
        user_snapshot = users_ref.order_by_child("token").equal_to(user_id).get()
        if not user_snapshot:
            logging.error(f"No user found with token: {user_id}")
            return []
        user_info = next(iter(user_snapshot.values()))
        user = user_info['id']
        db.reference(f"users/{user}/printers").set(printers)
        logging.info(f"Printer list updated for user {user_id}.")
        return printers
    except Exception as e:
        logging.error(f"Error updating printer list: {e}")
        return []

def update_connection_status(user_id, status):
    """Update device connection status in Firebase."""
    try:
        users_ref = db.reference("users")
        user_snapshot = users_ref.order_by_child("token").equal_to(user_id).get()
        user_info = next(iter(user_snapshot.values()))
        user = user_info['id']
        db.reference(f"users/{user}").update({"connected": status})
        logging.info(f"Connection status for user {user_id} set to {status}.")
    except Exception as e:
        logging.error(f"Error updating connection status: {e}")
       

# ------------------ File Download and Printing ------------------
def load_config():
    """Load configuration from config.json."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise

def download_file(url, save_path, progress_callback, timeout=30):
    """Download a file from a URL with progress tracking."""
    try:
      
        headers = {
            "Accept": "application/pdf",
           
        }
        response = requests.get(url, headers=headers, stream=True, timeout=timeout)
        if response.status_code != 200:
            raise Exception(f"Download failed with status code: {response.status_code}")
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress_callback(downloaded / total_size)
        logging.info(f"File downloaded successfully: {save_path}")
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
        raise

def download_pdf_from_url(file_url, file_key, progress_callback, dest_dir="downloads"):
    """Download a PDF file based on file_key."""
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        local_file = os.path.join(os.path.abspath(dest_dir), f"{file_key}.pdf")
        download_file(file_url, local_file, progress_callback)
        return local_file
    except Exception as e:
        logging.error(f"Error downloading PDF: {e}")
        raise

def print_pdf(settings, file_path):
    """Print a PDF file with specified printer settings."""
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return False
    return auto_print_pdf(file_path, settings)

def auto_print_pdf(file_path, settings):
    """Automatically print a PDF with optional DEVMODE settings."""
    printer_name = settings.get("namePrinter", win32print.GetDefaultPrinter())
    COOMEND = f"{settings.get("colorMode")},{settings.get("orientation")},paper={settings.get("paperSize")},"
    try:
        if not os.path.exists(sumatra_path):
            raise FileNotFoundError("SumatraPDF not found")

        subprocess.run([
    sumatra_path,
    "-print-to", printer_name,
    "-silent",
    "-print-settings", COOMEND,
    file_path
], check=True)
        logging.info(f"پرینت موفق برای {file_path} روی {printer_name}")
        return True
    except Exception as e:
        logging.error(f"خطا هنگام پرینت: {e}")
        return False

    except Exception as e:
        logging.error(f"Error during printing: {e}")
        return False

# ------------------ Token Management ------------------
def save_token(token):
    """Save token to a local file."""
    try:
        with open("token.txt", "w") as f:
            f.write(token)
        logging.info("Token saved successfully.")
    except Exception as e:
        logging.error(f"Error saving token: {e}")

def load_token():
    """Load token from a local file."""
    try:
        if os.path.exists("token.txt"):
            with open("token.txt", "r") as f:
                return f.read().strip()
        return None
    except Exception as e:
        logging.error(f"Error loading token: {e}")
        return None

# ------------------ System Information ------------------
def get_system_info():
    """Collect system information including IP and geolocation."""
    try:
        public_ip = requests.get("https://api.ipify.org", timeout=5).text
        location_data = requests.get(f"https://ipinfo.io/{public_ip}/json", timeout=5).json()
    except Exception as e:
        logging.error(f"Error retrieving IP or location: {e}")
        public_ip = "Unknown"
        location_data = {}
    return {
        "hostname": socket.gethostname(),
        "ip": socket.gethostbyname(socket.gethostname()),
        "public_ip": public_ip,
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "uuid": str(uuid.uuid1()),
        "location": {
            "city": location_data.get("city", "Unknown"),
            "region": location_data.get("region", "Unknown"),
            "country": location_data.get("country", "Unknown"),
            "loc": location_data.get("loc", "Unknown"),
            "org": location_data.get("org", "Unknown"),
            "timezone": location_data.get("timezone", "Unknown")
        }
    }

def upload_system_info(user_id):
    """Upload system information to Firebase for support."""
    try:
        system_info = get_system_info()
        users_ref = db.reference("users")
        user_snapshot = users_ref.order_by_child("token").equal_to(user_id).get()
        user_info = next(iter(user_snapshot.values()))
        user = user_info['id']
        
        db.reference(f"users/{user}/system_info").set(system_info)
        logging.info(f"System info uploaded for user {user_id}.")
    except Exception as e:
        logging.error(f"Error uploading system info: {e}")

# ------------------ System Tray Management ------------------
def create_system_tray(app):
    """Create a system tray icon for background execution."""
    def on_show():
        app.deiconify()
        app.lift()

    def on_exit():
        app.quit_app()

    menu = pystray.Menu(
        pystray.MenuItem("Show App", on_show),
        pystray.MenuItem("Exit", on_exit)
    )
    icon_image = Image.new("RGB", (64, 64), color="blue")
    icon = pystray.Icon("PrinterSync", icon_image, "PrinterSync Pro", menu)
    return icon

# ------------------ GUI Application ------------------
class PrinterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.update_queue = queue.Queue()
        self.printers = []
        self.jobs = {}
        self.user_id = None
        self.icon = None
        self.listener = None

        # Window setup
        self.title("PrinterSync Pro")
        self.geometry("1000x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.minsize(800, 600)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#1a1a1a")
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="PrinterSync Pro",
            font=("Helvetica", 32, "bold"),
            text_color="#4CAF50"
        )
        self.title_label.pack(pady=10)

        # Token input
        self.token_frame = ctk.CTkFrame(self, corner_radius=15)
        self.token_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.token_label = ctk.CTkLabel(
            self.token_frame,
            text="Enter Connection Token:",
            font=("Helvetica", 16)
        )
        self.token_label.pack(pady=5)
        self.token_entry = ctk.CTkEntry(
            self.token_frame,
            width=500,
            placeholder_text="Paste your token here",
            font=("Helvetica", 14),
            corner_radius=10
        )
        self.token_entry.pack(pady=5)
        self.submit_button = ctk.CTkButton(
            self.token_frame,
            text="Connect",
            command=self.on_connect,
            width=200,
            height=40,
            corner_radius=20,
            fg_color="#4CAF50",
            hover_color="#45A049"
        )
        self.submit_button.pack(pady=10)

        # Connection status
        self.status_frame = ctk.CTkFrame(self, corner_radius=10)
        self.status_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Disconnected",
            text_color="red",
            font=("Helvetica", 14)
        )
        self.status_label.pack(pady=5)

        # Main content
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure((0, 1), weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_remove()

        # Printers section
        self.printers_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.printers_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.printers_label = ctk.CTkLabel(
            self.printers_frame,
            text="Available Printers",
            font=("Helvetica", 18, "bold")
        )
        self.printers_label.pack(pady=5)
        self.printers_list = ctk.CTkScrollableFrame(self.printers_frame, height=150)
        self.printers_list.pack(fill="both", expand=True, padx=10, pady=5)
        self.refresh_button = ctk.CTkButton(
            self.printers_frame,
            text="Refresh Printers",
            command=self.refresh_printers,
            corner_radius=10,
            fg_color="#2196F3",
            hover_color="#1976D2"
        )
        self.refresh_button.pack(pady=5)

        # Print jobs section
        self.jobs_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.jobs_frame.grid(row=1, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")
        self.jobs_label = ctk.CTkLabel(
            self.jobs_frame,
            text="Print Jobs",
            font=("Helvetica", 18, "bold")
        )
        self.jobs_label.pack(pady=5)
        self.jobs_table = ctk.CTkFrame(self.jobs_frame)
        self.jobs_table.pack(fill="both", expand=True, padx=10, pady=5)

        # Log section
        self.log_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.log_frame.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")
        self.log_label = ctk.CTkLabel(
            self.log_frame,
            text="Event Log",
            font=("Helvetica", 18, "bold")
        )
        self.log_label.pack(pady=5)
        self.log_textbox = ctk.CTkTextbox(self.log_frame, height=300, font=("Helvetica", 12))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=5)

        # System tray setup
        self.icon = create_system_tray(self)
        threading.Thread(target=self.icon.run, daemon=True).start()

        # Event handlers
        self.protocol("WM_DELETE_WINDOW", self.on_minimize)
        self.after(100, self.check_update_queue)

        # Load token
        token = load_token()
        if token:
            self.token_entry.insert(0, token)
            self.on_connect()

    def check_update_queue(self):
     """Update UI based on queued messages."""
     while not self.update_queue.empty():
        message = self.update_queue.get()
        if message['type'] == 'log':
            self.log_textbox.insert("end", message['message'] + "\n")
            self.log_textbox.see("end")
        elif message['type'] == 'progress':
            progress_bar = message['progress_bar']
            try:
                if progress_bar.winfo_exists():  # Only update if the widget exists
                    progress_bar.set(message['value'])
            except Exception as e:
                print(f"Error updating progress bar: {e}")
     self.after(100, self.check_update_queue)

    def on_connect(self):
        """Validate token and initiate connection."""
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Error", "Please enter a valid token!")
            return
        threading.Thread(target=self.connect_to_printer, args=(token,), daemon=True).start()

    def connect_to_printer(self, token):
        """Connect to Firebase and start processing jobs."""
        try:
            users_ref = db.reference("users")
            user_snapshot = users_ref.order_by_child("token").equal_to(token).get()
            if not user_snapshot:
                self.after(0, lambda: messagebox.showerror("Error", "Invalid token!"))
                return
            user_info = next(iter(user_snapshot.values()))
            self.user_id = token;
            update_connection_status(self.user_id, True)
            upload_system_info(self.user_id)
            self.printers = update_printer_list(self.user_id)
            self.after(0, self.update_ui_after_connect)
            save_token(token)
            self.listenerUpdate = db.reference(f"users").listen(self.check_connection_status)

            self.listener = db.reference(f"print_jobs/{self.user_id}").listen(self.print_jobs_callback)
        except Exception as e:
            self.update_queue.put({'type': 'log', 'message': f"Connection error: {e}"})

    def update_ui_after_connect(self):
        """Update UI after successful connection."""
        self.status_label.configure(text="Connected", text_color="green")
        self.main_frame.grid()
        self.display_printers(self.printers)
        self.update_queue.put({'type': 'log', 'message': "Connected successfully."})

    def display_printers(self, printers):
        """Display list of printers in UI."""
        for widget in self.printers_list.winfo_children():
            widget.destroy()
        for printer in printers:
            frame = ctk.CTkFrame(self.printers_list, corner_radius=5)
            frame.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(
                frame,
                text=printer,
                font=("Helvetica", 12),
                text_color="#E0E0E0"
            ).pack(side="left", padx=10)
            ctk.CTkLabel(
                frame,
                text="Online",
                font=("Helvetica", 10),
                text_color="green"
            ).pack(side="right", padx=10)

    def refresh_printers(self):
        """Refresh the printer list."""
        if self.user_id:
            self.printers = update_printer_list(self.user_id)
            self.display_printers(self.printers)
            self.update_queue.put({'type': 'log', 'message': "Printer list refreshed."})
    def check_connection_status(self, event):
     print("check_connection_status")
     """Update device connection status in Firebase."""
     try:
        users_ref = db.reference("users")
        user_snapshot = users_ref.order_by_child("token").equal_to(self.user_id).get()
        if not user_snapshot:
                save_token('')
                self.status_label.configure(text="Disconnected", text_color="red")
                self.after(0, lambda: messagebox.showerror("Error", "Invalid token!"))
                return
     except Exception as e:
        logging.error(f"Error updating connection status: {e}") 
    def print_jobs_callback(self, event):
        """Handle print job updates from Firebase."""
        jobs_ref = db.reference(f"print_jobs/{self.user_id}")
        jobs = jobs_ref.get()
        if not jobs:
            return
        if jobs:
            self.jobs = jobs
            
            self.update_queue.put({'type': 'print_jobs', 'jobs': self.jobs})
            for job_id, job in self.jobs.items():
                if job.get("status") == "pending":
                    threading.Thread(
                        target=self.process_single_job,
                        args=(job_id, job),
                        daemon=True
                    ).start()

    def process_single_job(self, job_id, job):
     """Process a single print job with progress bar."""
     print("process_single_job")
     log = lambda msg: self.update_queue.put({'type': 'log', 'message': msg})
     progress_bar = None
     progress_bar_valid = True  # Flag to track if progress bar is still valid

     try:
        # Create progress bar
        progress_bar = ctk.CTkProgressBar(self.jobs_table, mode="determinate")
        progress_bar.grid(
            row=self.jobs_table.grid_size()[1] + 1,
            column=0,
            columnspan=5,
            padx=5,
            pady=5,
            sticky="ew"
        )
        progress_bar.set(0)

        def update_progress(value):
            if progress_bar_valid:
                self.update_queue.put({
                    'type': 'progress',
                    'progress_bar': progress_bar,
                    'value': value
                })

        # Download and print
        local_file = download_pdf_from_url(
            job.get("file_url"),
            job.get("file_key"),
            update_progress
        )
        success = print_pdf(job, local_file)

        # Update job status in Firebase
        db.reference(f"print_jobs/{self.user_id}/{job_id}").update({
            "status": "completed" if success else "failed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })
        log(f"Print job {job_id} {'completed' if success else 'failed'}.")

     except Exception as e:
        log(f"Error processing job {job_id}: {e}")
        db.reference(f"print_jobs/{self.user_id}/{job_id}").update({
            "status": "failed",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

     finally:
        # Clean up progress bar
        if progress_bar:
            progress_bar_valid = False  # Prevent further updates
            self.after(1000, lambda: self.cleanup_progress_bar(progress_bar))

    def cleanup_progress_bar(self, progress_bar):
     """Safely remove and destroy a progress bar."""
     try:
        if progress_bar.winfo_exists():  # Check if widget still exists
            progress_bar.grid_remove()  # Remove from grid
            progress_bar.destroy()  # Destroy widget
     except Exception as e:
        logging.error(f"Error cleaning up progress bar: {e}")
    def update_print_jobs_ui(self, jobs):
        """Update the print jobs table in UI."""
        for widget in self.jobs_table.winfo_children():
            widget.destroy()
        headers = ["Job ID", "Printer", "Status", "Timestamp", "Action"]
        for col, header in enumerate(headers):
            ctk.CTkLabel(
                self.jobs_table,
                text=header,
                font=("Helvetica", 12, "bold"),
                text_color="#FFFFFF"
            ).grid(row=0, column=col, padx=5, pady=5, sticky="w")
        if jobs and isinstance(jobs, dict):
            for i, (job_id, job) in enumerate(jobs.items(), start=1):
                ctk.CTkLabel(
                    self.jobs_table,
                    text=job_id,
                    font=("Helvetica", 12)
                ).grid(row=i, column=0, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(
                    self.jobs_table,
                    text=job.get('namePrinter', 'N/A'),
                    font=("Helvetica", 12)
                ).grid(row=i, column=1, padx=5, pady=5, sticky="w")
                status = job.get('status', 'N/A')
                status_color = {
                    "completed": "green",
                    "failed": "red",
                    "pending": "yellow",
                    "canceled": "gray"
                }.get(status, "white")
                ctk.CTkLabel(
                    self.jobs_table,
                    text=status.capitalize(),
                    font=("Helvetica", 12),
                    text_color=status_color
                ).grid(row=i, column=2, padx=5, pady=5, sticky="w")
                ctk.CTkLabel(
                    self.jobs_table,
                    text=job.get('timestamp', 'N/A'),
                    font=("Helvetica", 12)
                ).grid(row=i, column=3, padx=5, pady=5, sticky="w")
                if status == "pending":
                    cancel_btn = ctk.CTkButton(
                        self.jobs_table,
                        text="Cancel",
                        command=lambda j=job_id: self.cancel_job(j),
                        width=80,
                        corner_radius=10,
                        fg_color="#F44336",
                        hover_color="#D32F2F"
                    )
                    cancel_btn.grid(row=i, column=4, padx=5, pady=5)
        else:
            ctk.CTkLabel(
                self.jobs_table,
                text="No active print jobs",
                font=("Helvetica", 12)
            ).grid(row=1, column=0, columnspan=5, padx=5, pady=5)

    def cancel_job(self, job_id):
        """Cancel a print job."""
        try:
            db.reference(f"print_jobs/{self.user_id}/{job_id}").update({
                "status": "canceled",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            self.update_queue.put({'type': 'log', 'message': f"Print job {job_id} canceled."})
        except Exception as e:
            self.update_queue.put({'type': 'log', 'message': f"Error canceling job {job_id}: {e}"})

    def on_minimize(self):
        """Minimize to system tray instead of closing."""
        self.withdraw()
        self.update_queue.put({'type': 'log', 'message': "Application minimized to system tray."})

    def quit_app(self):
        """Cleanly exit the application."""
        self.stop_event.set()
        if self.listener:
            self.listener.close()
        if self.user_id:
            update_connection_status(self.user_id, False)
        if self.icon:
            self.icon.stop()
        self.destroy()

# ------------------ Main Execution ------------------
if __name__ == "__main__":
    init_firebase()
    app = PrinterApp()
    app.mainloop()