import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import os
import time
from urllib.parse import urlparse
import json
from datetime import datetime
import ftplib
from urllib.request import urlopen
import urllib.error

class DownloadManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Download Manager")
        self.root.geometry("900x700")
        
        # Download data
        self.downloads = {}
        self.download_history = []
        self.download_counter = 0
        
        # Default download directory
        self.download_dir = os.path.expanduser("~/Downloads")
        
        # Connection settings
        self.settings = {
            'timeout': 30,
            'max_retries': 4,
            'chunk_size': 8192,
            'max_connections': 5,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'default_protocol': 'https',
            'verify_ssl': True,
            'proxy_enabled': False,
            'proxy_host': '',
            'proxy_port': '',
            'ftp_passive': True
        }
        
        self.create_widgets()
        self.load_history()
        self.load_settings()
        
    def create_widgets(self):
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Downloads tab
        self.downloads_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.downloads_frame, text='Downloads')
        
        # Settings tab
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text='Settings')
        
        self.create_downloads_tab()
        self.create_settings_tab()
        
    def create_downloads_tab(self):
        main_frame = ttk.Frame(self.downloads_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # URL input frame
        url_frame = ttk.Frame(main_frame)
        url_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky=tk.W)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, padx=(5, 0), sticky=(tk.W, tk.E))
        
        # Protocol selection
        ttk.Label(url_frame, text="Protocol:").grid(row=0, column=2, padx=(10, 5), sticky=tk.W)
        self.protocol_var = tk.StringVar(value=self.settings['default_protocol'])
        protocol_combo = ttk.Combobox(url_frame, textvariable=self.protocol_var, 
                                    values=['http', 'https', 'ftp'], width=8, state='readonly')
        protocol_combo.grid(row=0, column=3, padx=(0, 5))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(buttons_frame, text="Add Download", command=self.add_download).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(buttons_frame, text="Choose Directory", command=self.choose_directory).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(buttons_frame, text="Clear Completed", command=self.clear_completed).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(buttons_frame, text="Test Connection", command=self.test_connection).grid(row=0, column=3, padx=(0, 5))
        
        # Directory label
        self.dir_label = ttk.Label(main_frame, text=f"Download Directory: {self.download_dir}")
        self.dir_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Downloads treeview
        self.tree = ttk.Treeview(main_frame, columns=('filename', 'protocol', 'size', 'progress', 'speed', 'status'), show='headings', height=12)
        self.tree.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Treeview headings
        self.tree.heading('filename', text='Filename')
        self.tree.heading('protocol', text='Protocol')
        self.tree.heading('size', text='Size')
        self.tree.heading('progress', text='Progress')
        self.tree.heading('speed', text='Speed')
        self.tree.heading('status', text='Status')
        
        # Column widths
        self.tree.column('filename', width=200)
        self.tree.column('protocol', width=80)
        self.tree.column('size', width=100)
        self.tree.column('progress', width=100)
        self.tree.column('speed', width=100)
        self.tree.column('status', width=120)
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=4, column=2, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Pause", command=self.pause_download).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(control_frame, text="Resume", command=self.resume_download).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(control_frame, text="Cancel", command=self.cancel_download).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(control_frame, text="Retry", command=self.retry_download).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(control_frame, text="Open File", command=self.open_file).grid(row=0, column=4, padx=(5, 0))
        
        # Configure grid weights
        self.downloads_frame.columnconfigure(0, weight=1)
        self.downloads_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        url_frame.columnconfigure(1, weight=1)
        
    def create_settings_tab(self):
        settings_main = ttk.Frame(self.settings_frame, padding="10")
        settings_main.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Connection Settings
        conn_frame = ttk.LabelFrame(settings_main, text="Connection Settings", padding="10")
        conn_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(conn_frame, text="Timeout (seconds):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.timeout_var = tk.StringVar(value=str(self.settings['timeout']))
        ttk.Entry(conn_frame, textvariable=self.timeout_var, width=10).grid(row=0, column=1, padx=(5, 0), sticky=tk.W)
        
        ttk.Label(conn_frame, text="Max Retries:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.retries_var = tk.StringVar(value=str(self.settings['max_retries']))
        ttk.Entry(conn_frame, textvariable=self.retries_var, width=10).grid(row=1, column=1, padx=(5, 0), sticky=tk.W)
        
        ttk.Label(conn_frame, text="Chunk Size (bytes):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.chunk_var = tk.StringVar(value=str(self.settings['chunk_size']))
        ttk.Entry(conn_frame, textvariable=self.chunk_var, width=10).grid(row=2, column=1, padx=(5, 0), sticky=tk.W)
        
        ttk.Label(conn_frame, text="Default Protocol:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.default_protocol_var = tk.StringVar(value=self.settings['default_protocol'])
        ttk.Combobox(conn_frame, textvariable=self.default_protocol_var, 
                    values=['http', 'https', 'ftp'], width=10, state='readonly').grid(row=3, column=1, padx=(5, 0), sticky=tk.W)
        
        self.verify_ssl_var = tk.BooleanVar(value=self.settings['verify_ssl'])
        ttk.Checkbutton(conn_frame, text="Verify SSL Certificates", variable=self.verify_ssl_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # FTP Settings
        ftp_frame = ttk.LabelFrame(settings_main, text="FTP Settings", padding="10")
        ftp_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.ftp_passive_var = tk.BooleanVar(value=self.settings['ftp_passive'])
        ttk.Checkbutton(ftp_frame, text="Use Passive Mode", variable=self.ftp_passive_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Proxy Settings
        proxy_frame = ttk.LabelFrame(settings_main, text="Proxy Settings", padding="10")
        proxy_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.proxy_enabled_var = tk.BooleanVar(value=self.settings['proxy_enabled'])
        ttk.Checkbutton(proxy_frame, text="Enable Proxy", variable=self.proxy_enabled_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(proxy_frame, text="Proxy Host:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.proxy_host_var = tk.StringVar(value=self.settings['proxy_host'])
        ttk.Entry(proxy_frame, textvariable=self.proxy_host_var, width=20).grid(row=1, column=1, padx=(5, 0), sticky=tk.W)
        
        ttk.Label(proxy_frame, text="Proxy Port:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.proxy_port_var = tk.StringVar(value=self.settings['proxy_port'])
        ttk.Entry(proxy_frame, textvariable=self.proxy_port_var, width=10).grid(row=2, column=1, padx=(5, 0), sticky=tk.W)
        
        # User Agent
        ua_frame = ttk.LabelFrame(settings_main, text="User Agent", padding="10")
        ua_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.user_agent_var = tk.StringVar(value=self.settings['user_agent'])
        ttk.Entry(ua_frame, textvariable=self.user_agent_var, width=60).grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Buttons
        button_frame = ttk.Frame(settings_main)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_settings).grid(row=0, column=1, padx=(0, 5))
        
        # Configure weights
        self.settings_frame.columnconfigure(0, weight=1)
        self.settings_frame.rowconfigure(0, weight=1)
        settings_main.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(1, weight=1)
        ua_frame.columnconfigure(0, weight=1)
        
    def choose_directory(self):
        directory = filedialog.askdirectory(initialdir=self.download_dir)
        if directory:
            self.download_dir = directory
            self.dir_label.config(text=f"Download Directory: {self.download_dir}")
    
    def test_connection(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL to test")
            return
        
        protocol = self.protocol_var.get()
        if not url.startswith(('http://', 'https://', 'ftp://')):
            url = f"{protocol}://{url}"
        
        def test_thread():
            try:
                self.root.after(0, lambda: self.status_label.config(text="Testing connection...", foreground="orange"))
                
                parsed_url = urlparse(url)
                
                if parsed_url.scheme == 'ftp':
                    # Test FTP connection
                    ftp = ftplib.FTP(timeout=self.settings['timeout'])
                    if self.settings['ftp_passive']:
                        ftp.set_pasv(True)
                    ftp.connect(parsed_url.hostname, parsed_url.port or 21)
                    ftp.login()
                    ftp.quit()
                    message = "FTP connection successful"
                else:
                    # Test HTTP/HTTPS connection
                    session = self.create_session()
                    response = session.head(url, timeout=self.settings['timeout'])
                    message = f"HTTP connection successful (Status: {response.status_code})"
                
                self.root.after(0, lambda: self.status_label.config(text=message, foreground="green"))
                self.root.after(0, lambda: messagebox.showinfo("Connection Test", message))
                
            except Exception as e:
                error_msg = f"Connection failed: {str(e)}"
                self.root.after(0, lambda: self.status_label.config(text=error_msg, foreground="red"))
                self.root.after(0, lambda: messagebox.showerror("Connection Test", error_msg))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def create_session(self):
        session = requests.Session()
        session.headers.update({'User-Agent': self.settings['user_agent']})
        
        if self.settings['proxy_enabled'] and self.settings['proxy_host']:
            proxy_url = f"http://{self.settings['proxy_host']}:{self.settings['proxy_port']}"
            session.proxies = {'http': proxy_url, 'https': proxy_url}
        
        session.verify = self.settings['verify_ssl']
        
        # Add retry adapter
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=self.settings['max_retries'],
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def add_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        
        protocol = self.protocol_var.get()
        if not url.startswith(('http://', 'https://', 'ftp://')):
            url = f"{protocol}://{url}"
            
        # Generate unique download ID
        self.download_counter += 1
        download_id = f"download_{self.download_counter}"
        
        # Get filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path) or f"download_{self.download_counter}"
        
        # Create download entry
        download_info = {
            'id': download_id,
            'url': url,
            'protocol': parsed_url.scheme.upper(),
            'filename': filename,
            'filepath': os.path.join(self.download_dir, filename),
            'size': 0,
            'downloaded': 0,
            'progress': 0,
            'speed': 0,
            'status': 'Starting...',
            'paused': False,
            'cancelled': False,
            'error': None,
            'thread': None,
            'start_time': time.time(),
            'retry_count': 0
        }
        
        self.downloads[download_id] = download_info
        
        # Add to treeview
        self.tree.insert('', 'end', iid=download_id, values=(
            filename, parsed_url.scheme.upper(), "0 B", "0%", "0 B/s", "Starting..."
        ))
        
        # Start download thread
        thread = threading.Thread(target=self.download_file, args=(download_id,))
        thread.daemon = True
        download_info['thread'] = thread
        thread.start()
        
        # Clear URL entry
        self.url_var.set("")
    
    def download_file(self, download_id):
        download_info = self.downloads[download_id]
        
        try:
            parsed_url = urlparse(download_info['url'])
            
            if parsed_url.scheme == 'ftp':
                self.download_ftp(download_id)
            else:
                self.download_http(download_id)
                
        except Exception as e:
            download_info['status'] = f'Error: {str(e)}'
            download_info['error'] = str(e)
            self.root.after(0, self.update_download_display, download_id)
    
    def download_http(self, download_id):
        download_info = self.downloads[download_id]
        session = self.create_session()
        
        try:
            # Get file info
            response = session.head(download_info['url'], timeout=self.settings['timeout'])
            
            if response.status_code not in [200, 301, 302]:
                raise Exception(f"HTTP {response.status_code}")
                
            # Get file size
            file_size = int(response.headers.get('content-length', 0))
            download_info['size'] = file_size
            
            # Update filename if Content-Disposition header exists
            if 'content-disposition' in response.headers:
                import re
                cd = response.headers['content-disposition']
                filename_match = re.findall('filename="(.+)"', cd)
                if filename_match:
                    new_filename = filename_match[0]
                    download_info['filename'] = new_filename
                    download_info['filepath'] = os.path.join(self.download_dir, new_filename)
            
            # Start actual download
            headers = {}
            if os.path.exists(download_info['filepath']):
                download_info['downloaded'] = os.path.getsize(download_info['filepath'])
                headers['Range'] = f"bytes={download_info['downloaded']}-"
            
            response = session.get(download_info['url'], headers=headers, stream=True, 
                                 timeout=self.settings['timeout'])
            
            if response.status_code not in [200, 206]:
                raise Exception(f"HTTP {response.status_code}")
            
            # Open file for writing
            mode = 'ab' if download_info['downloaded'] > 0 else 'wb'
            
            with open(download_info['filepath'], mode) as f:
                last_update = time.time()
                last_downloaded = download_info['downloaded']
                
                for chunk in response.iter_content(chunk_size=self.settings['chunk_size']):
                    if download_info['cancelled']:
                        break
                        
                    while download_info['paused'] and not download_info['cancelled']:
                        time.sleep(0.1)
                    
                    if chunk:
                        f.write(chunk)
                        download_info['downloaded'] += len(chunk)
                        
                        # Update progress every 0.5 seconds
                        current_time = time.time()
                        if current_time - last_update >= 0.5:
                            self.update_progress(download_info, current_time, last_update, last_downloaded)
                            last_update = current_time
                            last_downloaded = download_info['downloaded']
            
            # Final update
            if not download_info['cancelled']:
                download_info['status'] = 'Completed'
                download_info['progress'] = 100
                self.root.after(0, self.update_download_display, download_id)
                self.add_to_history(download_info)
                
        except Exception as e:
            download_info['status'] = f'Error: {str(e)}'
            download_info['error'] = str(e)
            self.root.after(0, self.update_download_display, download_id)
    
    def download_ftp(self, download_id):
        download_info = self.downloads[download_id]
        parsed_url = urlparse(download_info['url'])
        
        try:
            ftp = ftplib.FTP(timeout=self.settings['timeout'])
            if self.settings['ftp_passive']:
                ftp.set_pasv(True)
            
            ftp.connect(parsed_url.hostname, parsed_url.port or 21)
            ftp.login(parsed_url.username or 'anonymous', parsed_url.password or '')
            
            # Get file size
            try:
                file_size = ftp.size(parsed_url.path)
                download_info['size'] = file_size
            except:
                download_info['size'] = 0
            
            # Open file for writing
            mode = 'ab' if os.path.exists(download_info['filepath']) else 'wb'
            if mode == 'ab':
                download_info['downloaded'] = os.path.getsize(download_info['filepath'])
                ftp.sendcmd(f'REST {download_info["downloaded"]}')
            
            with open(download_info['filepath'], mode) as f:
                last_update = time.time()
                last_downloaded = download_info['downloaded']
                
                def callback(data):
                    if download_info['cancelled']:
                        return
                    
                    while download_info['paused'] and not download_info['cancelled']:
                        time.sleep(0.1)
                    
                    f.write(data)
                    download_info['downloaded'] += len(data)
                    
                    current_time = time.time()
                    if current_time - last_update >= 0.5:
                        self.update_progress(download_info, current_time, last_update, last_downloaded)
                        last_update, last_downloaded
                        last_update = current_time
                        last_downloaded = download_info['downloaded']
                
                ftp.retrbinary(f'RETR {parsed_url.path}', callback, self.settings['chunk_size'])
            
            ftp.quit()
            
            if not download_info['cancelled']:
                download_info['status'] = 'Completed'
                download_info['progress'] = 100
                self.root.after(0, self.update_download_display, download_id)
                self.add_to_history(download_info)
                
        except Exception as e:
            download_info['status'] = f'Error: {str(e)}'
            download_info['error'] = str(e)
            self.root.after(0, self.update_download_display, download_id)
    
    def update_progress(self, download_info, current_time, last_update, last_downloaded):
        # Calculate speed
        time_diff = current_time - last_update
        bytes_diff = download_info['downloaded'] - last_downloaded
        speed = bytes_diff / time_diff if time_diff > 0 else 0
        
        download_info['speed'] = speed
        download_info['status'] = 'Downloading...'
        
        # Calculate progress
        if download_info['size'] > 0:
            progress = (download_info['downloaded'] / download_info['size']) * 100
            download_info['progress'] = progress
        
        # Update UI
        self.root.after(0, self.update_download_display, download_info['id'])
    
    def update_download_display(self, download_id):
        if download_id not in self.downloads:
            return
            
        download_info = self.downloads[download_id]
        
        # Format size
        size_str = self.format_bytes(download_info['size']) if download_info['size'] > 0 else "Unknown"
        progress_str = f"{download_info['progress']:.1f}%"
        speed_str = f"{self.format_bytes(download_info['speed'])}/s"
        
        # Update treeview
        self.tree.item(download_id, values=(
            download_info['filename'],
            download_info['protocol'],
            size_str,
            progress_str,
            speed_str,
            download_info['status']
        ))
    
    def format_bytes(self, bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"
    
    def pause_download(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a download to pause")
            return
            
        download_id = selection[0]
        if download_id in self.downloads:
            self.downloads[download_id]['paused'] = True
            self.downloads[download_id]['status'] = 'Paused'
            self.update_download_display(download_id)
    
    def resume_download(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a download to resume")
            return
            
        download_id = selection[0]
        if download_id in self.downloads:
            self.downloads[download_id]['paused'] = False
            self.downloads[download_id]['status'] = 'Downloading...'
            self.update_download_display(download_id)
    
    def cancel_download(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a download to cancel")
            return
            
        download_id = selection[0]
        if download_id in self.downloads:
            self.downloads[download_id]['cancelled'] = True
            self.downloads[download_id]['status'] = 'Cancelled'
            self.update_download_display(download_id)
    
    def retry_download(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a download to retry")
            return
            
        download_id = selection[0]
        if download_id in self.downloads:
            download_info = self.downloads[download_id]
            if download_info['status'].startswith('Error') and download_info['retry_count'] < self.settings['max_retries']:
                download_info['retry_count'] += 1
                download_info['cancelled'] = False
                download_info['paused'] = False
                download_info['status'] = 'Retrying...'
                download_info['error'] = None
                
                # Start new download thread
                thread = threading.Thread(target=self.download_file, args=(download_id,))
                thread.daemon = True
                download_info['thread'] = thread
                thread.start()
                
                self.update_download_display(download_id)
            else:
                messagebox.showinfo("Info", "Maximum retries reached or download not in error state")
    
    def open_file(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a download to open")
            return
            
        download_id = selection[0]
        if download_id in self.downloads:
            filepath = self.downloads[download_id]['filepath']
            if os.path.exists(filepath):
                import subprocess
                import platform
                
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', filepath])
                elif platform.system() == 'Windows':  # Windows
                    os.startfile(filepath)
                else:  # Linux
                    subprocess.call(['xdg-open', filepath])
            else:
                messagebox.showerror("Error", "File not found")
    
    def clear_completed(self):
        to_remove = []
        for download_id, download_info in self.downloads.items():
            if download_info['status'] in ['Completed', 'Cancelled'] or download_info['status'].startswith('Error'):
                to_remove.append(download_id)
        
        for download_id in to_remove:
            self.tree.delete(download_id)
            del self.downloads[download_id]
    
    def add_to_history(self, download_info):
        self.download_history.append({
            'filename': download_info['filename'],
            'url': download_info['url'],
            'protocol': download_info['protocol'],
            'filepath': download_info['filepath'],
            'completed_time': datetime.now().isoformat(),
            'size': download_info['size']
        })
        self.save_history()
    
    def save_settings(self):
        try:
            # Update settings from UI
            self.settings['timeout'] = int(self.timeout_var.get())
            self.settings['max_retries'] = int(self.retries_var.get())
            self.settings['chunk_size'] = int(self.chunk_var.get())
            self.settings['default_protocol'] = self.default_protocol_var.get()
            self.settings['verify_ssl'] = self.verify_ssl_var.get()
            self.settings['ftp_passive'] = self.ftp_passive_var.get()
            self.settings['proxy_enabled'] = self.proxy_enabled_var.get()
            self.settings['proxy_host'] = self.proxy_host_var.get()
            self.settings['proxy_port'] = self.proxy_port_var.get()
            self.settings['user_agent'] = self.user_agent_var.get()
            
            # Save to file
            settings_file = os.path.join(os.path.expanduser("~"), ".download_manager_settings.json")
            with open(settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            # Update protocol combo default
            self.protocol_var.set(self.settings['default_protocol'])
            
            messagebox.showinfo("Settings", "Settings saved successfully!")
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid settings value: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving settings: {e}")
    
    def load_settings(self):
        try:
            settings_file = os.path.join(os.path.expanduser("~"), ".download_manager_settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                    
                # Update UI variables
                self.timeout_var.set(str(self.settings['timeout']))
                self.retries_var.set(str(self.settings['max_retries']))
                self.chunk_var.set(str(self.settings['chunk_size']))
                self.default_protocol_var.set(self.settings['default_protocol'])
                self.verify_ssl_var.set(self.settings['verify_ssl'])
                self.ftp_passive_var.set(self.settings['ftp_passive'])
                self.proxy_enabled_var.set(self.settings['proxy_enabled'])
                self.proxy_host_var.set(self.settings['proxy_host'])
                self.proxy_port_var.set(self.settings['proxy_port'])
                self.user_agent_var.set(self.settings['user_agent'])
                
                # Update protocol combo default
                self.protocol_var.set(self.settings['default_protocol'])
                
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def reset_settings(self):
        # Reset to defaults
        default_settings = {
            'timeout': 30,
            'max_retries': 3,
            'chunk_size': 8192,
            'max_connections': 5,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'default_protocol': 'https',
            'verify_ssl': True,
            'proxy_enabled': False,
            'proxy_host': '',
            'proxy_port': '',
            'ftp_passive': True
        }
        
        self.settings.update(default_settings)
        
        # Update UI
        self.timeout_var.set(str(self.settings['timeout']))
        self.retries_var.set(str(self.settings['max_retries']))
        self.chunk_var.set(str(self.settings['chunk_size']))
        self.default_protocol_var.set(self.settings['default_protocol'])
        self.verify_ssl_var.set(self.settings['verify_ssl'])
        self.ftp_passive_var.set(self.settings['ftp_passive'])
        self.proxy_enabled_var.set(self.settings['proxy_enabled'])
        self.proxy_host_var.set(self.settings['proxy_host'])
        self.proxy_port_var.set(self.settings['proxy_port'])
        self.user_agent_var.set(self.settings['user_agent'])
        self.protocol_var.set(self.settings['default_protocol'])
        
        messagebox.showinfo("Settings", "Settings reset to defaults!")
    
    def save_history(self):
        try:
            history_file = os.path.join(os.path.expanduser("~"), ".download_manager_history.json")
            with open(history_file, 'w') as f:
                json.dump(self.download_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def load_history(self):
        try:
            history_file = os.path.join(os.path.expanduser("~"), ".download_manager_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.download_history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.download_history = []

def main():
    root = tk.Tk()
    app = DownloadManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()