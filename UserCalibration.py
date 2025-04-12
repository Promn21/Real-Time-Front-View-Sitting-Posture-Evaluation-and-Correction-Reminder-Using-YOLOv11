import cv2
import torch
import numpy as np
from ultralytics import YOLO
import json

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
best_distance = None

idx_middle_shoulder = None
idx_facial_point = None
default_calibrated_distance = None

def load_best_distance():
    file_path = 'best_distance.json'
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get("best_distance", None)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No previous best distance found, using the 220 default distance instead.")
        return 220  # Default value if no previous distance is found
    
def get_calibration_frame():
    global best_distance, Bodybone, Facialbone, posture_percentage,default_calibrated_distance

    ret, calibrated_frame = cap.read()
    if not ret:
        return None

    calibrated_frame = cv2.flip(calibrated_frame, 1) 

    results = model.track(calibrated_frame, conf=0.4, iou=0.8, persist=True)

    # Check if there are detected keypoints
    if results and results[0].keypoints is not None:
        keypoints = results[0].keypoints.xy  # keypoints
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

            # Draw bounding box around the detected user
            x1, y1, x2, y2 = map(int, box)
            cv2.rectangle(calibrated_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)  

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
                       
            
            # Ensure facial keypoints (ear to ear normalized to the middle of the face)
            if kp is not None and len(kp) > 0:
                # Calculate the middle connected point
                if len(kp) > 4:
                    right_ear = kp[3] #right_eye = kp[1]
                    left_ear = kp[4] #left_eye = kp[2]
                    if right_ear[0] > 0 and left_ear[0] > 0: 
                        facial_point_x = (right_ear[0] + left_ear[0]) / 2
                        facial_point_y = (right_ear[1] + left_ear[1]) / 2
                        kp_facial_point = [facial_point_x, facial_point_y]
                     
                        kp = np.vstack([kp, kp_facial_point])  # Append facial as a new keypoint
                        idx_facial_point = len(kp) - 1  # Index of the new keypoint

                if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0:
                    SKELETON.append((idx_middle_shoulder, idx_facial_point))
                else:
                    cv2.putText(calibrated_frame, f"Make sure the camera can see all your face and shoulder keypoints!", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2) 
                    
                # Ensure keypoints for shoulders, nose, and ears 
                if len(kp) > 4:  
                    right_ear= kp[3]
                    left_ear = kp[4]
                    nose = kp[0]

                # Footage GUI
                # Draw skeleton connections
                for p1, p2 in SKELETON:
                    
                    if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0: #draw an extra inner outline between middle shoulder and facial point
                        cv2.line(calibrated_frame, (int(kp[idx_middle_shoulder][0]), int(kp[idx_middle_shoulder][1])), 
                            (int(kp[idx_facial_point][0]), int(kp[idx_facial_point][1])),
                            (0, 255, 0), 5)  # Green line
                        
                    if p1 < len(kp) and p2 < len(kp): #skeletons  
                        x1, y1 = kp[p1]
                        x2, y2 = kp[p2]
                        if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0: 
                            cv2.line(calibrated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 2) 
                    
                # Draw keypoints and display their names
                LEFT_KEYPOINTS = {2,4,6}   
                RIGHT_KEYPOINTS = {1,3,5} 

                for i, (x, y) in enumerate(kp):
                    if i < len(KEYPOINT_NAMES):
                        if x > 0 and y > 0: 
                            cv2.circle(calibrated_frame, (int(x), int(y)), 5, (0, 255, 0), -1)

                            # Offset x for left/right
                            if i in LEFT_KEYPOINTS:
                                text_x = int(x) - 55  # More space on left for names
                            elif i in RIGHT_KEYPOINTS:
                                text_x = int(x) + 5
                            else:
                                text_x = int(x)  # For center keypoints like nose

                            cv2.putText(calibrated_frame, KEYPOINT_NAMES[i], (text_x, int(y) - 5),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                            # Add Facial keypoint (ear to ear)
                            if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0:
                                cv2.circle(calibrated_frame, (int(kp_facial_point[0]), int(kp_facial_point[1])), 5, (0, 0, 255), -1)
                                cv2.putText(calibrated_frame, "Facial Point", (int(kp_facial_point[0]) - 5, int(kp_facial_point[1]) - 5), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                                # Add middle shoulder keypoint
                                cv2.circle(calibrated_frame, (int(kp_middle_shoulder[0]), int(kp_middle_shoulder[1])), 5, (0, 0, 255), -1)
                                cv2.putText(calibrated_frame, "Middle Shoulder", (int(kp_middle_shoulder[0]) - 5, int(kp_middle_shoulder[1]) - 5), 
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                #Posture Calibration 
                if right_ear[0] > 0 and left_ear[0] and right_shoulder[0] > 0 and left_shoulder[0] > 0:
                    idx_facial_point = len(kp) - 1
                    idx_middle_shoulder = len(kp) - 2
                    idx_facial_point = len(kp) - 1
                    idx_middle_shoulder = len(kp) - 2
                    left_shoulder_x, left_shoulder_y = kp[5] 
                    right_shoulder_x, right_shoulder_y = kp[6] 

                    
                    left_shoulder_x, left_shoulder_y = left_shoulder
                    right_shoulder_x, right_shoulder_y = right_shoulder
                    shoulder_distance = np.sqrt((left_shoulder_x - right_shoulder_x) ** 2 + (left_shoulder_y - right_shoulder_y) ** 2)

                    ideal_shoulder_distance = 360  #Average from 200 and 520 which is the average user min-max distance from camera

                    facial_point_x, facial_point_y = kp[-1]
                    middle_shoulder_x, middle_shoulder_y = kp[-2]
                    raw_calibrating_distance = np.sqrt((facial_point_x - middle_shoulder_x) ** 2 + (facial_point_y - middle_shoulder_y) ** 2)

                    #Scale posture distance based on shoulder distance
                    scaling_factor = ideal_shoulder_distance / shoulder_distance
                    calibrating_distance  = raw_calibrating_distance * scaling_factor

                    if default_calibrated_distance != 220:
                        default_calibrated_distance = load_best_distance() +10
                        


                    lower_limit = default_calibrated_distance * 0.95
                    upper_limit = default_calibrated_distance * 1.01  

                    # 6. Posture percentage calculation
                    if lower_limit <= calibrating_distance <= upper_limit:
                        posture_percentage = 100
                    elif calibrating_distance < lower_limit:
                        difference = lower_limit - calibrating_distance
                        posture_percentage = max(0, 100 - (difference / default_calibrated_distance) * 170)
                    elif calibrating_distance > upper_limit:
                        difference = calibrating_distance - upper_limit
                        posture_percentage = max(0, 100 - (difference / default_calibrated_distance) * 100)
                    else:
                        posture_percentage = 100

                
                    best_distance = calibrating_distance      
                               

                   
                    z_distance_text = f"z_distance: {shoulder_distance:.2f} px"  #show nomalized shoulders distance as text (distance from camera)
                    current_distance = f"Current Distance: {calibrating_distance:.2f} px" #show distance from facial point to middle shoulder as text

                    # Display posture grade
                    posture_text = ""
                    text_color = (255, 255, 255)
                    if posture_percentage >= 99:
                        posture_text = "Good Posture!"
                        text_color = (0, 255, 0)  # Green for perfect posture
                    elif posture_percentage >= 85:
                        posture_text = "Good Posture!"
                        text_color = (0, 255, 255)  # Yellow for good posture
                    else:
                        posture_text = "Bad Posture!"
                        text_color = (0, 165, 255)  # Orange for bad posture
                    
                    cv2.putText(calibrated_frame, "Sit with your back fully straightened!", (10, 25), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                    # Check if all facial and body parts are visible to the camera before show posture percentage
                    if right_ear[0] > 0 and left_ear[0] > 0 and nose[0] > 0: 
                        Facialbone = True
                    else:
                        Facialbone = False
                    
                    if right_shoulder[0] > 0 and left_shoulder[0] > 0: 
                        Bodybone = True
                    else:
                        Bodybone = False

                    # Display posture percentage and grade as texts
                    #if box_width > DISTANCE_THRESHOLD and Bodybone and Facialbone:
                    # Display the distance text near the middle of the bounding box
                    if Bodybone and Facialbone:
                        cv2.putText(calibrated_frame, z_distance_text, (int(middle_shoulder_x) + 0, int(middle_shoulder_y) + 20), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                        
                        cv2.putText(calibrated_frame, current_distance, (int(facial_point_x) + 0, int(facial_point_y) + 20), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                        cv2.putText(calibrated_frame, f"Posture Percentage: {int(posture_percentage)}%", (10, 50), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
                        cv2.putText(calibrated_frame, posture_text, (10, 80), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2) 

    return calibrated_frame

def release_calibrated_camera():
    global cap

    cap.release()
    cap = None

    if cap is None:
        cap = cv2.VideoCapture(0)

def save_best_distance(distance):
    distance = float(distance)
    
    file_path = 'best_distance.json'
    with open(file_path, 'w') as file:
        json.dump({"best_distance": distance}, file)
        print(f"Saved best distance: {distance} + 15")

def pressed_save():
    save_best_distance(best_distance)

