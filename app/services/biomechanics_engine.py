import cv2
import math
import base64
import numpy as np

try:
    import mediapipe as mp
    try:
        from mediapipe.python.solutions import pose as mp_pose
        from mediapipe.python.solutions import drawing_utils as mp_draw
    except Exception:
        mp_pose = getattr(mp, "solutions", None).pose if hasattr(mp, "solutions") else None
        mp_draw = getattr(mp, "solutions", None).drawing_utils if hasattr(mp, "solutions") else None
except Exception:
    mp = None
    mp_pose = None
    mp_draw = None

class BiomechanicsEngine:
    def __init__(self):
        self.mp_pose = mp_pose
        self.mp_draw = mp_draw
        self._pose = None

    def get_pose(self):
        """Lazy-loads MediaPipe TensorFlow model on demand, saving 80MB+ RAM on server boot."""
        if self._pose is None and self.mp_pose is not None:
            try:
                self._pose = self.mp_pose.Pose(static_image_mode=True)
            except Exception:
                self._pose = None
        return self._pose

    def analyze_image(self, image_bytes: bytes):
        pose = self.get_pose()
        if not pose or not self.mp_draw or not self.mp_pose:
            return {"error": "Modul analisis pose MediaPipe tidak tersedia di runtime ini."}

        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Gagal membaca format gambar."}

        result = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        if not result.pose_landmarks:
            return {"error": "Pose tidak terdeteksi pada gambar."}

        lm = result.pose_landmarks.landmark
        h, w, _ = img.shape
        def get_pt(idx): return [lm[idx].x, lm[idx].y]
        hip, knee, ankle, shoulder = get_pt(24), get_pt(26), get_pt(28), get_pt(12)

        knee_angle = abs(math.degrees(math.atan2(ankle[1]-knee[1], ankle[0]-knee[0]) - math.atan2(hip[1]-knee[1], hip[0]-knee[0])))
        lean_angle = abs(math.degrees(math.atan2(shoulder[1]-hip[1], shoulder[0]-hip[0])))
        
        score = 100
        if knee_angle < 150: score -= 25
        elif knee_angle < 165: score -= 10
        if lean_angle < 5: score -= 15
        elif lean_angle > 20: score -= 10
        score = max(0, min(score, 100))

        feedback = []
        if knee_angle < 150: feedback.append("Langkah terlalu panjang (overstride).")
        elif knee_angle > 175: feedback.append("Knee drive kurang aktif.")
        if lean_angle < 5: feedback.append("Badan terlalu tegak.")
        elif lean_angle > 20: feedback.append("Terlalu condong ke depan.")
        if not feedback: feedback.append("Form lari sangat efisien.")

        self.mp_draw.draw_landmarks(img, result.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
        _, buffer = cv2.imencode('.jpg', img)
        
        return {
            "metrics": {"score": score, "knee_angle": round(knee_angle, 1), "lean_angle": round(lean_angle, 1), "feedback": feedback},
            "annotated_image": base64.b64encode(buffer).decode('utf-8')
        }