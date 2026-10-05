import os
import hashlib
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://uszbqlcighavafvmrhfr.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_ciTaxf6GVUJFPDckPWdJXg_1YtSM-bv")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class TrialRequest(BaseModel):
    serial_number: str

def generate_code(serial: str) -> str:
    # توليد كود تفعيل مشفر مقروء بناءً على السيريال
    raw = f"{serial}_PROMA_TRIAL_SECRET"
    digest = hashlib.sha256(raw.encode()).hexdigest().upper()
    return f"PROMA-3D-{digest[:4]}-{digest[4:8]}"

@app.post("/generate-trial")
def generate_trial(req: TrialRequest):
    serial = req.serial_number.strip().upper()
    if not serial:
        raise HTTPException(status_code=400, detail="السيريال مطلوب")

    # 1. البحث عن السيريال في قاعدة البيانات
    response = supabase.table("trial_devices").select("*").eq("device_id", serial).execute()
    existing = response.data

    if existing:
        device = existing[0]
        # حساب المتبقي من الـ 3 أيام
        created_at = datetime.fromisoformat(device["created_at"].replace("Z", "+00:00"))
        expires_at = created_at + timedelta(days=3)
        now = datetime.now(created_at.tzinfo)

        if now > expires_at:
            return {
                "success": False,
                "message": "انتهت الفترة التجريبية (3 أيام) لهذا الجهاز مسبقاً."
            }
        
        days_left = max(1, (expires_at - now).days + 1)
        return {
            "success": True,
            "activation_code": device.get("activation_code", generate_code(serial)),
            "days_left": days_left,
            "message": f"تمت استعادة كود التفعيل المجاني. متبقي {days_left} أيام."
        }

    # 2. تسجيل جهاز جديد لمدة 3 أيام
    act_code = generate_code(serial)
    new_device = {
        "device_id": serial,
        "activation_code": act_code
    }
    supabase.table("trial_devices").insert(new_device).execute()

    return {
        "success": True,
        "activation_code": act_code,
        "days_left": 3,
        "message": "تم إنشاء كود التفعيل المجاني بنجاح لمدة 3 أيام!"
    }
