import os
import time
import json
import base64
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from cryptography.fernet import Fernet

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

# نفس مفتاح التشفير الموجود بداخل تطبيق activation_2.py
SECRET_KEY = b'fL5Z5bgrVzXAgMrKXwR2rokpyD64D0h7TTRCkZDQUBM='
cipher = Fernet(SECRET_KEY)

class TrialRequest(BaseModel):
    serial_number: str

def generate_fernet_trial_code(serial: str) -> str:
    # حساب وقت انتهاء الـ 3 أيام بالثواني
    exp_timestamp = time.time() + (3 * 86400)
    
    # الصياغة النصية التي يتعرف عليها التطبيق: TRIAL:DEVICE_ID:EXPIRY_TIMESTAMP
    payload = f"TRIAL:{serial}:{exp_timestamp}"
    
    # التشفير بـ Fernet وتحويله لصيغة Base64 ليتوافق مع فك التشفير في التطبيق
    encrypted_token = cipher.encrypt(payload.encode())
    return base64.urlsafe_b64encode(encrypted_token).decode()

@app.post("/generate-trial")
def generate_trial(req: TrialRequest):
    serial = req.serial_number.strip()
    if not serial:
        raise HTTPException(status_code=400, detail="السيريال مطلوب")

    # 1. البحث عن السيريال في قاعدة البيانات
    response = supabase.table("trial_devices").select("*").eq("device_id", serial).execute()
    existing = response.data

    if existing:
        device = existing[0]
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
            "activation_code": device.get("activation_code"),
            "days_left": days_left,
            "message": f"تمت استعادة كود التفعيل المجاني الخاص بك. متبقي {days_left} أيام."
        }

    # 2. توليد كود التفعيل لـ 3 أيام مطابق لتطبيق الديسكتوب
    act_code = generate_fernet_trial_code(serial)
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
