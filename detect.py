import os
import glob
from picamera2 import Picamera2
import cv2
import numpy as np
import time
import requests

# CONFIG
CONFIDENCE_THRESHOLD = 0.3
ALERT_CONFIDENCE_THRESHOLD = 0.44
COOLDOWN = 15
CLEANUP_INTERVAL = 600  # 10 mins

capture_message_id = None
waiting_for_capture_ok = False
capture_image_path = None

TELEGRAM_TOKEN = "" # Sign up to Telegram's Botfather and create a token there 
TELEGRAM_CHAT_ID = "" # Do a /getUpdates request with the bot and get the chat id

PERSON_CLASS_ID = 15 # Person is this class id in the model we are using

# TELEGRAM FUNCTIONS
def send_telegram_alert(image_path):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(image_path, "rb") as photo:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": "🚨 Person detected by Security Robot! Reply 'ok' to delete or 'save' to keep."
            }
            response = requests.post(url, data=payload, files={"photo": photo}, timeout=15).json()
        print("[TELEGRAM] Alert sent!")
        return response.get("result", {}).get("message_id")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return None

def delete_telegram_message(message_id):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "message_id": message_id
        }, timeout=5)
        print(f"[TELEGRAM] Deleted message {message_id}")
    except Exception as e:
        print(f"[TELEGRAM DELETE ERROR] {e}")

def check_for_ok_reply(last_update_id, alert_time):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
        params = {"offset": last_update_id + 1, "timeout": 1}
        response = requests.get(url, params=params, timeout=5).json()

        for update in response.get("result", []):
            message = update.get("message", {})
            text = message.get("text", "").strip().lower()
            msg_time = message.get("date", 0)
            ok_message_id = message.get("message_id")

            if text in ["ok", "save"] and msg_time > alert_time:
                last_update_id = update["update_id"]
                return True, last_update_id, ok_message_id, text
            elif text in ["ok", "save"]:
                last_update_id = update["update_id"]

        return False, last_update_id, None, None
    except Exception as e:
        print(f"[TELEGRAM CHECK ERROR] {e}")
        return False, last_update_id, None, None
def write_status(state):
    try:
        with open("robot_status.txt", "w") as f:
            f.write(state)
    except Exception as e:
        print(f"[STATUS ERROR] {e}")

def check_for_capture_request():
    try:
        if os.path.exists("/home/john/person_detection/capture_request.txt"):
            os.remove("/home/john/person_detection/capture_request.txt")
            return True
    except Exception as e:
        print(f"[CAPTURE ERROR] {e}")
    return False

# CLEANUP OLD ALERTS
def cleanup_old_alerts(max_age_hours=24):
    try:
        cutoff = time.time() - (max_age_hours * 3600)
        files = glob.glob("alert_*.jpg")
        deleted = 0
        for f in files:
            if os.path.getmtime(f) < cutoff:
                os.remove(f)
                deleted += 1
        if deleted > 0:
            print(f"[CLEANUP] Deleted {deleted} old alert image(s)")
    except Exception as e:
        print(f"[CLEANUP ERROR] {e}")

# LOAD MODEL
print("[INFO] Loading MobileNet SSD...")
net = cv2.dnn.readNetFromCaffe(
    "MobileNetSSD_deploy.prototxt",
    "MobileNetSSD_deploy.caffemodel"
)
print("[INFO] MobileNet SSD loaded")

# SETUP CAMERA
print("[INFO] Starting camera...")
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (640, 480)}
)
picam2.configure(config)
picam2.start()
time.sleep(2)
print("[INFO] Camera started")

# STATE VARIABLES
last_alert_time = 0
last_update_id = 0
last_cleanup_time = 0
waiting_for_ok = False
alert_message_id = None
image_path = None

print("[INFO] Starting detection loop. Press Q to quit.")
write_status("SCANNING")

# DETECTION LOOP
while True:
    frame_rgb = picam2.capture_array()
    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    frame = cv2.flip(frame, -1)
    h, w = frame.shape[:2]

    blob = cv2.dnn.blobFromImage(
        cv2.resize(frame, (300, 300)),
        scalefactor=0.007843,
        size=(300, 300),
        mean=127.5
    )

    net.setInput(blob)
    detections = net.forward()

    person_detected = False
    alert_confidence = 0.0

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        class_id = int(detections[0, 0, i, 1])

        if confidence < CONFIDENCE_THRESHOLD:
            continue
        if class_id != PERSON_CLASS_ID:
            continue

        person_detected = True
        if confidence > alert_confidence:
            alert_confidence = confidence

        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        (startX, startY, endX, endY) = box.astype("int")

        label = f"Person: {confidence * 100:.1f}%"
        cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
        text_y = max(startY - 10, 15)
        cv2.putText(frame, label, (startX, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        print(f"[DETECTED] {label}")

    # Send alert if confident enough and not waiting for ok
    if person_detected and alert_confidence >= ALERT_CONFIDENCE_THRESHOLD:
        current_time = time.time()
        if not waiting_for_ok and current_time - last_alert_time >= COOLDOWN:
            image_path = f"alert_{int(current_time)}.jpg"
            cv2.imwrite(image_path, frame)
            alert_message_id = send_telegram_alert(image_path)
            last_alert_time = current_time
            waiting_for_ok = True
            write_status("WAITING_FOR_OK")
            print(f"[INFO] Alert sent at {alert_confidence * 100:.1f}% confidence")
            print("[INFO] Waiting for ok from staff before sending further alerts...")
        elif waiting_for_ok:
            print(f"[INFO] Person detected but waiting for staff ok first")
    elif person_detected:
        print(f"[INFO] Person detected but only {alert_confidence * 100:.1f}% confident - no alert")

    # Check for ok/save reply from staff
    if waiting_for_ok:
        ok_received, last_update_id, ok_message_id, reply_type = check_for_ok_reply(last_update_id, last_alert_time)
        if ok_received:
            waiting_for_ok = False
            write_status("SCANNING")
            if reply_type == "ok":
                print("[INFO] OK received - deleting messages and re-enabling alerts")
                if alert_message_id:
                    delete_telegram_message(alert_message_id)
                if ok_message_id:
                    delete_telegram_message(ok_message_id)
            elif reply_type == "save":
                print("[INFO] SAVE received - reposting alert photo with saved caption")
                if ok_message_id:
                    delete_telegram_message(ok_message_id)
                if alert_message_id:
                    delete_telegram_message(alert_message_id)
                if image_path and os.path.exists(image_path):
                    try:
                        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                        with open(image_path, "rb") as photo:
                            requests.post(url, data={
                                "chat_id": TELEGRAM_CHAT_ID,
                                "caption": f"📸 Saved alert- {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(last_alert_time))}"
                            }, files={"photo": photo}, timeout=10)
                        print("[TELEGRAM] Saved alert reposted")
                    except Exception as e:
                        print(f"[TELEGRAM RESEND ERROR] {e}")
            alert_message_id = None

    # Check for capture request
    if check_for_capture_request():
        capture_image_path = f"capture_{int(time.time())}.jpg"
        cv2.imwrite(capture_image_path, frame)
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open(capture_image_path, "rb") as photo:
                response = requests.post(url, data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": f"📷 Manual capture- {time.strftime('%d/%m/%Y %H:%M:%S')}\nReply 'ok' to delete or 'save' to keep."
                }, files={"photo": photo}, timeout=10).json()
            capture_message_id = response.get("result", {}).get("message_id")
            waiting_for_capture_ok = True
            print("[INFO] Capture sent to Telegram")
        except Exception as e:
            print(f"[CAPTURE ERROR] {e}")

    # Check for capture ok/save reply (only when not waiting for alert ok)
    if waiting_for_capture_ok and not waiting_for_ok:
        ok_received, last_update_id, ok_message_id, reply_type = check_for_ok_reply(last_update_id, 0)
        if ok_received:
            waiting_for_capture_ok = False
            if reply_type == "ok":
                print("[INFO] Capture OK received - deleting")
                if capture_message_id:
                    delete_telegram_message(capture_message_id)
                if ok_message_id:
                    delete_telegram_message(ok_message_id)
                try:
                    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
                    params = {"offset": last_update_id, "timeout": 1}
                    response = requests.get(url, params=params, timeout=15).json()
                    for update in response.get("result", []):
                        msg = update.get("message", {})
                        if msg.get("text", "").strip().lower() == "/capture":
                            delete_telegram_message(msg.get("message_id"))
                except:
                    pass
                if capture_image_path and os.path.exists(capture_image_path):
                    os.remove(capture_image_path)
                capture_message_id = None
                capture_image_path = None
            elif reply_type == "save":
                print("[INFO] Capture SAVE received - reposting")
                if ok_message_id:
                    delete_telegram_message(ok_message_id)
                if capture_message_id:
                    delete_telegram_message(capture_message_id)
                if capture_image_path and os.path.exists(capture_image_path):
                    try:
                        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                        with open(capture_image_path, "rb") as photo:
                            requests.post(url, data={
                                "chat_id": TELEGRAM_CHAT_ID,
                                "caption": f"📸 Saved capture- {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(int(capture_image_path.split('_')[1].split('.')[0])))}"
                            }, files={"photo": photo}, timeout=10)
                        print("[TELEGRAM] Saved capture reposted")
                    except Exception as e:
                        print(f"[TELEGRAM RESEND ERROR] {e}")
                capture_message_id = None
                capture_image_path = None

    # cleanup of old alert images on Pi
    if time.time() - last_cleanup_time >= CLEANUP_INTERVAL:
        cleanup_old_alerts(max_age_hours=24)
        last_cleanup_time = time.time()

    # Screen overlay on pi
    if waiting_for_ok:
        cv2.putText(frame, "WAITING FOR OK", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
    elif waiting_for_capture_ok:
        cv2.putText(frame, "CAPTURE SENT - WAITING FOR OK", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)
    else:
        cv2.putText(frame, "SCANNING...", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Person Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# SHUTDOWN CLEAN UP
print("[INFO] Shutting down...")
write_status("OFFLINE")
picam2.stop()
cv2.destroyAllWindows()
print("[INFO] Done.")
