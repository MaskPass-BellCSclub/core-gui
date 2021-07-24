from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import cv2
from flask import Flask, Response
import time
import threading
import multiprocessing
import urllib
import json

camMult = 2

flaskServer = Flask(__name__)
camera = cv2.VideoCapture(0)
img = None

def video_thread(camera):
    while True:
        global img
        ret, img = camera.read()
        
def start_flask_server():
    camThread = threading.Thread(target=video_thread, args=(camera,))
    camThread.setDaemon(True)
    camThread.start()
    flaskServer.run(host='0.0.0.0', port="5510")

@flaskServer.route('/')
def index():
    return "Camera Server Active."

def generate_frame():
    while True:
        time.sleep(0.02)
        # ret, jpg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        ret, jpg = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        frame = jpg.tobytes()
        yield (b'--frame\r\n'
           b'Content-Type:image/jpeg\r\n'
           b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n'
           b'\r\n' + frame + b'\r\n')

@flaskServer.route('/status')
def status_check():
    global img
    if img is not None:
        return Response(status=200)
    else:
        return Response(status=503)

@flaskServer.route('/stream.mjpg')
def video_feed():
    return Response(generate_frame(), mimetype='multipart/x-mixed-replace; boundary=frame')

    
class videoThread(QThread):
    changePixmap = pyqtSignal(QImage)

    def __init__(self,_,address):
        super(videoThread,self).__init__()
        self.address = address
    
    def run(self):
        cap = cv2.VideoCapture(self.address)
        while True:
            ret, frame = cap.read()
            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbImage.shape
                bytesPerLine = ch * w
                convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
                p = convertToQtFormat.scaled(640*camMult, 480*camMult, Qt.KeepAspectRatio)
                self.changePixmap.emit(p)

class CameraDisplay(QWidget):
    def __init__(self):
        super().__init__()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    def initUI(self, cameraIp, statusText = None):
        self.statusText = statusText
        self.setWindowTitle("AI Camera Stream")
        self.resize(1800, 1200)
        # create a label
        self.label = QLabel(self)
        # self.label.move(0,0)
        self.label.resize(640*camMult, 480*camMult)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label.setAlignment(Qt.AlignCenter)
        

        self.layout = QGridLayout()
        self.layout.addWidget(self.label, 0, 0)
        self.setLayout(self.layout)
        
        th = videoThread(self, cameraIp + "/video_feed")
        th.changePixmap.connect(self.setImage)
        th.start()
        self.show()
        
    def closeEvent(self, event):
        if self.statusText:
            self.statusText.setText("VIDEO DISPLAY: EXITED")
            self.statusText.setStyleSheet("color: red")
        event.accept()
        
class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Control Panel")
        self.setMinimumWidth(250)
        self.titleText = QLabel("MaskPass Control Pannel")
        
        self.serverIp = QLineEdit("http://mc.ai1to1.com:5000")
        
        self.cameraToggle = QPushButton("Start Camera Server")
        self.cameraToggle.clicked.connect(self.toggleCamera)
        self.cameraStatus = QLabel("CAMERA: OFFLINE")
        self.cameraStatus.setStyleSheet("color: red")
        
        self.aiToggle = QPushButton("Send Start Command to AI Server")
        self.aiToggle.clicked.connect(self.toggleAi)
        self.aiStatus = QLabel("AI SERVER: OFFLINE")
        self.aiStatus.setStyleSheet("color: red")
        
        self.arduinoToggle = QPushButton("Start Arduino Service")
        self.arduinoToggle.clicked.connect(self.toggleArduino)
        self.arduinoStatus = QLabel("ARDUINO SERVICE: OFFLINE")
        self.arduinoStatus.setStyleSheet("color: red")
        
        self.videoToggle = QPushButton("Start Video Service")
        self.videoToggle.clicked.connect(self.toggleVideo)
        self.videoStatus = QLabel("VIDEO DISPLAY: OFFLINE")
        self.videoStatus.setStyleSheet("color: red")
        
        self.stopServerToggle = QPushButton("Stop AI Server")
        self.stopServerToggle.clicked.connect(self.stopServer)
        self.stopServerToggle.setStyleSheet("background-color: red")
        
        self.exitToggle = QPushButton("EXIT")
        self.exitToggle.clicked.connect(self.toggleExit)
        self.exitToggle.setStyleSheet("background-color: red")
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.titleText)
        self.layout.addWidget(self.serverIp)
        self.layout.addWidget(self.cameraToggle)
        self.layout.addWidget(self.cameraStatus)
        self.layout.addWidget(self.aiToggle)
        self.layout.addWidget(self.aiStatus)
        self.layout.addWidget(self.arduinoToggle)
        self.layout.addWidget(self.arduinoStatus)
        self.layout.addWidget(self.videoToggle)
        self.layout.addWidget(self.videoStatus)
        self.layout.addWidget(self.stopServerToggle)
        self.layout.addWidget(self.exitToggle)
        self.setLayout(self.layout)
        self.show()
        
    def toggleCamera(self):
        self.cameraStatus.setText("CAMERA: LOADING")
        self.cameraStatus.setStyleSheet("color: orange")
        self.repaint()
        try:
            flaskThread = multiprocessing.Process(target=start_flask_server)
            flaskThread.start()
            while True:
                try:
                    with urllib.request.urlopen("http://localhost:5510/status") as url:
                        print(url)
                        if url.status == 200:
                            break
                except Exception as e:
                    print(e)
                    
            self.cameraStatus.setText("CAMERA: ONLINE")
            self.cameraStatus.setStyleSheet("color: green")
                
        except Exception as e:
            print(e)
            self.cameraStatus.setText("CAMERA: FAILED")
            self.cameraStatus.setStyleSheet("color: red")
        
    def toggleAi(self):
        self.aiStatus.setText("AI SERVER: LOADING")
        self.aiStatus.setStyleSheet("color: orange")
        self.repaint()
        
        try:
            external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')

            req = urllib.request.Request(self.serverIp.text() + "/start_ai")
            req.add_header('Content-Type', 'application/json; charset=utf-8')
            jsondata = json.dumps({'camera': "http://" + external_ip + ":5510" + "/stream.mjpg"})
            jsondataasbytes = jsondata.encode('utf-8')   # needs to be bytes
            req.add_header('Content-Length', len(jsondataasbytes))
            
            with urllib.request.urlopen(req, jsondataasbytes) as url:
                if url.status != 200:
                    raise Exception(url.status)
                    
            self.aiStatus.setText("AI SERVER: ONLINE")
            self.aiStatus.setStyleSheet("color: green")
                
        except Exception as e:
            print(e)
            self.aiStatus.setText("AI SERVER: FAILED")
            self.aiStatus.setStyleSheet("color: red")
            
    def toggleArduino(self):
        self.arduinoStatus.setText("ARDUINO SERVICE: LOADING")
        self.arduinoStatus.setStyleSheet("color: orange")
        self.repaint()
        arduinoThread = threading.Thread(target=arduinoHandler, args=(self.serverIp.text(),))
        arduinoThread.setDaemon(True)
        arduinoThread.start()
        self.arduinoStatus.setText("ARDUINO SERVICE: ONLINE")
        self.arduinoStatus.setStyleSheet("color: green")
        
    def toggleVideo(self):
        self.videoStatus.setText("VIDEO DISPLAY: LOADING")
        self.videoStatus.setStyleSheet("color: orange")
        self.repaint()
        self.cameraService = CameraDisplay()
        self.cameraService.initUI(self.serverIp.text(), statusText = self.videoStatus)
        self.cameraService.show()
        self.videoStatus.setText("VIDEO DISPLAY: ONLINE")
        self.videoStatus.setStyleSheet("color: green")
        
    def stopServer(self):
        with urllib.request.urlopen(self.serverIp.text() + "/stop") as url:
            pass
        
    def toggleExit(self):
        time.sleep(1)
        sys.exit(0)
        

# FILL IN THE CODE HERE!
def arduino_open_door():
    print("DOOR OPEN")
    time.sleep(5) # remove this. this is to emulate a door opening
    pass
        
def arduino_close_door():
    print("DOOR CLOSE")
    time.sleep(5) # remove this. this is to emulate a door closing
    pass
        
def arduinoHandler(serverIp):
    while True:
        try:
            time.sleep(1)
            with urllib.request.urlopen(serverIp + "/open_door") as url:
                if url.status == 200:
                    res = url.read().decode('utf-8')
                    if res == "True":
                        arduino_open_door()
                        time.sleep(5)
                        arduino_close_door()
                    else:
                        pass
                else:
                    raise Exception(url.status)
        except Exception as e:
            print(e)
        
if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    runApp = ControlPanel()
    runApp.show()
    sys.exit(app.exec_()) 