"""
Goalie — Subscriptions Router
Manages athlete subscription status, checkout orders (QRIS / VA), and activation.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.services import sandbox_store
from app.schemas.models import SubscriptionOrderInput, SubscriptionActivateInput
from app.core.auth import get_current_user

router = APIRouter(tags=["Subscription"])


@router.get("/api/v1/subscription/status")
def get_subscription_status(user_id: str = Depends(get_current_user)):
    """Mengambil status langganan atlet saat ini (Free vs Pro)."""
    sub = sandbox_store.get_subscription(user_id)
    return {
        "status": "success",
        "subscription": sub
    }


@router.post("/api/v1/subscription/create-order")
def create_subscription_order(
    order_req: SubscriptionOrderInput,
    user_id: str = Depends(get_current_user)
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
        "plan_name": "Paket Pro Tahunan (Hemat 22%)" if plan == "annual" else "Paket Pro Bulanan",
        "amount_idr": amount,
        "payment_method": order_req.payment_method or "qris",
        "qris_code": qris_code,
        "va_number": va_number,
        "expires_in_seconds": 900
    }


@router.post("/api/v1/subscription/activate")
def activate_subscription(
    activate_req: SubscriptionActivateInput,
    user_id: str = Depends(get_current_user)
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
        "message": "Langganan Goalie AI Coach Pro berhasil diaktifkan! Fitur Google Gemini 3.8 Flash kini aktif penuh.",
        "subscription": sub
    }
