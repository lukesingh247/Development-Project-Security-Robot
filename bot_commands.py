import requests
import time
import os
import subprocess

TELEGRAM_TOKEN = "" # Check detect.py
TELEGRAM_CHAT_ID = ""

DETECTION_SCRIPT = "/home/john/person_detection/detect.py"
PYTHON_PATH = "/home/john/robot-env/bin/python3"

last_update_id = 0
detection_process = None

# This text is what shows when the user runs /help
HELP_TEXT = """
*Security Robot Help*

*Commands:*
`ok` - Acknowledge alert and delete the photo
`save` - Acknowledge alert and keep the photo with a saved caption
`/help` - Show this message
`/status` - Check current robot status
`/begin` - Start the detection script
`/stop` - Stop the detection script
`/capture` - Take an instant capture using the camera 

*Alert states:*
🟢 SCANNIN - Robot is patrolling, no alerts pending
🟠 WAITING FO OK - Person detected, waiting for acknowledgement
⚪ OFFLIN - Detection script not running

*Notes:*
- Alerts will not resend until you acknowledge with ok or save
- Saved photos are timestamped with the detection time
- Alert images are automatically deleted from the Pi after 24 hours
"""

def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=5)
    except Exception as e:
        print(f"[BOT ERROR] {e}")

def get_status():
    try:
        # First check if the process is actually running
        if not is_detection_running():
            return "⚪ *Status:* Detection script not running"
        # read froom the status text to get status of bot
        if not os.path.exists("/home/john/person_detection/robot_status.txt"):
            return "🟢 *Status:* Running- status unknown"
        with open("/home/john/person_detection/robot_status.txt", "r") as f:
            state = f.read().strip()
        if state == "WAITING_FOR_OK":
            return "🟠 *Status:* Person detected- waiting for acknowledgement"
        elif state == "SCANNING":
            return "🟢 *Status:* Scanning- no alerts pending"
        else:
            return f"❓ *Status:* Unknown state: {state}"
    except Exception as e: # any error return a warning to user in chat
        return f"❓ *Status:* Could not read status: {e}"

def request_capture():
    try:
        if not is_detection_running():
            send_message("⚠️ Detection script is not running — use /begin first")
            return
        with open("/home/john/person_detection/capture_request.txt", "w") as f:
            f.write("CAPTURE")
        send_message("📷 Capture requested...")
        print("[BOT] Capture request sent")
    except Exception as e:
        send_message(f"❌ Failed to request capture: {e}")

def is_detection_running():
    global detection_process
    if detection_process is None:
        return False
    # Check if it is still running
    return detection_process.poll() is None

def start_detection():
    global detection_process
    if is_detection_running():
        send_message("⚠️ Detection is already running")
        return
    try:
        detection_process = subprocess.Popen(
            [PYTHON_PATH, DETECTION_SCRIPT],
            cwd="/home/john/person_detection"
        )
        time.sleep(2)
        if is_detection_running():
            send_message("✅ Detection started successfully")
            print("[BOT] Detection script started")
        else:
            send_message("❌ Detection failed to strt - check the Pi logs")
    except Exception as e:
        send_message(f"❌ Failed to start detection: {e}")
        print(f"[BOT ERROR] {e}")

def stop_detection():
    global detection_process
    if not is_detection_running():
        send_message("⚠️ Detection is not currently running - use /begin first")
        return
    try:
        detection_process.terminate()
        detection_process.wait(timeout=5)
        detection_process = None
        write_status("OFFLINE")
        send_message("🛑 Detection stopped")
        print("[BOT] Detection script stopped")
    except Exception as e:
        send_message(f"❌ Failed to stop detection: {e}")
        print(f"[BOT ERROR] {e}")

def is_waiting_for_ok():
    try:
        path = "/home/john/person_detection/robot_status.txt"
        if not os.path.exists(path):
            return False
        with open(path, "r") as f:
            return f.read().strip() == "WAITING_FOR_OK"
    except:
        return False

# Used for the updating the status file which is used for status check
def write_status(state):
    try:
        with open("robot_status.txt", "w") as f:
            f.write(state)
    except Exception as e:
        print(f"[STATUS ERROR] {e}")

# Check for commands is mainly for error handling
def check_for_commands(last_update_id):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {"offset": last_update_id + 1, "timeout": 1}
        response = requests.get(url, params=params, timeout=5).json()

        for update in response.get("result", []):
            last_update_id = update["update_id"]
            message = update.get("message", {})
            text = message.get("text", "").strip().lower()

            if text == "/help":
                send_message(HELP_TEXT)
                print("[BOT] Sent help message")
            elif text == "/status":
                send_message(get_status())
                print("[BOT] Sent status message")
            elif text == "/begin":
                print("[BOT] Start command received")
                start_detection()
            elif text == "/stop":
                if is_waiting_for_ok():
                    send_message("⚠️ Cannot stop while an alert is active.\n\nReply *ok* to delete or *save* to keep the alert first.")
                    print("[BOT] Blocked /stop during WAITING_FOR_OK")
                else:
                    print("[BOT] Stop command received")
                    stop_detection()
            elif text == "/capture":
                if is_waiting_for_ok():
                    send_message("⚠️ Cannot capture while an alert is active.\n\nReply *ok* or *save* first.")
                    print("[BOT] Blocked /capture during WAITING_FOR_OK")
                else:
                    print("[BOT] Capture command received")
                    request_capture()
            elif text in ["ok", "save"]:
                continue # continuing instead of pass as there was a conflict between the two scripts
            elif text == "/start":
                pass
            elif text:
                # Anything else
                send_message(
                    f"⚠️ Unknown command: `{text}`\n\nType /help to see available commands."
                )
                print(f"[BOT] Unknown command received: {text}")

        return last_update_id
    except Exception as e:
        print(f"[BOT ERROR] {e}")
        return last_update_id

print("[BOT] Command listener running. Press Ctrl+C to stop.")

while True:
    last_update_id = check_for_commands(last_update_id)
    time.sleep(2)
