#The Main Functions of the application are in this script
import cv2
import torch
import numpy as np
import time
import os
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from win10toast import ToastNotifier

# YOLO model for pose estimation
model = YOLO("yolo11n-pose.pt") 

# Open webcam
cap = cv2.VideoCapture(0)

# Keypoint Labels 
KEYPOINT_NAMES = [
    "Nose", "Right Eye", "Left Eye", "Right Ear", "Left Ear",
    "Right Shoulder", "Left Shoulder",  # Only keep shoulder-related keypoints
]

SKELETON = [
    (0, 1), (0, 2),  # Eyes to nose 
    (1, 3), (2, 4),  # Ears to respective eyes
    (5, 6),  # Shoulders connection 
]

DISTANCE_THRESHOLD = 520  
Bodybone = False
Facialbone= False
cap = cv2.VideoCapture(0)

def get_posture_frame():
    ret, frame = cap.read()
    if not ret:
        return None

    frame = cv2.flip(frame, 1)  # Flip for mirrored effect

    results = model.track(frame, conf=0.4, iou=0.8, persist=True)

    annotator = Annotator(frame, line_width=2)

    posture_percentage = 0  # Start posture percentage

    # Check if there are detected keypoints
    if results and results[0].keypoints is not None:
        keypoints = results[0].keypoints.xy  # keypoints
        boxes = results[0].boxes.xyxy  # User Bounding boxe
        classes = results[0].boxes.cls  # Class labels

        if len(boxes) > 0:
            # Select the largest detected person based on bounding box size
            areas = [(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in boxes]
            largest_idx = np.argmax(areas)  

            # Extract keypoints and bounding box of the largest person
            kp = keypoints[largest_idx]
            box = boxes[largest_idx]

            if isinstance(kp, torch.Tensor):
                kp = kp.cpu().numpy()

            # Draw bounding box around the detected user
            x1, y1, x2, y2 = map(int, box)
            box_width = x2 - x1
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)  

            # Ensure keypoints
            if kp is not None and len(kp) > 0:
                Bodybone = False
                Facialbone = False
                # Calculate the middle shoulder
                if len(kp) > 5 and len(kp) > 6:
                    right_shoulder = kp[5]
                    left_shoulder = kp[6]
                    if right_shoulder[0] > 0 and left_shoulder[0] > 0: 
                        middle_shoulder_x = (right_shoulder[0] + left_shoulder[0]) / 2
                        middle_shoulder_y = (right_shoulder[1] + left_shoulder[1]) / 2
                        kp_middle_shoulder = [middle_shoulder_x, middle_shoulder_y]
                        Bodybone = True

                        # Add middle shoulder keypoint
                        cv2.circle(frame, (int(kp_middle_shoulder[0]), int(kp_middle_shoulder[1])), 5, (255, 0, 0), -1)
                        cv2.putText(frame, "Middle Shoulder", (int(kp_middle_shoulder[0]) + 5, int(kp_middle_shoulder[1]) - 5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        kp = np.vstack([kp, kp_middle_shoulder])  # Append middle shoulder as a new keypoint
                       
                        SKELETON.append((0, len(kp) - 1))  # Adding bone between nose and middle shoulder
                              
                if len(kp) > 4:  # Ensure keypoints for eyes, nose, and ears 
                    right_eye = kp[1]
                    left_eye = kp[2]
                    nose = kp[0]

                    # Check if all facial parts are visible before calculating posture percentage
                    if right_eye[0] > 0 and left_eye[0] > 0 and nose[0] > 0: 
                        Facialbone = True

                # Draw keypoints and display their names
                for i, (x, y) in enumerate(kp):
                    if i < len(KEYPOINT_NAMES):
                        if x > 0 and y > 0: 
                            cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1) 
                            cv2.putText(frame, KEYPOINT_NAMES[i], (int(x) + 5, int(y) - 5), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Draw skeleton connections only for middle shoulder to nose
                for p1, p2 in SKELETON:
                    if p1 < len(kp) and p2 < len(kp):  
                        x1, y1 = kp[p1]
                        x2, y2 = kp[p2]
                        if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0: 
                            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2) 
                            
                # Calculate posture percentage using distance between nose and middle shoulder
                if len(kp) > 6:
                    nose_x, nose_y = kp[0]
                    middle_shoulder_x, middle_shoulder_y = kp[-1]
                    distance = np.sqrt((nose_x - middle_shoulder_x) ** 2 + (nose_y - middle_shoulder_y) ** 2)

                    # Logic: Nose farther from middle shoulder means better posture
                    if distance > 16:  
                        # Stronger scaling with 70% as a base
                        posture_percentage = int((distance - 165 ) * 0.45) + 70  # Start at 70% as the base

                        # Ensure the percentage doesn't go above 100%
                        posture_percentage = min(posture_percentage, 100)
                    else:  
                        # More aggressive decrease if user hunched thier back pass the certain point
                        posture_percentage = max(40, int(90 - (150 - distance) * 0.7))  # 40% minimum

                    # Again, ensure the percentage stays between 1% and 100%
                    posture_percentage = min(100, max(1, posture_percentage))

                # Display posture grade
                posture_text = ""
                text_color = (255, 255, 255)
                if posture_percentage >= 99:
                    posture_text = "Perfect Posture!"
                    text_color = (0, 255, 0)  # Green for perfect posture
                elif posture_percentage >= 80:
                    posture_text = "Good Posture!"
                    text_color = (0, 255, 255)  # Yellow for good posture
                elif posture_percentage >= 79:
                    posture_text = "Bad Posture!"
                    text_color = (0, 165, 255)  # Orange for bad posture
                    window_notification()
                else:
                    posture_text = "Bad Posture!"
                    text_color = (0, 165, 255)  # Orange for bad posture
                    window_notification()
                    


                    # Display posture percentage and grade as texts
                if box_width > DISTANCE_THRESHOLD and Bodybone and Facialbone:
                        cv2.putText(frame, f"Posture Percentage: {int(posture_percentage)}%", (10, 50), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                        cv2.putText(frame, posture_text, (10, 80), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2) 
                else: 
                    cv2.putText(frame, f"Get closer to the camera", (10, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    return frame

#Window Notification 
last_notification_time = 0  
COOLDOWN_TIME = 15  
notifications_enabled = True

def set_notifications_enabled(state):
    global notifications_enabled
    notifications_enabled = state
    print(f"Notifications enabled: {notifications_enabled}") 

def window_notification():
    global last_notification_time  # global variable

    
    current_time = time.time()  # Get the current time
    if current_time - last_notification_time < COOLDOWN_TIME:
        return  # Exit function if notification cooldown is active

    if not notifications_enabled:
        return  # Do not show notification if disabled via UI
    
    # Update the last notification time
    last_notification_time = current_time

    toast = ToastNotifier()
    toast.show_toast(
        "Bad Posture Detected",
        "Correct Your Sitting For Your Back Health!",
        duration=5,
        icon_path='',
        threaded=True,)

def release_camera():
    cap.release()