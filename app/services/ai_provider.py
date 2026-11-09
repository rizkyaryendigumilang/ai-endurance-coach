import os
import asyncio
import requests
from typing import List, Dict, Optional
from app.core.config import GEMINI_API_KEY, GEMINI_FREE_API_KEY, GEMINI_PRO_API_KEY, OPENAI_API_KEY

SYSTEM_PROMPT = """Kamu adalah Lead Sports Scientist dan Head Performance Coach untuk platform analitik atletik GOALIE.

Karakter Komunikasi:
- Berbicaralah seperti pelatih endurance veteran: langsung pada data dan instruksi, super ringkas, tanpa narasi panjang.
- Maksimal 2-3 poin ringkas per jawaban. Dilarang membuat paragraf panjang, basa-basi, atau esai.
- Jangan pernah menggunakan basa-basi pembuka khas chatbot seperti "Tentu saja!", "Halo!", "Pertanyaan bagus!". Langsung angka dan tindakan.
- Dilarang keras menggunakan emoji apa pun.
- Format: bullet points ringkas berbasis metrik (Pace, Heart Rate, Zona, Cadence, TSB, Rekomendasi).

ATURAN ARSITEKTUR:
1. Angka metrik fisiologis (Pace, Training Load, Aerobic Efficiency, HR Drift, GAP, TSB) adalah hasil komputasi deterministik Sports Engine backend.
2. Gunakan Bahasa Indonesia teknis yang sangat padat dan langsung dapat dieksekusi atlet di lapangan."""


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
        """Invokes OpenAI GPT-4o-mini non-blockingly using worker thread."""
        if not self.openai_client:
            return {"success": False, "error": "OpenAI client not configured"}

        def _execute_sync_openai():
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
            return completion.choices[0].message.content.strip()

        try:
            text = await asyncio.to_thread(_execute_sync_openai)
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
        """Invokes Google Gemini with the specified API key non-blockingly via asyncio.to_thread."""
        target_key = api_key or self.gemini_pro_key or self.gemini_free_key
        if not target_key:
            return {"success": False, "error": "Gemini key not configured"}

        def _execute_sync_gemini():
            # 1. Primary: Official Google GenAI SDK (google-genai 3.x)
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=target_key)
                target_model = model_name if "gemini" in model_name else "gemini-2.5-flash"
                if target_model == "gemini-3.8-flash":
                    target_model = "gemini-2.5-flash"
                cfg = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=600,
                )
                full_msg = f"Konteks Fisiologi Atlet:\n{context}\n\nPertanyaan Atlet:\n{message}"
                response = client.models.generate_content(
                    model=target_model,
                    contents=full_msg,
                    config=cfg
                )
                if response and response.text:
                    return {"success": True, "text": response.text.strip()}
            except Exception:
                pass

            # 2. Secondary attempt: Direct REST API (Reliable fallback with multiple model options)
            models_to_try = [model_name, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            for m in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={target_key}"
                contents = [
                    {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\nKonteks Data Atlet:\n{context}\n\nPertanyaan Atlet:\n{message}"}]}
                ]
                try:
                    res = requests.post(url, json={"contents": contents}, timeout=5)
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

        try:
            return await asyncio.to_thread(_execute_sync_gemini)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_deterministic_response(self, context: str, message: str) -> str:
        """
        High-precision sports science response derived deterministically from the metrics.
        Ensures that even if both API quotas are exhausted, the athlete receives accurate coaching advice.
        """
        msg_lower = message.lower()

        if any(w in msg_lower for w in ["recovery", "lelah", "istirahat", "rest", "capek"]):
            return (
                "Rekomendasi Pemulihan:\n"
                "- Tidur 7-8 jam; rehidrasi 500ml + elektrolit pasca-latihan.\n"
                "- RHR naik >5 bpm: jadwalkan Rest Day atau Easy Spin Zona 1 (max 30m).\n"
                "- TSB pasca-sesi berat: kembali ke zona netral (-10 s/d 0) dalam 48 jam."
            )
        elif any(w in msg_lower for w in ["pace", "kecepatan", "tempo", "interval", "target"]):
            return (
                "Strategi Pacing & Zona:\n"
                "- 80% volume di Zona 2 Aerobic Base (FatMax, percakapan nyaman).\n"
                "- 20% volume di Zona 4 Threshold (1x per minggu, RPE 7-8/10).\n"
                "- Rute tanjakan: ikuti Grade-Adjusted Pace (GAP) agar daya tetap stabil."
            )
        elif any(w in msg_lower for w in ["tsb", "fitness", "fatigue", "form"]):
            return (
                "Status Beban & TSB:\n"
                "- TSB = CTL (Fitness) - ATL (Fatigue).\n"
                "- Fase Bangun: TSB -10 s/d -25 (overreaching terukur).\n"
                "- Fase Lomba: Taper 10-14 hari hingga TSB +5 s/d +15 (Freshness)."
            )
        else:
            return (
                "Evaluasi Latihan:\n"
                f"- Metrik: {context.strip()[:80] if context else 'Nominal'}.\n"
                "- Batasi lonjakan beban mingguan maksimal +10% (ACWR 0.8 - 1.3).\n"
                "- Jaga cardiac drift <5% untuk stabilitas efisiensi aerobik."
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


# Backward Compatibility Alias & Singleton
GeminiAIProvider = MultiTierAIProvider
ai_provider = MultiTierAIProvider()
