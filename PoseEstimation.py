#The Main Functions of the application are in this script
import cv2
import torch
import numpy as np
import math
import time
from ultralytics import YOLO
from win10toast import ToastNotifier
import json
import random
from collections import deque

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

Bodybone = False
Facialbone= False
posture_percentage = 0

# For smoothing
middle_shoulder_buffer = deque(maxlen=5)
facial_point_buffer = deque(maxlen=5)


def load_best_distance():
    file_path = 'best_distance.json'
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get("best_distance", None)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No previous best distance found or JSON is invalid.")
        return None
    
def get_posture_frame():
    global Bodybone, Facialbone, posture_percentage

    ret, frame = cap.read()
    if not ret:
        return None

    frame = cv2.flip(frame, 1) 

    results = model.track(frame, conf=0.4, iou=0.8, persist=True)

    # Check if there are detected keypoints
    if results and results[0].keypoints is not None:
        keypoints = results[0].keypoints.xy  # Keypoints
        boxes = results[0].boxes.xyxy  # User Bounding boxe

        if len(boxes) > 0:
            # Select the largest detected person based on bounding box size so that it detects only a single person
            areas = [(x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in boxes]
            largest_idx = np.argmax(areas)  

            # Extract keypoints and bounding box of the largest person
            kp = keypoints[largest_idx]
            box = boxes[largest_idx]

            if isinstance(kp, torch.Tensor):
                kp = kp.cpu().numpy()
            
            idx_middle_shoulder = None
            idx_facial_point = None
            
            # Draw bounding box around the detected user
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)  

            # Ensure Middle_Shoulder keypoints
            if kp is not None and len(kp) > 0:
                # Calculate the middle shoulder
                if len(kp) > 5 and len(kp) > 6:
                    right_shoulder = kp[5]
                    left_shoulder = kp[6]
                    if right_shoulder[0] > 0 and left_shoulder[0] > 0: 
                        middle_shoulder_x = (right_shoulder[0] + left_shoulder[0]) / 2
                        middle_shoulder_y = (right_shoulder[1] + left_shoulder[1]) / 2
                        kp_middle_shoulder = [middle_shoulder_x, middle_shoulder_y]
                        
                        kp = np.vstack([kp, kp_middle_shoulder])  # Append middle shoulder as a new keypoint
                        idx_middle_shoulder = len(kp) - 1 
                       
            
            # Ensure facial keypoints (ear to ear)
            if kp is not None and len(kp) > 0:
                # Calculate the middle connected point
                if len(kp) > 4:
                    right_ear = kp[3]
                    left_ear = kp[4]
                    if right_ear[0] > 0 and left_ear[0] > 0: 
                        facial_point_x = (right_ear[0] + left_ear[0]) / 2
                        facial_point_y = (right_ear[1] + left_ear[1]) / 2
                        kp_facial_point = [facial_point_x, facial_point_y]

                        kp = np.vstack([kp, kp_facial_point])  # Append facial as a new keypoint
                        idx_facial_point = len(kp) - 1  
                        
                if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0:
                    SKELETON.append((idx_middle_shoulder, idx_facial_point))
                
                # Ensure keypoints for shoulders, ears, and nose
                if len(kp) > 4:  
                    right_ear= kp[3]
                    left_ear = kp[4]
                    nose = kp[0]

                # Footage GUI
                # Draw skeleton connections
                for p1, p2 in SKELETON:
                    
                    if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0: #draw an extra inner outline between middle shoulder and facial point
                        cv2.line(frame, 
                            (int(kp[idx_middle_shoulder][0]), int(kp[idx_middle_shoulder][1])), 
                            (int(kp[idx_facial_point][0]), int(kp[idx_facial_point][1])),
                            (0, 255, 0), 5)  # Green line
                        
                    if p1 < len(kp) and p2 < len(kp): #skeletons  
                        x1, y1 = kp[p1]
                        x2, y2 = kp[p2]
                        if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0: 
                            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2) 
                    
                # Draw keypoints and display their names
                LEFT_KEYPOINTS = {2,4,6}   
                RIGHT_KEYPOINTS = {1,3,5} 

                for i, (x, y) in enumerate(kp):
                    if i < len(KEYPOINT_NAMES):
                        if x > 0 and y > 0: 
                            cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)

                            # Offset x for left/right
                            if i in LEFT_KEYPOINTS:
                                text_x = int(x) - 55  # More space on left for names
                            elif i in RIGHT_KEYPOINTS:
                                text_x = int(x) + 5
                            else:
                                text_x = int(x)  # For center keypoints like nose

                            cv2.putText(frame, KEYPOINT_NAMES[i], (text_x, int(y) - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                            # Add Facial keypoint (ear to ear)
                            if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0:
                                cv2.circle(frame, (int(kp_facial_point[0]), int(kp_facial_point[1])), 5, (0, 0, 255), -1)
                                cv2.putText(frame, "Facial Point", (int(kp_facial_point[0]) - 5, int(kp_facial_point[1]) - 5), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                                # Add middle shoulder keypoint
                                cv2.circle(frame, (int(kp_middle_shoulder[0]), int(kp_middle_shoulder[1])), 5, (0, 0, 255), -1)
                                cv2.putText(frame, "Middle Shoulder", (int(kp_middle_shoulder[0]) - 5, int(kp_middle_shoulder[1]) - 5), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                #Posture Pecentage Calculation method
                if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0:

                    # 1. Calculate shoulder distance
                    left_shoulder_x, left_shoulder_y = left_shoulder
                    right_shoulder_x, right_shoulder_y = right_shoulder
                    shoulder_distance = np.sqrt((left_shoulder_x - right_shoulder_x) ** 2 + (left_shoulder_y - right_shoulder_y) ** 2)

                    # 2. Define a consistent reference distance for shoulder width
                    ideal_shoulder_distance = 360  #Average from 200 and 520 which is the average user min-max distance from camera

                    # 3. Calculate current face-to-body distance using the middle shoulder and facial point
                    if 'kp_middle_shoulder' in locals() and 'kp_facial_point' in locals():
                        dx = kp_middle_shoulder[0] - kp_facial_point[0]
                        dy = kp_middle_shoulder[1] - kp_facial_point[1]
                        raw_distance = math.sqrt(dx ** 2 + dy ** 2)

                    # 4. Scale posture distance based on shoulder distance
                    scaling_factor = ideal_shoulder_distance / shoulder_distance
                    current_distance = raw_distance * scaling_factor

                    # 5. Compare the current_distance with the best_calibrated_distance (saved from the calibration window)
                    best_calibrated_distance = load_best_distance() +10


                    lower_limit = best_calibrated_distance * 0.95
                    upper_limit = best_calibrated_distance * 1.01  

                    # 6. Posture percentage calculation
                    if lower_limit <= current_distance <= upper_limit:
                        posture_percentage = 100
                    elif current_distance < lower_limit:
                        difference = lower_limit - current_distance
                        posture_percentage = max(0, 100 - (difference / best_calibrated_distance) * 170)
                    elif current_distance > upper_limit:
                        difference = current_distance - upper_limit
                        posture_percentage = max(0, 100 - (difference / best_calibrated_distance) * 100)
                    else:
                        posture_percentage = 100

                    #Show nomalized shoulders distance as text (distance from camera)
                    #z_distance_text = f"z_distance: {shoulder_distance}"
                    # = f"Current Distance: {current_distance:.2f}"
                    #best_calibrated_distance_text = f" Calibrated Distance: {best_calibrated_distance}"

                    # Determine posture grade & color
                    if posture_percentage >= 99:
                        posture_text = "Good Posture!"
                        text_color = (0, 255, 0)  # Green
                    elif posture_percentage >= 90:
                        posture_text = "Good Posture!"
                        text_color = (0, 255, 255)  # Yellow
                    else:
                        posture_text = "Bad Posture!"
                        text_color = (0, 165, 255)  # Orange
                        window_notification()  # Trigger notification for bad posture

                    # Check if all facial and body parts are visible to the camera before show posture percentage
                    if right_ear[0] > 0 and left_ear[0] > 0 and nose[0] > 0: 
                        Facialbone = True
                    else:
                        Facialbone = False
                    
                    if right_shoulder[0] > 0 and left_shoulder[0] > 0: 
                        Bodybone = True
                    else:
                        Bodybone = False
                    
                    if Bodybone and Facialbone:
                        #cv2.putText(frame, z_distance_text, (int(middle_shoulder_x) + 0, int(middle_shoulder_y) + 40), 
                            #cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                        cv2.putText(frame, f"Posture Percentage: {int(posture_percentage)}%", (10, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                        cv2.putText(frame, posture_text, (10, 80),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)
                        
                        #cv2.putText(frame, best_calibrated_distance_text, (5, 110), 
                           # cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        #cv2.putText(frame, current_distance_text, (15, 140), 
                           # cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                else:
                    cv2.putText(frame, f"Make sure the camera can see all your face and shoulder keypoints!", (10, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
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
    
    messages = [
    "Sit Up Straight – Your Back Will Thank You!",
    "Support Your Spine – Adjust Your Posture Now!",
    "Keep Your Back Happy – Fix That Posture!",
    "Straighten Up for a Stronger, Healthier Back!",
    "A Healthier Back Starts with Better Posture – Sit Right!"]

    random_message = random.choice(messages)

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
        random_message,
        duration=5,
        icon_path='',
        threaded=True,)

def release_camera():
    global cap

    cap.release()
    cap = None

    if cap is None:
        cap = cv2.VideoCapture(0)

