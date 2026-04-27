import cv2
import mediapipe as mp

print("--- SMART POSTURE AI BASLATILIYOR ---")

# 1. MediaPipe Yapılandırması
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,      # CPU dostu: 0 en hızlı, 1 orta, 2 en ağır modeldir.
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils

# 2. Değişkenler
ideal_posture_y = None  # Kalibrasyon değeri
threshold = 0.05        # Hassasiyet (Stand yüksekliğine göre 0.05 - 0.10 arası denenebilir)

# 3. Kamera Başlatma
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("HATA: Kamera algılanamadı!")
else:
    print("\nKOMUTLAR:")
    print("- 's' tusuna basarak ideal durusunuzu kalibre edin.")
    print("- 'q' tusuna basarak programdan cikin.\n")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Görüntü İşleme (RGB'ye çevir ve MediaPipe'a gönder)
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        # Arka plan kutusu (Yazıların okunabilirliği için)
        cv2.rectangle(frame, (20, 20), (480, 130), (10, 10, 10), -1)

        if results.pose_landmarks:
            # Eklemleri ekrana çiz
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            # Koordinatları al
            landmarks = results.pose_landmarks.landmark
            left_shoulder_y = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y
            right_shoulder_y = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y
            shoulder_avg_y = (left_shoulder_y + right_shoulder_y) / 2

            # DURUM ANALİZİ
            if ideal_posture_y is None:
                status_text = "Lutfen 'S' ile KALIBRE EDIN"
                color = (0, 255, 255) # Sarı
            else:
                # Eğer omuzlar ideal seviyeden aşağı düşerse (Y değeri artarsa)
                if shoulder_avg_y > (ideal_posture_y + threshold):
                    status_text = "DIKKAT: KAMBUR DURUYORSUN!"
                    color = (0, 0, 255) # Kırmızı
                else:
                    status_text = "DURUSUN HARIKA"
                    color = (0, 255, 0) # Yeşil

            # Bilgileri Ekrana Yazdır
            cv2.putText(frame, status_text, (40, 65), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            
            cv2.putText(frame, f"Anlik Omuz Y: {round(shoulder_avg_y, 3)}", (40, 95), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            if ideal_posture_y:
                cv2.putText(frame, f"Ideal Omuz Y: {round(ideal_posture_y, 3)}", (40, 115), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Pencereyi göster
        cv2.imshow('Smart Posture AI - Engine v1.0', frame)

        # Tuş Kontrolleri
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            ideal_posture_y = shoulder_avg_y
            print(f"Kalibrasyon basarili! Yeni Hedef: {round(ideal_posture_y, 3)}")
        elif key == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
print("--- PROGRAM KAPANDI ---")