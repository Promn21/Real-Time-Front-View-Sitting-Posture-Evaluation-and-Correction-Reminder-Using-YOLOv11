import sys
import cv2
from pygrabber.dshow_graph import FilterGraph
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, 
                             QComboBox, QHBoxLayout, QMenu, QSystemTrayIcon, QCheckBox)
from PyQt6.QtGui import QImage, QPixmap, QFont, QFontDatabase, QIcon
from PyQt6.QtCore import QTimer, Qt, QEvent
import PyQt6.QtCore as QtCore
from PoseEstimation import  get_posture_frame, release_camera, set_notifications_enabled, load_best_distance
from CalibrationWindow import Calibration_Window

Calibrated = False

POSTURE_FILE = "user_posture.json"
best_distance = None

class PostureTapApp(QWidget):
    def __init__(self):
        super().__init__()
        self.app = QApplication([])
        self.init_ui()
        self.init_tray()
        self.calibration_window = Calibration_Window()
        self.calibration_window.calibration_done.connect(self.calibration_complete)

    def closeEvent(self, event):
        release_camera()
        self.timer.stop()


    def init_ui(self):
        """Initialize the main UI."""
        font_path = r"User Interface/Fredoka-VariableFont_wdth,wght.ttf"
        font_id = QFontDatabase.addApplicationFont(font_path)
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        app.setFont(QFont(font_family, 14))
        self.show()

        self.setWindowTitle("Correct Your Posture!")
        self.setGeometry(200, 200, 550, 450)
        self.setStyleSheet("background-color: #A2B800; color: white; font-size: 14px; font-weight: bold;")
        self.setFixedSize(663, 703)
        self.setWindowIcon(QIcon(r"User Interface/shrek.png"))

        # Center the window on the screen
        screen = QApplication.primaryScreen().geometry()
        window_rect = self.frameGeometry()
        window_rect.moveCenter(screen.center())
        self.move(window_rect.topLeft())

        # Title Layout (Text + Image)
        title_layout = QHBoxLayout()
        self.title_label = QLabel("PostureTap", self)
        self.title_label.setFont(QFont(font_family))
        self.title_label.setStyleSheet("font-size: 33px; font-weight: bold; color: white;")

        self.image_label = QLabel(self)
        pixmap = QPixmap(r"User Interface/shrek.png")
        pixmap = pixmap.scaled(50, 50, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.image_label)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Camera Device Label
        self.device_label = QLabel("Camera Device")
        self.device_label.setFont(QFont(font_family))
        self.device_label.setStyleSheet("font-size: 20px; font-weight: bold; color: yellow;")

        # Camera Dropdown
        self.camera_dropdown = QComboBox(self)
        self.camera_dropdown.setFont(QFont(font_family))
        self.camera_dropdown.setStyleSheet("background-color: white; color: #9fb3a4; padding: 5px; border-radius: 5px;")
        self.detect_cameras()

        # Start & Stop Buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")

        button_style = """
            QPushButton {
                background-color: #0078A0;
                color: white;
                padding: 10px;
                border-radius: 5px;
                border: 2px solid transparent;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f7f;
                border: 2px solid white;
            }
            QPushButton:pressed {
                background-color: #004c66;
            }
            QPushButton:focus {
                border: 2px solid yellow;
            }
        """

        stop_button_style = """
            QPushButton {
                background-color: #D32F2F;
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

        self.start_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(stop_button_style)

        self.start_button.clicked.connect(self.start_camera)
        self.stop_button.clicked.connect(self.stop_camera)

        self.start_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.stop_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Checkbox for enabling/disabling notifications
        self.notification_checkbox = QCheckBox("Enable Notifications", self)
        self.notification_checkbox.setChecked(True) 
        self.notification_checkbox.setFont(QFont(font_family))
        self.notification_checkbox.setStyleSheet("font-size: 18px; color: white;")
        self.notification_checkbox.stateChanged.connect(self.toggle_notifications)

        # Camera Feed Label
        self.camera_label = QLabel("How to use:\n" \
        "\n1. Sit comfy with back straighten, then hit Calibrate.\n" \
        "\n2. Tap Start after the calibration is done.\n" \
        "\n3. Minimize the app — it'll hang out in the tray.\n" \
        "\n4. It'll gently remind you if you start slouching.", self)
        self.camera_label.setFont(QFont(font_family))
        self.camera_label.setStyleSheet("font-size: 23px; color: white; background-color: black; border-radius: 10px;")
        self.camera_label.setFixedSize(640, 480)
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        camera_label_layout = QVBoxLayout()
        camera_label_layout.addWidget(self.camera_label)

        self.calibration_start = QPushButton("Start Calibration")
        self.calibration_confirm = QPushButton("This is my best posture")
        
        # Calibration buttons style
        calibration_button_style = """
            QPushButton {
                background-color: #0078A0;
                color: white;
                padding: 10px;
                border-radius: 5px;
                border: 2px solid transparent;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005f7f;
                border: 2px solid white;
            }
            QPushButton:pressed {
                background-color: #004c66;
            }
            QPushButton:focus {
                border: 2px solid yellow;
            }
        """

        calibration_confirm_style = """
            QPushButton {
                background-color: #D32F2F;
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

        self.calibration_start.setStyleSheet(calibration_button_style)
        self.calibration_confirm.setStyleSheet(calibration_confirm_style)

        self.calibration_start.clicked.connect(self.start_calibration)
        self.calibration_confirm.clicked.connect(self.calibration_complete)

        self.calibration_confirm.setVisible(False)
        self.calibration_confirm.setEnabled(False) 

        self.calibration_start.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.calibration_confirm.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        camera_label_layout.addWidget(self.calibration_start)
        camera_label_layout.addWidget(self.calibration_confirm)

        # Layouts
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(title_layout)
        main_layout.addWidget(self.device_label)
        main_layout.addWidget(self.camera_dropdown)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.notification_checkbox)
        main_layout.addLayout(camera_label_layout)

        self.setLayout(main_layout)

        # Timer for updating camera feed
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def init_tray(self):
        """Initialize the system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(r"User Interface/shrek.png"))
        self.tray_menu = QMenu()

        restore_action = self.tray_menu.addAction("Restore")
        exit_action = self.tray_menu.addAction("Exit")

        restore_action.triggered.connect(self.showNormal)
        exit_action.triggered.connect(self.close_application)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_click)
        self.tray_icon.show()

    def changeEvent(self, event: QEvent):
        """Detect window minimize and send to tray."""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.tray_icon.show()
                self.hide()
                self.tray_icon.showMessage("PostureTap", "Running in system tray", QSystemTrayIcon.MessageIcon.Information, 3000)
        super().changeEvent(event)

    def on_tray_icon_click(self, reason):
        """Restore window when clicking the tray icon."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_normal()

    def show_normal(self):
        """Restore the window from tray."""
        self.showNormal()
        self.activateWindow()

    def close_application(self):
        """Exit the application properly."""
        self.tray_icon.hide()
        release_camera() 
        self.close()

    def toggle_notifications(self, state):
        """Enable or disable notifications based on checkbox state."""
        enabled = self.notification_checkbox.isChecked()
        set_notifications_enabled(enabled) 

    def detect_cameras(self):
        """ Detect available cameras and list them in dropdown with real device names """
        self.camera_dropdown.clear()
        cameras = self.get_camera_names()
        if cameras:
            for index, name in cameras.items():
                self.camera_dropdown.addItem(name, index)
        else:
            self.camera_dropdown.addItem("No Camera Found", -1)

    def get_camera_names(self):
        devices = FilterGraph().get_input_devices()
        cameras = {}
        for device_index, device_name in enumerate(devices):
            cameras[device_index] = device_name
        return cameras

    def start_camera(self):
        """ Start the selected camera """
        global Calibrated
        if not Calibrated:
            self.camera_label.setText("No available height data, start the calibration first!")
            return
        
        release_camera()
        self.timer.start(30)  # Update every 30ms
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.calibration_start.setVisible(False)
        self.calibration_start.setEnabled(False)


    def stop_camera(self):
        """ Stop the camera feed """

        self.timer.stop()
        release_camera()
        self.camera_label.setText("Camera Device")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.calibration_start.setVisible(True)
        self.calibration_start.setEnabled(True)

    def start_calibration(self):
            """Starts the calibration process."""
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)

            self.calibration_start.setEnabled(False)
            self.calibration_start.setVisible(False)
            self.calibration_confirm.setEnabled(True)
            self.calibration_confirm.setVisible(True)
            
            self.calibration_window.show()
            self.calibration_window.start_Calibration_camera()

    def calibration_complete(self):
        """ Handle the completion of calibration """
        global Calibrated
        self.camera_label.setText("Calibration Completed, start your camera!")
        
        Calibrated = True
        load_best_distance()
        self.calibration_confirm.setVisible(False)
        self.calibration_start.setVisible(True)
        self.calibration_start.setEnabled(True)
        self.start_button.setEnabled(True)

    def update_frame(self):
        """ Capture and update the camera feed """
        frame = get_posture_frame()  # Get the processed frame from PoseEsimation.py
        if frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert frame to RGB
            h, w, ch = frame.shape
            qimg = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.camera_label.setPixmap(QPixmap.fromImage(qimg))
            
            self.camera_label.setPixmap(QPixmap.fromImage(qimg))
            self.camera_label.setScaledContents(True)  # Ensure it scales correctly



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PostureTapApp()
    window.show()
    c_window = Calibration_Window()
    c_window.hide()
    sys.exit(app.exec())
