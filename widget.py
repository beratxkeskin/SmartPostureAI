import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette

class PostureWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # 1. Pencere Özellikleri (Şeffaf, Çerçevesiz, Her Zaman Üstte)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |       # Çerçeveyi kaldır
            Qt.WindowType.WindowStaysOnTopHint |     # Her zaman üstte tut
            Qt.WindowType.Tool                        # Görev çubuğunda gösterme
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Arka planı şeffaf yap
        
        # 2. Boyut ve Konum (Ekranın sağ alt köşesi)
        self.resize(200, 80)
        
        # Ekranın sağ alt köşesine konumlandır (Basit bir yöntem)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 220, screen.height() - 120)

        # 3. Arayüz Elemanları (Yazı ve Düzen)
        self.layout = QVBoxLayout()
        self.label = QLabel("BAŞLATILIYOR...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Yazı Tipi ve Rengi
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 150); /* Yarı şeffaf siyah arka plan */
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)

        # 4. Test için bir Zamanlayıcı (Renk değiştirmeyi denemek için)
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.change_status_test)
        self.test_timer.start(2000) # Her 2 saniyede bir durumu değiştir
        self.status_counter = 0

    def change_status_test(self):
        """Test amaçlı durumu değiştirir."""
        if self.status_counter % 3 == 0:
            self.set_status("DURUSUN HARİKA", "green")
        elif self.status_counter % 3 == 1:
            self.set_status("LÜTFEN KALİBRE ET", "yellow")
        else:
            self.set_status("KAMBUR DURUYORSUN!", "red")
        self.status_counter += 1

    def set_status(self, text, color_name):
        """Dışarıdan çağrılacak fonksiyon: Yazıyı ve rengi değiştirir."""
        self.label.setText(text)
        
        # Renk tonlarını belirleyelim
        if color_name == "green":
            bg_color = "rgba(0, 150, 0, 180)" # Yarı şeffaf yeşil
        elif color_name == "red":
            bg_color = "rgba(200, 0, 0, 180)"   # Yarı şeffaf kırmızı
        elif color_name == "yellow":
            bg_color = "rgba(200, 200, 0, 180)" # Yarı şeffaf sarı
        else:
            bg_color = "rgba(0, 0, 0, 150)"   # Varsayılan siyah

        # Stili güncelle
        self.label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                font-weight: bold;
                background-color: {bg_color};
                border-radius: 10px;
                padding: 10px;
            }}
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = PostureWidget()
    widget.show()
    sys.exit(app.exec())