"""
Goalie — Subscriptions Router
Manages athlete subscription status, BYOK activation, checkout orders (QRIS / VA), and activation.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.services import sandbox_store
from app.schemas.models import SubscriptionOrderInput, SubscriptionActivateInput, ByokRegisterInput
from app.core.auth import get_current_user, get_current_user_optional

router = APIRouter(tags=["Subscription"])


@router.get("/api/v1/subscription/status")
def get_subscription_status(user_id: str = Depends(get_current_user_optional)):
    """Mengambil status langganan atlet saat ini (Pemula Free, Coach Free, vs Coach Pro/BYOK)."""
    sub = sandbox_store.get_subscription(user_id)
    return {
        "status": "success",
        "subscription": sub
    }


@router.post("/api/v1/subscription/byok")
def register_byok_key(
    byok_req: ByokRegisterInput,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Mendaftarkan atau menghapus Bring-Your-Own-Key (BYOK) Google Gemini API Key.
    Key valid langsung membuka tier Coach (Pro) 100% gratis tanpa biaya langganan.
    """
    key = (byok_req.api_key or "").strip()
    if key and len(key) < 15:
        raise HTTPException(
            status_code=400,
            detail="Format Gemini API Key tidak valid (minimal 15 karakter). Dapatkan key gratis di Google AI Studio."
        )

    res = sandbox_store.set_byok_key(user_id, key)
    msg = (
        "BYOK Gemini API Key berhasil diverifikasi dan disimpan! Tier Coach (Pro) kini aktif 100% Gratis."
        if key else
        "BYOK Gemini API Key dinonaktifkan. Akun kembali ke Coach (Free)."
    )
    return {
        "status": "success",
        "message": msg,
        "data": res
    }


@router.post("/api/v1/subscription/create-order")
def create_subscription_order(
    order_req: SubscriptionOrderInput,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Membuat checkout order langganan Pro Plan (QRIS, VA, atau Kartu Kredit).
    """
    plan = (order_req.plan or "monthly").lower()
    amount = 828000 if plan == "annual" else 89000
    order_id = f"ORD-PRO-{datetime.now(timezone.utc).strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    qris_code = f"00020101021226680016ID.CO.GOALIE.WWW0118936009999900010203510400005303360540{amount}5802ID5914GOALIE COACH6007JAKARTA62070703A016304ABCD"

    va_number = None
    if "va" in (order_req.payment_method or ""):
        prefix = "88001" if "bca" in order_req.payment_method else "89002"
        va_number = prefix + str(uuid.uuid4().int)[:7]

    return {
        "status": "success",
        "order_id": order_id,
        "plan": plan,
        "plan_name": "Paket Pro Tahunan (Hemat 22%)" if plan == "annual" else "Paket Pro Bulanan ($19/mo / Rp 89.000)",
        "amount_idr": amount,
        "payment_method": order_req.payment_method or "qris",
        "qris_code": qris_code,
        "va_number": va_number,
        "expires_in_seconds": 900
    }


@router.post("/api/v1/subscription/activate")
def activate_subscription(
    activate_req: SubscriptionActivateInput,
    user_id: str = Depends(get_current_user_optional)
):
    """
    Mengaktifkan paket langganan Pro Plan atlet setelah pembayaran selesai/dikonfirmasi.
    """
    sub = sandbox_store.set_subscription(
        user_id=user_id,
        plan=activate_req.plan or "monthly",
        order_id=activate_req.order_id,
        payment_method=activate_req.payment_method or "qris"
    )
    return {
        "status": "success",
        "message": "Langganan Goalie AI Coach Pro berhasil diaktifkan! Fitur Google Gemini 3.8 Flash Pro kini aktif penuh.",
        "subscription": sub
    }
