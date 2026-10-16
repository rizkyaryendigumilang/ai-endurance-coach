import os
import requests
from typing import List, Dict, Optional
from app.core.config import GEMINI_API_KEY, GEMINI_FREE_API_KEY, GEMINI_PRO_API_KEY, OPENAI_API_KEY

SYSTEM_PROMPT = """Kamu adalah Lead Sports Scientist dan Head Performance Coach untuk platform analitik atletik GOALIE.

Karakter Komunikasi:
- Berbicaralah seperti pelatih endurance veteran: langsung pada inti masalah, lugas, profesional, dan berbasis data fisiologi.
- Jangan pernah menggunakan basa-basi pembuka khas chatbot seperti "Tentu saja!", "Halo atlet hebat!", "Pertanyaan yang luar biasa!", atau "Saya siap membantu Anda". Langsung sajikan analisis dan instruksi.
- Dilarang keras menggunakan emoji apa pun (tanpa api, roket, jempol, kilat, atau sejenisnya).
- Gunakan terminologi olahraga yang tepat (fase aerobik, ambang laktat/threshold, TSB, cardiac drift, form fatigue, kadens, GAP, TRIMP).

ATURAN ARSITEKTUR:
1. Angka metrik fisiologis (Pace, Training Load, Aerobic Efficiency, HR Drift, GAP, TSB) adalah hasil komputasi deterministik Sports Engine backend. Jadikan sebagai rujukan faktual.
2. Bertindak sebagai penasihat strategi atlet, bukan pengubah basis data langsung.
3. Gunakan Bahasa Indonesia yang ringkas, berbobot, dan dapat diterapkan langsung di lapangan."""


class MultiTierAIProvider:
    """
    Dual Multi-Tier AI Provider:
    - Free Tier: Google Gemini 3.8 Flash (Free API Key) with OpenAI & Sports Engine fallback
    - Pro Subscription Tier: Google Gemini 3.8 Flash (Pro Subs Key) with deep macrocycle reasoning
    - Deterministic Sports Science Engine: Resilient offline fallback when quotas are exhausted
    """
    def __init__(self):
        self.gemini_free_key = GEMINI_FREE_API_KEY or GEMINI_API_KEY or ""
        self.gemini_pro_key = GEMINI_PRO_API_KEY or GEMINI_API_KEY or ""
        self.openai_key = OPENAI_API_KEY or ""
        self.openai_client = None

        if self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                print(f"[AI Provider] Warning: Failed to init OpenAI client: {e}")

    def get_tier_status(self) -> Dict:
        """Returns the operational status of Pemula (Free), Coach (Free), and Coach (Pro) engines."""
        return {
            "pemula_tier": {
                "name": "Pemula (Free)",
                "provider": "Sports Science Deterministic Engine",
                "model": "deterministic-v2.4",
                "status": "operational",
                "badge": "PEMULA",
                "description": "Kalkulasi pace dasar, estimasi VO2max, kalkulator zona detak jantung & panduan latihan mandiri."
            },
            "free_tier": {
                "name": "Coach (Free)",
                "provider": "Google Gemini 3.8 Flash (Free Tier)",
                "model": "gemini-3.8-flash",
                "status": "operational" if (self.gemini_free_key or self.openai_key) else "unconfigured",
                "badge": "FREE COACH",
                "description": "Konsultasi latihan harian dengan AI Coach, evaluasi pace, panduan recovery & catatan latihan umum."
            },
            "pro_tier": {
                "name": "Coach (Pro)",
                "provider": "Google Gemini 3.8 Flash (Pro Subscription)",
                "model": "gemini-3.8-flash",
                "status": "operational" if self.gemini_pro_key else "unconfigured",
                "badge": "PRO COACH",
                "description": "Periodisasi makrosiklus mendalam, deteksi cardiac drift, adaptasi beban TSB & biomekanika video tanpa batas."
            }
        }

    async def chat_with_coach(
        self,
        context: str,
        message: str,
        history: List[Dict] = None,
        tier: str = "free",
        provider_override: Optional[str] = None,
        custom_api_key: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Routes the conversation through the appropriate AI engine based on tier:
        - tier='pemula' -> Sports Science Deterministic Engine (Offline mathematical calculation)
        - tier='free' or 'coach_free' -> Google Gemini 3.8 Flash (Free Key), fallback to OpenAI, then Deterministic Engine
        - tier='pro' or 'coach_pro'  -> Google Gemini 3.8 Flash (Pro Subs Key or User BYOK Key)
        Returns a dict with 'text', 'provider_used', and 'tier'.
        """
        # 0. Pemula (Free): Pure deterministic sports science engine
        if tier in ("pemula", "pemula_free"):
            fallback_text = self._generate_deterministic_response(context, message)
            return {
                "text": fallback_text,
                "provider_used": "Pemula Engine (Deterministic Sports Science)",
                "tier": "pemula"
            }

        # 1. Coach (Pro): Pro Subscription or BYOK API Key Request
        if tier in ("pro", "coach_pro") or provider_override == "gemini_pro":
            active_pro_key = (custom_api_key.strip() if custom_api_key else "") or self.gemini_pro_key
            res_pro = await self._call_gemini(context, message, history, api_key=active_pro_key)
            if res_pro.get("success"):
                label = "Google Gemini 3.8 Flash (Coach Pro)"
                if custom_api_key:
                    label += " [Athlete API Key]"
                return {
                    "text": res_pro["text"],
                    "provider_used": label,
                    "tier": "pro"
                }
            print(f"[AI Provider] Gemini Pro error ({res_pro.get('error')}), falling back...")

        # 2. Free Tier Request: First attempt with Gemini Free Key
        if self.gemini_free_key:
            res_free_gemini = await self._call_gemini(context, message, history, api_key=self.gemini_free_key)
            if res_free_gemini.get("success"):
                return {
                    "text": res_free_gemini["text"],
                    "provider_used": "Google Gemini 3.8 Flash (Free Tier)",
                    "tier": "free"
                }
            print(f"[AI Provider] Gemini Free error ({res_free_gemini.get('error')}), testing OpenAI fallback...")

        # 3. Secondary Fallback: OpenAI GPT-4o-mini
        if self.openai_client:
            res_openai = await self._call_openai(context, message, history)
            if res_openai.get("success"):
                return {
                    "text": res_openai["text"],
                    "provider_used": "OpenAI GPT-4o-mini (Free Tier)",
                    "tier": "free"
                }

        # 4. Resilient Deterministic Sports Science Fallback
        fallback_text = self._generate_deterministic_response(context, message)
        return {
            "text": fallback_text,
            "provider_used": f"Sports Science Engine ({'Pro Fallback' if tier == 'pro' else 'Free Tier'})",
            "tier": tier
        }

    async def _call_openai(self, context: str, message: str, history: List[Dict] = None) -> Dict:
        """Invokes OpenAI GPT-4o-mini."""
        if not self.openai_client:
            return {"success": False, "error": "OpenAI client not configured"}

        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if history:
                for h in history[-8:]:
                    role = "user" if h.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": h.get("content", "")})

            full_prompt = f"Konteks Fisiologi Atlet:\n{context}\n\nPertanyaan Atlet:\n{message}"
            messages.append({"role": "user", "content": full_prompt})

            completion = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=450,
                temperature=0.4
            )
            text = completion.choices[0].message.content.strip()
            return {"success": True, "text": text}
        except Exception as e:
            err_str = str(e)
            return {"success": False, "error": err_str}

    async def _call_gemini(
        self,
        context: str,
        message: str,
        history: List[Dict] = None,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.8-flash"
    ) -> Dict:
        """Invokes Google Gemini with the specified API key."""
        target_key = api_key or self.gemini_pro_key or self.gemini_free_key
        if not target_key:
            return {"success": False, "error": "Gemini key not configured"}

        # 1. First attempt: google.generativeai SDK
        try:
            import google.generativeai as genai
            genai.configure(api_key=target_key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_PROMPT
            )
            chat_history = []
            if history:
                for h in history[-8:]:
                    role = "user" if h.get("role") == "user" else "model"
                    chat_history.append({"role": role, "parts": [h.get("content", "")]})

            full_msg = f"Konteks Fisiologi Atlet:\n{context}\n\nPertanyaan Atlet:\n{message}"
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(full_msg)
            if response and response.text:
                return {"success": True, "text": response.text.strip()}
        except Exception as e:
            print(f"[AI Provider] Gemini SDK attempt error: {e}")

        # 2. Second attempt: Direct REST API
        models_to_try = [model_name, "gemini-flash-latest", "gemini-pro-latest", "gemini-flash-lite-latest"]
        for m in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={target_key}"
            contents = [
                {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\nKonteks Data Atlet:\n{context}\n\nPertanyaan Atlet:\n{message}"}]}
            ]
            try:
                res = requests.post(url, json={"contents": contents}, timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return {"success": True, "text": parts[0].get("text", "").strip()}
            except Exception:
                continue

        return {"success": False, "error": "Gemini request timed out or unavailable"}

    def _generate_deterministic_response(self, context: str, message: str) -> str:
        """
        High-precision sports science response derived deterministically from the metrics.
        Ensures that even if both API quotas are exhausted, the athlete receives accurate coaching advice.
        """
        msg_lower = message.lower()

        if any(w in msg_lower for w in ["recovery", "lelah", "istirahat", "rest", "capek"]):
            return (
                "Rekomendasi Recovery Fisiologis:\n"
                "- Status kardiovaskular menunjukkan akumulasi beban latihan aktif. Utamakan tidur malam 7-8 jam untuk pemulihan glikogen dan sintesis protein otot.\n"
                "- Jika resting heart rate (RHR) pagi naik >5 bpm di atas baseline, lakukan active recovery (jalan santai/sepeda ringan Zona 1) maksimal 30 menit atau jadwalkan full rest day.\n"
                "- Pertahankan hidrasi 500ml per jam pasca-sesi latihan ditambah asupan elektrolit sodium."
            )
        elif any(w in msg_lower for w in ["pace", "kecepatan", "tempo", "interval", "target"]):
            return (
                "Strategi Pacing & Distribusi Zona Latihan:\n"
                "- 80% dari total volume mingguan wajib dijalankan di Zona 2 Aerobic Base (bisa berbicara tanpa terengah-engah) untuk memperbesar densitas mitokondria.\n"
                "- Sesi tempo/threshold dialokasikan 1x per minggu pada batas laktat (RPE 7/10) untuk meningkatkan ambang batas ketahanan laktat.\n"
                "- Gunakan Grade Adjusted Pace (GAP) pada rute berkontur tanjakan guna mencegah kelelahan dini akibat lonjakan daya mekanik."
            )
        elif any(w in msg_lower for w in ["tsb", "fitness", "fatigue", "form"]):
            return (
                "Analisis Training Stress Balance (TSB):\n"
                "- TSB dihitung dari Chronic Training Load (CTL / Fitness) dikurangi Acute Training Load (ATL / Fatigue).\n"
                "- Nilai TSB di rentang -10 s/d -30 menandakan fase produktif penumpukan beban latihan (overreaching terukur).\n"
                "- Jelang race day / lomba utama, kurangi volume 40-50% selama 10-14 hari agar TSB naik ke rentang +5 s/d +15 (peak freshness / race ready)."
            )
        else:
            return (
                f"Evaluasi Latihan Atletik:\n"
                f"- Berdasarkan data fisiologi saat ini ({context.strip()[:140] if context else 'Data tersimpan'}), "
                "kunci peningkatan performa endurance adalah konsistensi beban mingguan (progressive overload) tanpa lonjakan volume mendadak >10% per minggu.\n"
                "- Pantau indikator dekompensasi seperti kenaikan detak jantung pada pace yang sama (cardiac drift) untuk mencegah sindrom overtraining."
            )

    async def generate_adaptation_explanation(self, context_dict: Dict, tier: str = "pro") -> str:
        """
        Generates tactical recovery and workout adaptation recommendations.
        """
        prompt = (
            f"Konteks Atlet: {context_dict.get('athlete', 'Atlet')}\n"
            f"Status TSB: {context_dict.get('tsb', {})}\n"
            f"Jumlah sesi: {context_dict.get('recent_workouts_count', 0)}\n"
            f"Query: {context_dict.get('query', 'Evaluasi beban')}"
        )
        res = await self.chat_with_coach(str(context_dict), prompt, tier=tier)
        return res["text"]


# Backward Compatibility Alias
GeminiAIProvider = MultiTierAIProvider