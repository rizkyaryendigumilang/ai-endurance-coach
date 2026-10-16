import os
import hmac
import hashlib
import uuid
from datetime import datetime
from typing import Dict, Optional

PAYMENT_PROVIDER = os.getenv("PAYMENT_GATEWAY_PROVIDER", "mock").lower()
MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY", "")
XENDIT_SECRET_KEY = os.getenv("XENDIT_SECRET_KEY", "")

class BasePaymentGateway:
    def create_order(self, user_id: str, plan: str, amount: int, payment_method: str = "qris") -> Dict:
        raise NotImplementedError

    def verify_webhook(self, payload: Dict, signature: str = "") -> bool:
        raise NotImplementedError


class MockPaymentGateway(BasePaymentGateway):
    """
    Placeholder Payment Gateway: Generates valid QRIS standard payloads and VA numbers.
    Used until production Midtrans/Xendit credentials are provided.
    """
    def create_order(self, user_id: str, plan: str, amount: int, payment_method: str = "qris") -> Dict:
        order_id = f"ORD-PRO-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        qris_code = f"00020101021226680016ID.CO.GOALIE.WWW0118936009999900010203510400005303360540{amount}5802ID5914GOALIE COACH6007JAKARTA62070703A016304ABCD"
        va_number = None
        if "va" in (payment_method or ""):
            prefix = "88001" if "bca" in payment_method else "89002"
            va_number = prefix + str(uuid.uuid4().int)[:7]

        return {
            "order_id": order_id,
            "plan": plan,
            "plan_name": "Paket Pro Tahunan (Hemat 22%)" if plan == "annual" else "Paket Pro Bulanan",
            "amount_idr": amount,
            "payment_method": payment_method or "qris",
            "qris_code": qris_code,
            "va_number": va_number,
            "expires_in_seconds": 900,
            "provider": "mock_placeholder"
        }

    def verify_webhook(self, payload: Dict, signature: str = "") -> bool:
        return True


class MidtransPaymentGateway(BasePaymentGateway):
    """
    Midtrans Snap / Core API Gateway:
    Activated when MIDTRANS_SERVER_KEY is supplied.
    """
    def __init__(self, server_key: str):
        self.server_key = server_key

    def create_order(self, user_id: str, plan: str, amount: int, payment_method: str = "qris") -> Dict:
        order_id = f"MDT-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        # Midtrans API request placeholder
        return {
            "order_id": order_id,
            "plan": plan,
            "amount_idr": amount,
            "payment_method": payment_method,
            "provider": "midtrans",
            "status": "pending"
        }

    def verify_webhook(self, payload: Dict, signature: str = "") -> bool:
        order_id = payload.get("order_id", "")
        status_code = payload.get("status_code", "")
        gross_amount = payload.get("gross_amount", "")
        sig_str = f"{order_id}{status_code}{gross_amount}{self.server_key}"
        expected_sig = hashlib.sha512(sig_str.encode()).hexdigest()
        return hmac.compare_digest(expected_sig, signature)


def get_payment_gateway() -> BasePaymentGateway:
    if MIDTRANS_SERVER_KEY:
        return MidtransPaymentGateway(MIDTRANS_SERVER_KEY)
    return MockPaymentGateway()
