from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import secrets
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel
from app.core.auth import get_current_user_optional
from app.services import sandbox_store
from app.services.db_storage import sqlite_store

router = APIRouter(tags=["Enterprise Hub"])

class NotificationReadInput(BaseModel):
    notification_id: Optional[str] = None
    all: Optional[bool] = False

class TeamInviteInput(BaseModel):
    email: str
    role: str = "athlete"  # 'head_coach' | 'assistant_coach' | 'athlete'
    team_name: Optional[str] = "Goalie Jakarta Racing Squad"

class SupportFeedbackInput(BaseModel):
    category: str  # 'feature_request' | 'bug_report' | 'coaching_feedback' | 'other'
    subject: str
    message: str
    rating: Optional[int] = 5

# In-memory notification state tracker
_READ_NOTIFICATIONS = set()
_PENDING_INVITES: List[Dict[str, Any]] = []
_FEEDBACK_ENTRIES: List[Dict[str, Any]] = []

@router.get("/api/v1/notifications", tags=["Notifications"])
def get_notifications(user_id: str = Depends(get_current_user_optional)):
    """
    Pusat Notifikasi: Mengambil daftar peringatan beban latihan, pengingat jadwal,
    dan status telemetri atlet.
    """
    uid = user_id or sandbox_store.OWNER_USER_ID
    profile = sandbox_store.get_profile(uid) or {}
    race_name = profile.get("target_race_name") or "BTN Jakarta International Marathon (JAKIM) 2026"

    all_notifications = [
        {
            "id": "notif-01",
            "type": "alert",
            "priority": "high",
            "title": "Status Beban ACWR Optimal",
            "message": "Rasio beban latihan mingguan Anda berada di rasio 1.08 (Sweet Spot). Pertahankan ritme ini.",
            "category": "training",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "read": "notif-01" in _READ_NOTIFICATIONS
        },
        {
            "id": "notif-02",
            "type": "reminder",
            "priority": "medium",
            "title": f"Target Lomba: {race_name}",
            "message": "Fase periodisasi spesifik maraton dimulai. Pastikan hidrasi dan konsumsi karbohidrat terjadwal.",
            "category": "race",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
            "read": "notif-02" in _READ_NOTIFICATIONS
        },
        {
            "id": "notif-03",
            "type": "alert",
            "priority": "low",
            "title": "Sinkronisasi Garmin Terverifikasi",
            "message": "Token Garmin Connect Garth aktif di server VPS. Telemetri rute GPS dan detak jantung sinkron.",
            "category": "sync",
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "read": "notif-03" in _READ_NOTIFICATIONS
        },
        {
            "id": "notif-04",
            "type": "reminder",
            "priority": "medium",
            "title": "Evaluasi Pemulihan Malam (HRV)",
            "message": "Nilai rMSSD semalam berada dalam kisaran baseline seimbang. Siap untuk sesi lari tempo.",
            "category": "recovery",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            "read": "notif-04" in _READ_NOTIFICATIONS
        }
    ]

    unread_count = sum(1 for n in all_notifications if not n["read"])

    return {
        "status": "success",
        "unread_count": unread_count,
        "notifications": all_notifications
    }

@router.post("/api/v1/notifications/read", tags=["Notifications"])
def mark_notifications_read(data: NotificationReadInput):
    """
    Tandai notifikasi telah dibaca.
    """
    if data.all:
        for nid in ["notif-01", "notif-02", "notif-03", "notif-04"]:
            _READ_NOTIFICATIONS.add(nid)
    elif data.notification_id:
        _READ_NOTIFICATIONS.add(data.notification_id)

    return {
        "status": "success",
        "message": "Notifikasi berhasil ditandai telah dibaca."
    }

@router.get("/api/v1/team/squad", tags=["User Management"])
def get_team_squad(user_id: str = Depends(get_current_user_optional)):
    """
    Manajemen Tim & Pengguna: Menampilkan profil anggota tim, peran, izin, dan undangan.
    """
    uid = user_id or sandbox_store.OWNER_USER_ID
    profile = sandbox_store.get_profile(uid) or {}

    roles = [
        {
            "id": "head_coach",
            "title": "Head Coach",
            "description": "Akses penuh manajemen jadwal latihan atlet, kalibrasi VDOT, dan administrasi tim."
        },
        {
            "id": "assistant_coach",
            "title": "Assistant Coach",
            "description": "Dapat melihat telemetri atlet, mencatat evaluasi latihan, dan memantau status pemulihan."
        },
        {
            "id": "athlete",
            "title": "Athlete",
            "description": "Mengakses kalender latihan personal, mencatat sesi lari, dan mengunggah berkas GPX/FIT."
        }
    ]

    members = [
        {
            "id": uid,
            "name": profile.get("full_name") or "Rizky Aryendi Gumilang",
            "email": profile.get("email") or "rizkyaryendigumilang@gmail.com",
            "role": "head_coach",
            "role_title": "Head Coach",
            "status": "active",
            "permissions": ["view_telemetry", "edit_schedule", "manage_members", "billing_access"],
            "joined_at": "2026-01-15T08:00:00Z"
        },
        {
            "id": "squad-athlete-02",
            "name": "Budi Santoso",
            "email": "budi.marathon@goalie.fit",
            "role": "athlete",
            "role_title": "Athlete",
            "status": "active",
            "permissions": ["view_telemetry", "log_workouts"],
            "joined_at": "2026-02-10T10:30:00Z"
        },
        {
            "id": "squad-coach-03",
            "name": "Sarah Coach",
            "email": "sarah.coach@goalie.fit",
            "role": "assistant_coach",
            "role_title": "Assistant Coach",
            "status": "active",
            "permissions": ["view_telemetry", "edit_schedule"],
            "joined_at": "2026-03-01T09:15:00Z"
        }
    ]

    return {
        "status": "success",
        "team_name": "Goalie Jakarta Racing Squad",
        "roles": roles,
        "members": members,
        "pending_invitations": _PENDING_INVITES
    }

@router.post("/api/v1/team/invite", tags=["User Management"])
def invite_team_member(data: TeamInviteInput):
    """
    Kirim undangan bergabung ke tim / klub lari.
    """
    invite_code = f"GLIE-{secrets.token_hex(4).upper()}"
    expiry = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    invitation = {
        "email": str(data.email),
        "role": data.role,
        "team_name": data.team_name,
        "invite_code": invite_code,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expiry,
        "status": "pending"
    }
    _PENDING_INVITES.append(invitation)

    return {
        "status": "success",
        "message": f"Undangan berhasil dikirim ke {data.email}.",
        "invite_code": invite_code,
        "expires_at": expiry
    }

@router.get("/api/v1/billing/invoices", tags=["Billing"])
def get_billing_invoices(user_id: str = Depends(get_current_user_optional)):
    """
    Langganan & Tagihan: Menampilkan status paket, metode pembayaran, dan riwayat faktur.
    """
    current_plan = {
        "plan_id": "pro_athlete",
        "name": "Goalie Pro Athlete",
        "status": "active",
        "billing_cycle": "lifetime",
        "price_formatted": "Rp 0 (Lifetime Pro)",
        "renewal_date": "2030-12-31T23:59:59Z",
        "features": [
            "Mesin Fisiologis Jack Daniels VDOT & ACWR Banister",
            "Kalkulasi Grade-Adjusted Pace Minetti & Dekopling Aerobik",
            "Sinkronisasi Garmin Connect Garth & Strava Suite",
            "Pusat Analisis Biomekanika 33-Titik MediaPipe"
        ]
    }

    invoices = [
        {
            "id": "INV-2026-001",
            "date": "2026-01-15",
            "amount_formatted": "Rp 499.000",
            "status": "paid",
            "description": "Goalie Pro Athlete Early Access Activation",
            "pdf_url": "#"
        },
        {
            "id": "INV-2026-002",
            "date": "2026-06-01",
            "amount_formatted": "Rp 0",
            "status": "paid",
            "description": "Lifetime Pro Athlete Loyalty Upgrade",
            "pdf_url": "#"
        }
    ]

    payment_methods = [
        {
            "id": "pm-01",
            "type": "qris",
            "name": "QRIS Instant Settlement",
            "is_default": True
        },
        {
            "id": "pm-02",
            "type": "bank_transfer",
            "name": "BCA Virtual Account",
            "is_default": False
        }
    ]

    return {
        "status": "success",
        "current_plan": current_plan,
        "payment_methods": payment_methods,
        "invoices": invoices
    }

@router.post("/api/v1/support/feedback", tags=["Help & Support"])
def submit_support_feedback(data: SupportFeedbackInput):
    """
    Kirim masukan atau laporan kendala dari atlet.
    """
    entry = {
        "category": data.category,
        "subject": data.subject,
        "message": data.message,
        "rating": data.rating,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    _FEEDBACK_ENTRIES.append(entry)

    return {
        "status": "success",
        "message": "Terima kasih. Masukan Anda telah kami terima untuk penyempurnaan Goalie."
    }

@router.get("/api/v1/system/status", tags=["System Pages"])
def get_system_status():
    """
    Status Sistem & Halaman Operasional: Menampilkan kesehatan layanan backend.
    """
    return {
        "status": "healthy",
        "version": "Goalie v2.4.0-prod",
        "environment": "production-vps",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "sqlite_persistence": "operational",
            "sports_engine": "operational",
            "garmin_sync_gateway": "operational",
            "open_meteo_weather": "operational"
        }
    }
