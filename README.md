# PostureTap—Real-Time Front-View Sitting Posture Evaluation and Correction Reminder Using YOLOv11

This repository offers a custom-built, ***open-source application for real-time front-view sitting posture detection, evaluation, and correction reminder***, powered by [YOLOv11](https://github.com/ultralytics/ultralytics). It allows users to define and save their ideal sitting posture through a guided calibration process. Once calibrated, the system actively tracks the user's posture using keypoint analysis and compares it against their personalized benchmark. The goal is to deliver meaningful, user-specific feedback that encourages better posture habits and supports ergonomic well-being during prolonged sitting.

## Key Features
* **Buit With Python**: Developed in Python, leveraging OpenCV and GUI components for real-time posture feedback in a user-friendly environment.
* **YOLOv11 Pose Estimation**: Utilizes YOLOv11 to detect and analyze body keypoints with high precision for accurate assessment of sitting posture, usable with only a single webcam input.
* **Minimal Hardware Requirement**: No specialized hardware is needed as the application runs on standard front-view of laptop or desktop webcams.
* **Real-time Posture Detection**: Provides live feedback using a front-facing camera, making it ideal for everyday use at desks, in study areas, or at workstations.
* **Personalized Calibration Process**: Users calibrate their best posture through a guided setup. This generalized the system posture evaluation for diverse human's body type.
* **Posture Percentage Evaluation**: The application calculates a posture percentage score and classifies posture into three levels: Perfect  Good, and Bad Posture.
* **Correction Reminder**: If poor posture is detected, the app triggers motivational system notifications to remind users to sit properly.
* **Lightweight and Minimizable**: Minimal resource usage, with support for minimizing to the system tray for background running.

---


# Setup Instructions

## Prerequisites

* Python 3.11.x

## Installation Process  
  
1. `git clone .git`  
2. `python -m venv venv`  
3. `.\venv\scripts\activate.bat`  
4. `pip install -r requirements.txt`

## Run the program

`python PostureTap.py`

# About

This project was developed by [Suppawit Sontarat](https://github.com/Promn21). It was supervised by [Chatchai Wangwiwattana](https://github.com/redeian) as part of the final assignment at Faculty of Information and Communication Technology, Mahidol University (MUICT).

# License

PostureTap project is licensed under the MIT License. See the LICENSE file for details.
