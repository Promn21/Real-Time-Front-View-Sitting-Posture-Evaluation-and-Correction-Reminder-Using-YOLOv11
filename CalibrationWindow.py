#This Script create the Aplication User Interface to work together with import functions from the PoseEstimation.py
import sys
import cv2
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout)
from PyQt6.QtGui import QImage, QPixmap, QFont, QFontDatabase
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from UserCalibration import release_calibrated_camera, get_calibration_frame,pressed_save

POSTURE_FILE = "user_posture.json"
best_distance = None

class Calibration_Window(QWidget):
    calibration_done = pyqtSignal()
    calibration_ready = pyqtSignal()
    calibration_notready = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.hide()
        self.distance = None  # Or some default value
        self.calibrated_frame = None  # Or some default value
        #self.start_Calibration_camera() # for testing, comment this when finish the test


    def closeEvent(self, event):
        release_calibrated_camera()
        self.calibration_done.emit()
        self.timer.stop()


    def init_ui(self):
        """Initialize the main UI."""
        self.app = QApplication.instance()


        font_path = r"User Interface/Fredoka-VariableFont_wdth,wght.ttf"
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.app.setFont(QFont(font_family, 14))

        self.setWindowTitle("Decide Your Best Posture")
        self.setGeometry(200, 200, 550, 450)
        self.setStyleSheet("background-color: #A2B800; color: white; font-size: 14px; font-weight: bold;")
        self.setFixedSize(663, 580)

        # Center the window on the screen
        screen = QApplication.primaryScreen().geometry()
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen.center())
        self.move(window_rect.topLeft())

        # Camera Feed Label
        self.camera_label = QLabel("Wait A Moment...", self)
        self.camera_label.setFont(QFont(font_family))
        self.camera_label.setStyleSheet("font-size: 23px; color: white; background-color: black; border-radius: 10px;")
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        camera_label_layout = QVBoxLayout()
        camera_label_layout.addWidget(self.camera_label)

        self.calibration_confirm = QPushButton("Confirm Best Posture")
        self.calibration_confirm.clicked.connect(self.stop_Calibration_camera)

        calibration_confirm_style = """
            QPushButton {
                background-color: #0078A0;
                color: white;
                padding: 10px;
                border-radius: 5px;
                border: 2px solid transparent;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a82828;
                border: 2px solid white;
            }
            QPushButton:pressed {
                background-color: #8b1e1e;
            }
            QPushButton:focus {
                border: 2px solid yellow;
            }
        """

        self.calibration_confirm.setStyleSheet(calibration_confirm_style)
        self.calibration_confirm.clicked.connect(self.stop_Calibration_camera)

        self.calibration_confirm.setVisible(True)
        self.calibration_confirm.setEnabled(True) 

        self.calibration_confirm.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        camera_label_layout.addWidget(self.calibration_confirm)
        

        # Layouts
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        main_layout.addLayout(camera_label_layout)

        # Timer for updating camera feed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_Calibration_frame)

        
    def start_Calibration_camera(self):
        """ Start the selected camera """
        self.show()
        self.camera_label.setText("Wait A Moment...")
        release_calibrated_camera()
        self.timer.start(30)  # Update every 30ms

    def update_Calibration_frame(self):
        """ Capture and update the camera feed """
        frame_calibration = get_calibration_frame()

        if frame_calibration is not None:
            frame_calibration = cv2.cvtColor(frame_calibration, cv2.COLOR_BGR2RGB)  
            h, w, ch = frame_calibration.shape
            qimg = QImage(frame_calibration.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.camera_label.setPixmap(QPixmap.fromImage(qimg))
    

    def stop_Calibration_camera(self):
        """ Stop the camera feed """
        pressed_save()
        self.timer.stop()
        self.camera_label.setText("Best Posture Saved, Start the Application Anytime!")
        release_calibrated_camera()
        self.close()
        self.calibration_done.emit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    c_window= Calibration_Window()
    c_window.show()
    sys.exit(app.exec())

