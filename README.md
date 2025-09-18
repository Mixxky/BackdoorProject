


# BackdoorProject - Remote Administration Tool

This project is a sophisticated remote administration tool (RAT) developed in Python. It consists of a client (`bd.py`) and a server (`server.py`) with a graphical user interface (GUI) built using Tkinter. This tool is intended for educational purposes in the field of ethical hacking and cybersecurity.

## Features

- **GUI Control Panel:** An intuitive server-side interface for managing connections and operations.
- **Multi-Client Handling:** Can manage multiple client connections simultaneously.
- **Command Execution:** A full remote shell to execute commands on the target machine.
- **File Transfer:** Upload and download files between the server and client.
- **Session Capture:**
    - Live Desktop Streaming
    - Screenshot Capture
    - Audio Recording
- **Keylogger:** Capture and retrieve keystrokes from the target.
- **Privilege Escalation:** Includes a UAC bypass technique for Windows to gain elevated privileges.

## Prerequisites

- Python 3.x
- `pip` (Python package installer)

## Setup & Installation

Follow these steps to set up the environment for both the server and the client.

### 1. Clone the Repository

First, clone the repository to your local machine (both the attacker's and the victim's).

```bash
git clone https://github.com/Mixxky/backdoorupgrade.git
cd backdoorupgrade
```

### 2. Set Up a Virtual Environment

It is highly recommended to use a Python virtual environment to manage dependencies and avoid conflicts.

**On Windows:**

```bash
python -m venv my-env
my-env\\Scripts\\activate
```

**On macOS/Linux:**

```bash
python3 -m venv my-env
source my-env/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

## Configuration

Before running the application, you must configure the static IP address. This IP should be the address of the machine where the **server** will be running.

**Important:** This IP address must be accessible from the client machine. If you are not on the same local network, you will need to use your server's public IP address and ensure the correct ports are open (5555 for the control connection and 5556 for the video stream).

1.  **Open `server.py`:**
    Find the line `STATIC_IP = '192.168.1.41'` and change the IP address to your server's IP.

2.  **Open `bd.py`:**
    Find the line `HOST = '192.168.1.41'` and change the IP address to match the one you set in `server.py`.

## How to Use

### Step 1: Start the Server

On the attacker's machine, run the `server.py` script.

```bash
python server.py
```

The Control Panel GUI will launch, and the server will start listening for incoming connections.

### Step 2: Run the Backdoor on the Target

On the victim's machine, run the `bd.py` script.

```bash
python bd.py
```

The script will run silently in the background and attempt to connect to the server.

### Step 3: Manage the Target via the Control Panel

Once the client connects, a dialog will appear on the server GUI asking you to give the target a nickname. After that, the target will appear in the "TARGETS" list.

- **Select a Target:** Click on a client in the "TARGETS" list to make it the active target.
- **Use the Features:**
    - **Terminal:** Execute shell commands.
    - **Files Tab:** Upload/download files.
    - **Privilege Escalation Tab:** Attempt to gain admin rights.
    - **Keylogger Tab:** Capture keystrokes.
    - **Quick Actions Panel:** Use shortcuts for common actions like screenshots, audio recording, and desktop streaming.
    - **Help Button:** Click the "Instructions" button for a detailed guide on all features.

## Disclaimer

This tool is for educational purposes only. Unauthorized access to computer systems is illegal. The author is not responsible for any misuse of this software. Always obtain explicit permission before testing on any system.
