import sys
import cv2
import mediapipe as mp
import keyboard
import json
import os
import time
import signal
import math
import matplotlib
matplotlib.use('Agg') # GUI thread dışında güvenli grafik oluşturma için
import matplotlib.pyplot as plt
from datetime import datetime
from win10toast import ToastNotifier
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                             QSystemTrayIcon, QMenu, QStyle, QSlider, QPushButton, QHBoxLayout, QFormLayout, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint, QTimer, QObject
from PyQt6.QtGui import QImage, QPixmap
import sqlite3
import winreg
from ctypes import windll, Structure, c_long, byref

class RECT(Structure):
    _fields_ = [("left", c_long), ("top", c_long), ("right", c_long), ("bottom", c_long)]

LANGUAGES = {
    "tr": {
        "status_great": "DURUŞUN HARİKA", "status_fix": "DURUŞU DÜZELT", "status_head_up": "BAŞINI KALDIR!",
        "status_straight": "DİK DUR!", "status_too_close": "YAKIN DURMA!", "status_tilt": "YAMUK OTURMA!",
        "status_calibrate": "F8 İLE KALİBRE ET", "status_waiting": "KULLANICI BEKLENİYOR...",
        "eye_break": "GÖZ DİNLENDİRME", "body_break": "HAREKET ZAMANI!", "water_break": "💧 SU İÇME VAKTİ!",
        "settings_saved": "AYARLAR KAYDEDİLDİ!", "game_mode_on": "Oyun Modu Aktif: Sessiz Takip",
        "game_summary_title": "Maç Sonu Raporu", "game_summary_msg": "Sürenin %{0} kadarında duruşun bozuktu. Mola verelim mi?",
        "tray_ghost": "Ghost Mode Aç/Kapat", "tray_cam": "Kamera Görünümü Aç/Kapat", "tray_eye": "Göz Sağlığı Takibi",
        "tray_body": "Mola Hatırlatıcı", "tray_stats": "Anlık İstatistikler", "tray_settings": "Ayarlar",
        "tray_calibrate": "F8: Kalibre Et", "tray_quit": "Çıkış (F9)", "report_title": "Bugünün Raporu Hazır",
        "stats_title": "Anlık İstatistikler", "stats_session": "--- ŞU ANKİ OTURUM ---",
        "stats_total": "Toplam Süre", "stats_active": "Aktif Çalışma", "stats_away": "Masada Değil",
        "stats_ratio": "Dik Duruş Oranı", "stats_details": "--- BUGÜNÜN DETAYLARI ---",
        "stats_kambur": "Kambur", "stats_boyun": "Boyun Önde", "stats_yanal": "Yanal Eğilme",
        "stats_yakin": "Çok Yakın", "stats_history": "--- GEÇMİŞ KIYASLAMA ---",
        "stats_yesterday": "Dünkü Başarı", "stats_weekly": "7 Günlük Ort", "stats_congrats": "🌟 Ortalamanın üzerindesin!",
        "stats_work": "💪 Biraz daha dik durabilirsin!", "settings_title": "Ayarlar", "settings_kambur": "Kambur Hassasiyeti:",
        "settings_boyun": "Boyun Hassasiyeti:", "settings_yakin": "Yakınlık Hassasiyeti:", "settings_yanal": "Yanal Eğilme Hassasiyeti:",
        "settings_delay": "Uyarı Gecikmesi (sn):", "settings_startup": "Sistem Başlangıcında Çalıştır",
        "settings_eye": "Göz Sağlığı (20-20-20)", "settings_body": "Mola Hatırlatıcı (50dk/5dk)",
        "settings_game": "Otomatik Oyun Modu", "settings_lang": "Dil (Language):", "settings_save": "Ayarları Kaydet"
    },
    "en": {
        "status_great": "POSTURE IS GREAT", "status_fix": "CORRECT POSTURE", "status_head_up": "HEAD UP!",
        "status_straight": "SIT STRAIGHT!", "status_too_close": "DON'T SIT TOO CLOSE!", "status_tilt": "DON'T TILT!",
        "status_calibrate": "CALIBRATE WITH F8", "status_waiting": "WAITING FOR USER...",
        "eye_break": "EYE RELAXATION", "body_break": "TIME TO MOVE!", "water_break": "💧 WATER TIME!",
        "settings_saved": "SETTINGS SAVED!", "game_mode_on": "Game Mode Active: Silent Tracking",
        "game_summary_title": "Match Summary", "game_summary_msg": "Posture was bad for %{0} of the session. Take a break?",
        "tray_ghost": "Toggle Ghost Mode", "tray_cam": "Toggle Camera View", "tray_eye": "Toggle Eye Health",
        "tray_body": "Toggle Body Break", "tray_stats": "Live Statistics", "tray_settings": "Settings",
        "tray_calibrate": "F8: Calibrate Now", "tray_quit": "Quit (F9)", "report_title": "Daily Report Ready",
        "stats_title": "Live Statistics", "stats_session": "--- CURRENT SESSION ---",
        "stats_total": "Total Time", "stats_active": "Active Work", "stats_away": "Away from Desk",
        "stats_ratio": "Straight Posture Ratio", "stats_details": "--- TODAY'S DETAILS ---",
        "stats_kambur": "Slouching", "stats_boyun": "Neck Forward", "stats_yanal": "Lateral Tilt",
        "stats_yakin": "Too Close", "stats_history": "--- HISTORY COMPARISON ---",
        "stats_yesterday": "Yesterday's Success", "stats_weekly": "7-Day Avg", "stats_congrats": "🌟 Above average today!",
        "stats_work": "💪 You can sit straighter!", "settings_title": "Settings", "settings_kambur": "Slouch Sensitivity:",
        "settings_boyun": "Neck Sensitivity:", "settings_yakin": "Proximity Sensitivity:", "settings_yanal": "Tilt Sensitivity:",
        "settings_delay": "Alert Delay (sec):", "settings_startup": "Run on Startup",
        "settings_eye": "Eye Health (20-20-20)", "settings_body": "Body Break (50min/5min)",
        "settings_game": "Auto Game Mode", "settings_lang": "Language (Dil):", "settings_save": "Save Settings"
    }
}

def is_fullscreen_app():
    try:
        hwnd = windll.user32.GetForegroundWindow()
        if not hwnd: return False
        rect = RECT()
        windll.user32.GetWindowRect(hwnd, byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        # Get primary screen resolution
        screen_w = windll.user32.GetSystemMetrics(0)
        screen_h = windll.user32.GetSystemMetrics(1)
        # Check if window is full screen size (or very close)
        return width >= screen_w - 5 and height >= screen_h - 5 and rect.top <= 5 and rect.left <= 5
    except: return False

# --- AYARLAR ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = "settings.json"
REPORTS_DIR = "reports"
toaster = ToastNotifier()

if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

class AppSignals(QObject):
    quit_signal = pyqtSignal()
    calibrate_signal = pyqtSignal()

signals = AppSignals()

def init_db():
    conn = sqlite3.connect("posture_history.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            active_seconds REAL,
            away_seconds REAL,
            dik_durus REAL,
            kambur REAL,
            boyun_onde REAL,
            cok_yakin REAL
        )
    ''')
    try:
        cursor.execute("ALTER TABLE daily_stats ADD COLUMN yanal_egilme REAL DEFAULT 0")
    except:
        pass # Sütun zaten varsa hata vermesini önler
    conn.commit()
    conn.close()

init_db()

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
    except: pass

def load_settings():
    default_settings = {
        "ideal_y": None, "ideal_neck_dist": None, "ideal_eye_dist": None, "ideal_neck_y": None,
        "kambur_sens": 8, "boyun_sens": 8, "yakin_sens": 5, "yanal_sens": 5, "alert_delay": 3,
        "startup": False, "eye_health": True, "body_break": True, "game_mode_auto": True, "language": "tr"
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                default_settings.update(data)
                return default_settings
        except: pass
    return default_settings

def set_startup(status):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "SmartPostureAI"
    # Python executable (pythonw.exe for silent start) and script path
    executable = sys.executable.replace("python.exe", "pythonw.exe")
    app_path = f'"{executable}" "{os.path.abspath(sys.argv[0])}"'
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if status:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError: pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Startup Error: {e}")
        return False

class PoseWorker(QThread):
    status_signal = pyqtSignal(str, str)
    frame_signal = pyqtSignal(object)
    hp_signal = pyqtSignal(int)
    water_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.running = True
        settings = load_settings()
        self.ideal_y = settings.get("ideal_y")
        self.ideal_neck_dist = settings.get("ideal_neck_dist")
        self.ideal_eye_dist = settings.get("ideal_eye_dist")
        self.ideal_neck_y = settings.get("ideal_neck_y")
        
        # Dinamik Hassasiyetler
        self.kambur_sens = settings.get("kambur_sens", 8) / 100
        self.boyun_sens = settings.get("boyun_sens", 8) / 100
        self.yakin_sens = settings.get("yakin_sens", 5) / 100
        self.yanal_sens = settings.get("yanal_sens", 5) / 100
        self.alert_delay = settings.get("alert_delay", 3)
        
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(model_complexity=0, min_detection_confidence=0.5)
        
        self.last_data = {"y": 0.7, "neck_dist": 0.1, "eye": 0.05, "neck_y": 0.15}
        self.bad_posture_start = None
        self.last_toast_time = 0
        self.stats = {"Dik Duruş": 0, "Kambur": 0, "Boyun Önde": 0, "Çok Yakın": 0, "Yanal Eğilme": 0, "Masada Değil": 0}
        self.total_active_seconds = 0
        self.total_away_seconds = 0
        self.ghost_mode = False
        self.show_camera = False
        
        # Göz Sağlığı (20-20-20) Değişkenleri
        self.eye_health_active = settings.get("eye_health", True)
        self.last_eye_break_time = time.time()
        self.is_in_eye_break = False
        self.eye_break_start_time = 0
        
        # Mola Hatırlatıcı (Body Break)
        self.body_break_active = settings.get("body_break", True)
        self.last_body_break_time = time.time()
        self.is_in_body_break = False
        self.body_break_start_time = 0

        # Yeni Özellikler
        self.hp = 100
        self.last_water_time = time.time()
        self.water_interval = 3600 # 1 saat (saniye)
        self.skeleton_mode = settings.get("skeleton_mode", False)
        self.last_status = "BAŞLATILIYOR..."

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        while self.running and cap.isOpened():
            success, frame = cap.read()
            if not success: continue
            
            # --- SU HATIRLATICI KONTROLÜ ---
            if time.time() - self.last_water_time >= self.water_interval:
                self.water_signal.emit()
                self.last_water_time = time.time()

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image_rgb)
            
            # İskelet Modu için siyah ekran hazırla
            if self.skeleton_mode:
                display_frame = frame.copy()
                display_frame.fill(0) # Siyah ekran
            else:
                display_frame = frame

            is_present = False
            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                if lm[11].visibility > 0.5 and lm[12].visibility > 0.5:
                    is_present = True
                
                if self.show_camera:
                    self.mp_drawing.draw_landmarks(display_frame, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                    self.frame_signal.emit(display_frame)

            if is_present:
                lm = results.pose_landmarks.landmark
                curr_y = (lm[11].y + lm[12].y) / 2
                curr_neck_dist = math.sqrt((lm[7].x - lm[11].x)**2 + (lm[7].y - lm[11].y)**2)
                curr_neck_y = abs(lm[7].y - lm[11].y)
                curr_eye_dist = math.sqrt((lm[2].x - lm[5].x)**2 + (lm[2].y - lm[5].y)**2)
                
                self.last_data = {"y": curr_y, "neck_dist": curr_neck_dist, "eye": curr_eye_dist, "neck_y": curr_neck_y}

                # --- GÖZ SAĞLIĞI KONTROLÜ ---
                if self.eye_health_active:
                    now = time.time()
                    if not self.is_in_eye_break:
                        # 20 dakika (1200 saniye) doldu mu?
                        if now - self.last_eye_break_time >= 1200:
                            self.is_in_eye_break = True
                            self.eye_break_start_time = now
                    else:
                        elapsed_break = now - self.eye_break_start_time
                        if elapsed_break >= 20: # 20 saniye mola bitti
                            self.is_in_eye_break = False
                            self.last_eye_break_time = now
                        else:
                            self.status_signal.emit(f"{LANGUAGES[self.lang]['eye_break']} ({int(20-elapsed_break)}s)", "blue")
                            self.msleep(200)
                            continue

                # --- MOLA HATIRLATICI KONTROLÜ ---
                if self.body_break_active:
                    now = time.time()
                    if not self.is_in_body_break:
                        # 50 dakika (3000 saniye) doldu mu?
                        if now - self.last_body_break_time >= 3000:
                            self.is_in_body_break = True
                            self.body_break_start_time = now
                    else:
                        elapsed_body = now - self.body_break_start_time
                        if elapsed_body >= 300: # 5 dakika (300s) mola bitti
                            self.is_in_body_break = False
                            self.last_body_break_time = now
                        else:
                            self.status_signal.emit(f"{LANGUAGES[self.lang]['body_break']} ({int((300-elapsed_body)/60)}m)", "blue")
                            self.msleep(200)
                            continue

                if self.ideal_y is not None:
                    is_kambur = curr_y > (self.ideal_y + self.kambur_sens)
                    is_boyun = (curr_neck_dist > (self.ideal_neck_dist + self.boyun_sens)) or \
                               (curr_neck_y < (self.ideal_neck_y - self.boyun_sens))
                    is_yakin = curr_eye_dist > (self.ideal_eye_dist + self.yakin_sens)
                    is_yanal = abs(lm[11].y - lm[12].y) > self.yanal_sens

                    self.total_active_seconds += 0.2
                    if is_yakin: status = "Çok Yakın"
                    elif is_yanal: status = "Yanal Eğilme"
                    elif is_boyun: status = "Boyun Önde"
                    elif is_kambur: status = "Kambur"
                    else: status = "Dik Duruş"
                    self.stats[status] += 0.2

                    if is_kambur or is_boyun or is_yakin or is_yanal:
                        if self.bad_posture_start is None: self.bad_posture_start = time.time()
                        elapsed = time.time() - self.bad_posture_start
                        if elapsed >= self.alert_delay:
                            msg = LANGUAGES[self.lang]['status_tilt'] if is_yanal else (LANGUAGES[self.lang]['status_head_up'] if is_boyun else (LANGUAGES[self.lang]['status_too_close'] if is_yakin else LANGUAGES[self.lang]['status_straight']))
                            self.status_signal.emit(msg, "red")
                            if self.ghost_mode and (time.time() - self.last_toast_time > 10):
                                toaster.show_toast("Smart Posture AI", msg, duration=3, threaded=True)
                                self.last_toast_time = time.time()
                        else:
                            self.status_signal.emit(f"{LANGUAGES[self.lang]['status_fix']} ({int(self.alert_delay-elapsed)}s)", "yellow")
                    else:
                        self.bad_posture_start = None
                        self.status_signal.emit(LANGUAGES[self.lang]['status_great'], "green")
                        if self.hp < 100: self.hp += 0.5
                    
                    # HP Güncelleme (Hatalı duruşta düşer)
                    if is_kambur or is_boyun or is_yakin or is_yanal:
                        self.hp -= 0.2
                    
                    self.hp = max(0, min(100, self.hp))
                    self.hp_signal.emit(int(self.hp))
                else:
                    self.status_signal.emit(LANGUAGES[self.lang]['status_calibrate'], "yellow")
            else:
                self.total_away_seconds += 0.2
                self.stats["Masada Değil"] += 0.2
                self.status_signal.emit(LANGUAGES[self.lang]['status_waiting'], "gray")
                self.bad_posture_start = None
                if self.show_camera:
                    self.frame_signal.emit(frame)

            self.msleep(200)
        cap.release()

    def calibrate(self):
        self.ideal_y = self.last_data["y"]
        self.ideal_neck_dist = self.last_data["neck_dist"]
        self.ideal_eye_dist = self.last_data["eye"]
        self.ideal_neck_y = self.last_data["neck_y"]
        
        current_settings = load_settings()
        current_settings.update({
            "ideal_y": self.ideal_y, "ideal_neck_dist": self.ideal_neck_dist, 
            "ideal_eye_dist": self.ideal_eye_dist, "ideal_neck_y": self.ideal_neck_y
        })
        save_settings(current_settings)
        return True

    def save_to_db(self):
        try:
            conn = sqlite3.connect("posture_history.db")
            cursor = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO daily_stats (date, active_seconds, away_seconds, dik_durus, kambur, boyun_onde, cok_yakin, yanal_egilme)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (today, self.total_active_seconds, self.total_away_seconds, 
                  self.stats["Dik Duruş"], self.stats["Kambur"], self.stats["Boyun Önde"], self.stats["Çok Yakın"], self.stats["Yanal Eğilme"]))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB Kayıt Hatası: {e}")

    def generate_final_report(self):
        self.save_to_db() # Rapor üretilirken veritabanına da kaydet
        total_time = self.total_active_seconds + self.total_away_seconds
        if total_time < 2: return
        def format_time(seconds):
            m, s = divmod(int(seconds), 60); return f"{m}dk {s}sn"
        labels, sizes = list(self.stats.keys()), list(self.stats.values())
        fig, ax = plt.subplots(figsize=(12, 7)); plt.subplots_adjust(right=0.7)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c', '#f1c40f', '#3498db', '#8e44ad', '#95a5a6'], startangle=140)
        info_text = f"TOPLAM: {format_time(total_time)}\nAKTIF: {format_time(self.total_active_seconds)}\nUZAK: {format_time(self.total_away_seconds)}"
        plt.text(1.35, 0.5, info_text, transform=ax.transAxes, fontsize=11, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
        report_path = os.path.join(REPORTS_DIR, f"rapor_{datetime.now().strftime('%Y%m%d_%H%M')}.png")
        plt.savefig(report_path, bbox_inches='tight'); plt.close()
        return report_path

class SummaryWindow(QWidget):
    def __init__(self, report_path, on_close_callback):
        super().__init__()
        self.on_close_callback = on_close_callback
        self.setWindowTitle("Smart Posture AI - Günlük Raporunuz")
        self.setFixedSize(850, 650)
        self.setStyleSheet("background-color: #1a1a1a; color: white; font-family: 'Segoe UI';")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        
        title = QLabel("🎉 Tebrikler! Bugünün Raporu Hazır")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px; color: #2ecc71;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.img_label = QLabel()
        pixmap = QPixmap(report_path)
        self.img_label.setPixmap(pixmap.scaled(800, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.img_label)

        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Raporu Kapat ve Çık")
        close_btn.setStyleSheet("background-color: #e74c3c; padding: 12px; font-weight: bold; border-radius: 8px; font-size: 16px;")
        close_btn.clicked.connect(self.close_and_exit)
        
        folder_btn = QPushButton("Raporlar Klasörünü Aç")
        folder_btn.setStyleSheet("background-color: #3498db; padding: 12px; font-weight: bold; border-radius: 8px; font-size: 16px;")
        folder_btn.clicked.connect(lambda: os.startfile(os.path.abspath(REPORTS_DIR)))

        btn_layout.addWidget(folder_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def close_and_exit(self):
        self.close()
        self.on_close_callback()

class CameraWindow(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.setWindowTitle("Smart Posture AI - Kamera Görünümü")
        self.setFixedSize(640, 480)
        self.layout = QVBoxLayout()
        self.image_label = QLabel("Kamera Yükleniyor...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)
        
        self.mode_btn = QPushButton("Görünüm Değiştir (Kamera/İskelet)")
        self.mode_btn.setStyleSheet("background-color: #34495e; padding: 8px; font-weight: bold; border-radius: 5px;")
        self.mode_btn.clicked.connect(self.toggle_skeleton)
        self.layout.addWidget(self.mode_btn)

        self.setLayout(self.layout)
        self.setStyleSheet("background-color: #1a1a1a; color: white;")

    def toggle_skeleton(self):
        self.parent_app.worker.skeleton_mode = not self.parent_app.worker.skeleton_mode
        # Ayarlara kaydet
        s = load_settings()
        s["skeleton_mode"] = self.parent_app.worker.skeleton_mode
        save_settings(s)

    def update_image(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.image_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
        return QPixmap.fromImage(p)

class StatsWindow(QWidget):
    def __init__(self, worker, lang):
        super().__init__()
        self.worker = worker
        self.lang = lang
        self.setWindowTitle(LANGUAGES[self.lang]['stats_title'])
        self.setFixedSize(400, 380)
        self.layout = QVBoxLayout()
        self.stats_label = QLabel("Veriler Hesaplanıyor...")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.stats_label.setStyleSheet("font-family: 'Segoe UI'; font-size: 13px; padding: 15px;")
        self.layout.addWidget(self.stats_label)
        self.setLayout(self.layout)
        self.setStyleSheet("background-color: #2c3e50; color: white;")
        
        # Saniyede bir güncelle
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start(1000)

    def get_historical_stats(self):
        yesterday_avg = 0
        weekly_avg = 0
        try:
            conn = sqlite3.connect("posture_history.db")
            cursor = conn.cursor()
            
            # Dünkü başarı oranı
            cursor.execute('''
                SELECT (dik_durus / active_seconds) * 100 
                FROM daily_stats 
                WHERE date(date) = date('now', '-1 day', 'localtime')
                AND active_seconds > 60
                ORDER BY id DESC LIMIT 1
            ''')
            row = cursor.fetchone()
            if row: yesterday_avg = row[0]

            # Son 7 günlük ortalama
            cursor.execute('''
                SELECT AVG(dik_durus / active_seconds) * 100 
                FROM daily_stats 
                WHERE date(date) >= date('now', '-7 days', 'localtime')
                AND active_seconds > 60
            ''')
            row = cursor.fetchone()
            if row and row[0]: weekly_avg = row[0]
            
            conn.close()
        except: pass
        return yesterday_avg, weekly_avg

    def refresh_stats(self):
        def format_time(seconds):
            m, s = divmod(int(seconds), 60); return f"{m}dk {s}sn"
        
        total_active = self.worker.total_active_seconds
        away_time = self.worker.total_away_seconds
        total_time = total_active + away_time
        
        if total_active > 0:
            dik_oran = (self.worker.stats["Dik Duruş"] / total_active) * 100
        else:
            dik_oran = 0
            
        yesterday, weekly = self.get_historical_stats()
        texts = LANGUAGES[self.lang]

        text = f"{texts['stats_session']}\n\n"
        text += f"{texts['stats_total']}: {format_time(total_time)}\n"
        text += f"{texts['stats_active']}: {format_time(total_active)}\n"
        text += f"{texts['stats_away']}: {format_time(away_time)}\n"
        text += f"{texts['stats_ratio']}: %{dik_oran:.1f}\n\n"
        
        text += f"{texts['stats_details']}\n"
        text += f"{texts['stats_kambur']}: {format_time(self.worker.stats['Kambur'])}\n"
        text += f"{texts['stats_boyun']}: {format_time(self.worker.stats['Boyun Önde'])}\n"
        text += f"{texts['stats_yanal']}: {format_time(self.worker.stats['Yanal Eğilme'])}\n"
        text += f"{texts['stats_yakin']}: {format_time(self.worker.stats['Çok Yakın'])}\n\n"

        text += f"{texts['stats_history']}\n\n"
        text += f"{texts['stats_yesterday']}: %{yesterday:.1f}\n"
        text += f"{texts['stats_weekly']}: %{weekly:.1f}\n\n"
        
        if dik_oran > weekly and weekly > 0:
            text += texts['stats_congrats']
        elif weekly > 0:
            text += texts['stats_work']
        
        self.stats_label.setText(text)

class SettingsWindow(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        settings = load_settings()
        self.lang = settings.get("language", "tr")
        self.setWindowTitle(LANGUAGES[self.lang]['settings_title'])
        self.setFixedSize(380, 520)
        self.layout = QVBoxLayout()
        self.form = QFormLayout()
        self.setStyleSheet("background-color: #2c3e50; color: white; font-family: 'Segoe UI';")

        texts = LANGUAGES[self.lang]

        # Sliders
        self.kambur_slider = self.create_slider(1, 20, settings["kambur_sens"])
        self.boyun_slider = self.create_slider(1, 20, settings["boyun_sens"])
        self.yakin_slider = self.create_slider(1, 20, settings["yakin_sens"])
        self.yanal_slider = self.create_slider(1, 20, settings["yanal_sens"])
        self.delay_slider = self.create_slider(1, 10, settings["alert_delay"])
        
        # Checkboxes
        self.startup_check = QCheckBox("Sistem Başlangıcında Çalıştır")
        self.startup_check.setChecked(settings.get("startup", False))
        
        self.eye_check = QCheckBox("Göz Sağlığı (20-20-20)")
        self.eye_check.setChecked(settings.get("eye_health", True))
        
        self.body_check = QCheckBox("Mola Hatırlatıcı (50dk/5dk)")
        self.body_check.setChecked(settings.get("body_break", True))

        self.game_mode_check = QCheckBox(texts['settings_game'])
        self.game_mode_check.setChecked(settings.get("game_mode_auto", True))

        from PyQt6.QtWidgets import QComboBox
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Türkçe", "English"])
        self.lang_combo.setCurrentIndex(0 if self.lang == "tr" else 1)
        self.lang_combo.setStyleSheet("color: black; background-color: white;")

        self.form.addRow(texts['settings_kambur'], self.kambur_slider)
        self.form.addRow(texts['settings_boyun'], self.boyun_slider)
        self.form.addRow(texts['settings_yakin'], self.yakin_slider)
        self.form.addRow(texts['settings_yanal'], self.yanal_slider)
        self.form.addRow(texts['settings_delay'], self.delay_slider)
        self.form.addRow("", self.startup_check)
        self.form.addRow("", self.eye_check)
        self.form.addRow("", self.body_check)
        self.form.addRow("", self.game_mode_check)
        self.form.addRow(texts['settings_lang'], self.lang_combo)

        self.save_btn = QPushButton(texts['settings_save'])
        self.save_btn.setStyleSheet("background-color: #27ae60; padding: 10px; font-weight: bold; border-radius: 5px;")
        self.save_btn.clicked.connect(self.save_and_apply)

        self.layout.addLayout(self.form)
        self.layout.addWidget(self.save_btn)
        self.setLayout(self.layout)

    def create_slider(self, min_v, max_v, curr_v):
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(int(curr_v))
        return s

    def save_and_apply(self):
        new_settings = load_settings()
        new_settings.update({
            "kambur_sens": self.kambur_slider.value(),
            "boyun_sens": self.boyun_slider.value(),
            "yakin_sens": self.yakin_slider.value(),
            "yanal_sens": self.yanal_slider.value(),
            "alert_delay": self.delay_slider.value(),
            "startup": self.startup_check.isChecked(),
            "eye_health": self.eye_check.isChecked(),
            "body_break": self.body_check.isChecked(),
            "game_mode_auto": self.game_mode_check.isChecked(),
            "language": "tr" if self.lang_combo.currentIndex() == 0 else "en"
        })
        save_settings(new_settings)
        
        # Uygula ve Yeniden Başlat (Dil değişimi için pencereleri sıfırla)
        self.parent_app.lang = new_settings["language"]
        self.parent_app.worker.lang = new_settings["language"]
        self.parent_app.game_mode_enabled = new_settings["game_mode_auto"]
        self.parent_app.update_tray_menu()
        
        # Pencereleri sıfırla ki bir sonraki açılışta yeni dille oluşsunlar
        self.parent_app.settings_window = None
        self.parent_app.stats_window = None
        
        # Ana widget'ı anında bilgilendir
        texts = LANGUAGES[self.parent_app.lang]
        self.parent_app.widget.update_widget(texts['settings_saved'], "blue")
        
        self.hide()

class PostureWidget(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(300, 80)
        self.setWindowOpacity(0.8)
        
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(geo.left() + geo.width() - 320, geo.top() + geo.height() - 150)
        else:
            self.move(100, 100) # Fallback
        
        self.layout = QVBoxLayout()
        self.label = QLabel("BAŞLATILIYOR...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # HP Barı (İnce Çizgi)
        self.hp_bar = QWidget()
        self.hp_bar.setFixedHeight(4)
        self.hp_bar.setFixedWidth(280)
        self.hp_bar.setStyleSheet("background-color: #27ae60; border-radius: 2px;")
        
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.hp_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.layout)
        
        # Göz Jimnastiği için hareketli nokta
        self.eye_dot = QLabel("🔵", self)
        self.eye_dot.hide()
        self.eye_timer = QTimer()
        self.eye_timer.timeout.connect(self.animate_eye_dot)
        self.eye_angle = 0

        self.drag_pos = QPoint()

    def animate_eye_dot(self):
        self.eye_angle += 0.1
        x = 150 + math.cos(self.eye_angle) * 80
        y = 40 + math.sin(self.eye_angle) * 20
        self.eye_dot.move(int(x), int(y))

    def show_water_alert(self):
        texts = LANGUAGES[self.parent_app.lang]
        toaster.show_toast("Smart Posture AI", texts['water_break'], duration=5, threaded=True)
        self.label.setText(texts['water_break'])
        QTimer.singleShot(5000, lambda: self.label.setText(self.parent_app.worker.last_status))

    def update_hp(self, val):
        width = int(2.8 * val)
        color = "#27ae60" if val > 70 else ("#f1c40f" if val > 30 else "#e74c3c")
        self.hp_bar.setFixedWidth(width)
        self.hp_bar.setStyleSheet(f"background-color: {color}; border-radius: 2px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def enterEvent(self, event):
        self.setWindowOpacity(1.0)
    
    def leaveEvent(self, event):
        self.setWindowOpacity(0.8)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2c3e50; color: white; border: 1px solid #34495e; } QMenu::item:selected { background-color: #3498db; }")
        texts = LANGUAGES[self.parent_app.lang]
        
        action_ghost = menu.addAction(texts['tray_ghost'])
        action_camera = menu.addAction(texts['tray_cam'])
        action_eye = menu.addAction(texts['tray_eye'])
        action_body = menu.addAction(texts['tray_body'])
        action_stats = menu.addAction(texts['tray_stats'])
        action_settings = menu.addAction(texts['tray_settings'])
        action_calibrate = menu.addAction(texts['tray_calibrate'])
        menu.addSeparator()
        action_quit = menu.addAction(texts['tray_quit'])
        
        action = menu.exec(event.globalPos())
        
        if action == action_ghost:
            self.parent_app.toggle_ghost_mode()
        elif action == action_camera:
            self.parent_app.toggle_camera_view()
        elif action == action_eye:
            self.parent_app.toggle_eye_health()
        elif action == action_body:
            self.parent_app.toggle_body_break()
        elif action == action_stats:
            self.parent_app.toggle_stats_view()
        elif action == action_settings:
            self.parent_app.toggle_settings_view()
        elif action == action_calibrate:
            self.parent_app.calibrate_now()
        elif action == action_quit:
            self.parent_app.quit_app()

    def update_widget(self, text, color):
        if self.parent_app.is_gaming:
            return # Oyun modundayken görsel güncelleme yapma

        if self.parent_app.worker.ghost_mode and color == "green":
            self.hide()
            return
        elif self.parent_app.worker.ghost_mode:
            self.show()

        styles = {"green": "rgba(46, 204, 113, 220)", "red": "rgba(231, 76, 60, 220)", "yellow": "rgba(241, 196, 15, 210)", "blue": "rgba(52, 152, 219, 240)", "gray": "rgba(127, 140, 141, 200)"}
        self.label.setText(text)
        self.parent_app.worker.last_status = text
        
        # Göz Jimnastiği Başlat/Durdur
        if "GÖZ DİNLENDİRME" in text:
            self.eye_dot.show()
            self.eye_timer.start(50)
        else:
            self.eye_dot.hide()
            self.eye_timer.stop()

        self.label.setStyleSheet(f"QLabel {{ color: white; font-family: 'Segoe UI'; font-size: 14px; font-weight: bold; background-color: {styles.get(color, 'black')}; border-radius: 18px; padding: 12px; border: 2px solid rgba(255,255,255,40); }}")

class PostureApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        settings = load_settings()
        self.lang = settings.get("language", "tr")
        
        self.worker = PoseWorker()
        self.worker.lang = self.lang
        self.widget = PostureWidget(self)
        self.cam_window = None
        self.stats_window = None
        self.settings_window = None
        self.summary_window = None
        self.is_gaming = False
        self.game_mode_enabled = settings.get("game_mode_auto", True)
        self.gaming_stats = {"total": 0, "bad": 0}
        
        # Başlangıç ayarını kontrol et ve uygula
        if settings.get("startup"):
            set_startup(True)
        
        # Sinyal bağlantıları
        signals.quit_signal.connect(self.quit_app)
        signals.calibrate_signal.connect(self.calibrate_now)
        
        self.worker.status_signal.connect(self.widget.update_widget)
        self.worker.hp_signal.connect(self.widget.update_hp)
        self.worker.water_signal.connect(self.widget.show_water_alert)
        
        self.tray = QSystemTrayIcon(self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), self.app)
        self.update_tray_menu()
        self.tray.show()
        
        keyboard.add_hotkey('f8', signals.calibrate_signal.emit)
        keyboard.add_hotkey('f9', signals.quit_signal.emit)
        
        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.check_game_mode)
        self.game_timer.start(5000)
        
        self.worker.start()
        self.widget.show()

    def update_tray_menu(self):
        texts = LANGUAGES[self.lang]
        menu = QMenu()
        menu.addAction(texts['tray_ghost']).triggered.connect(self.toggle_ghost_mode)
        menu.addAction(texts['tray_cam']).triggered.connect(self.toggle_camera_view)
        menu.addAction(texts['tray_eye']).triggered.connect(self.toggle_eye_health)
        menu.addAction(texts['tray_body']).triggered.connect(self.toggle_body_break)
        menu.addAction(texts['tray_stats']).triggered.connect(self.toggle_stats_view)
        menu.addAction(texts['tray_settings']).triggered.connect(self.toggle_settings_view)
        menu.addAction(texts['tray_calibrate']).triggered.connect(self.calibrate_now)
        menu.addAction(texts['tray_quit']).triggered.connect(self.quit_app)
        self.tray.setContextMenu(menu)

    def check_game_mode(self):
        if not self.game_mode_enabled: 
            self.is_gaming = False
            return

        fullscreen = is_fullscreen_app()
        texts = LANGUAGES[self.lang]
        
        if fullscreen and not self.is_gaming:
            # Oyuna yeni girildi
            self.is_gaming = True
            self.gaming_stats = {"total": 0, "bad": 0}
            self.widget.hide()
            self.tray.showMessage("Smart Posture AI", texts['game_mode_on'], QSystemTrayIcon.MessageIcon.Information, 3000)
        elif not fullscreen and self.is_gaming:
            # Oyundan çıkıldı
            self.is_gaming = False
            self.widget.show()
            self.show_gaming_summary()
        
        # İstatistik toplama (Oyun modundaysak)
        if self.is_gaming:
            self.gaming_stats["total"] += 5
            if self.worker.bad_posture_start is not None:
                self.gaming_stats["bad"] += 5

    def show_gaming_summary(self):
        total = self.gaming_stats["total"]
        if total < 60: return
        
        bad_ratio = (self.gaming_stats["bad"] / total) * 100
        texts = LANGUAGES[self.lang]
        if bad_ratio > 30:
            msg = texts['game_summary_msg'].format(int(bad_ratio))
            toaster.show_toast(texts['game_summary_title'], msg, duration=10, threaded=True)

    def toggle_ghost_mode(self):
        self.worker.ghost_mode = not self.worker.ghost_mode
        status = "ON" if self.worker.ghost_mode else "OFF"
        self.widget.update_widget(f"GHOST MODE: {status}", "blue")
        if not self.worker.ghost_mode:
            self.widget.show()

    def toggle_camera_view(self):
        if not self.cam_window:
            self.cam_window = CameraWindow(self)
            self.worker.frame_signal.connect(self.cam_window.update_image)
        
        if self.worker.show_camera:
            self.worker.show_camera = False
            self.cam_window.hide()
        else:
            self.worker.show_camera = True
            self.cam_window.show()

    def toggle_eye_health(self):
        self.worker.eye_health_active = not self.worker.eye_health_active
        self.worker.last_eye_break_time = time.time()
        self.worker.is_in_eye_break = False
        status = "ON" if self.worker.eye_health_active else "OFF"
        texts = LANGUAGES[self.lang]
        self.widget.update_widget(f"{texts['tray_eye']}: {status}", "blue")

    def toggle_body_break(self):
        self.worker.body_break_active = not self.worker.body_break_active
        self.worker.last_body_break_time = time.time()
        self.worker.is_in_body_break = False
        status = "ON" if self.worker.body_break_active else "OFF"
        texts = LANGUAGES[self.lang]
        self.widget.update_widget(f"{texts['tray_body']}: {status}", "blue")

    def toggle_stats_view(self):
        if not self.stats_window:
            self.stats_window = StatsWindow(self.worker, self.lang)
        
        if self.stats_window.isVisible():
            self.stats_window.hide()
        else:
            self.stats_window.show()
            self.stats_window.refresh_stats()

    def toggle_settings_view(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(self)
        
        if self.settings_window.isVisible():
            self.settings_window.hide()
        else:
            self.settings_window.show()

    def calibrate_now(self):
        if self.worker.calibrate():
            self.widget.update_widget(LANGUAGES[self.lang]['settings_saved'], "blue")

    def quit_app(self):
        report_path = self.worker.generate_final_report()
        self.worker.running = False
        if report_path and os.path.exists(report_path):
            self.widget.hide() # Ana widget'ı gizle
            self.summary_window = SummaryWindow(report_path, self.finalize_quit)
            self.summary_window.show()
        else:
            self.finalize_quit()

    def finalize_quit(self):
        keyboard.unhook_all()
        os.kill(os.getpid(), signal.SIGTERM)

if __name__ == '__main__':
    PostureApp().app.exec()