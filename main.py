import os
import base64
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cryptography.fernet import Fernet
from supabase import create_client, Client

# مفتاح التشفير الخاص بـ Proma
SECRET_KEY = b'fL5Z5bgrVzXAgMrKXwR2rokpyD64D0h7TTRCkZDQUBM='
cipher = Fernet(SECRET_KEY)

# بيانات Supabase الخاصة بك
SUPABASE_URL = "https://uszbqlcighavafvmrhfr.supabase.co"
SUPABASE_KEY = "sb_publishable_ciTaxf6GVUJFPDckPWdJXg_1YtSM-bv"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrialRequest(BaseModel):
    device_id: str

def generate_trial_token(device_id: str) -> str:
    expiry_time = datetime.now(timezone.utc) + timedelta(days=3)
    expiry_timestamp = int(expiry_time.timestamp())
    payload = f"TRIAL:{device_id.strip()}:{expiry_timestamp}"
    token = cipher.encrypt(payload.encode())
    return base64.urlsafe_b64encode(token).decode()

@app.post("/api/request-trial")
async def request_trial(data: TrialRequest, request: Request):
    device_id = data.device_id.strip()
    client_ip = request.client.host if request.client else "Unknown"

    if not device_id:
        raise HTTPException(status_code=400, detail="يرجى إدخال سيريال الجهاز الصحيح.")

    # فحص إذا كان الجهاز مسجلاً من قبل
    existing = supabase.table("trial_devices").select("device_id").eq("device_id", device_id).execute()
    
    if len(existing.data) > 0:
        return {
            "success": False,
            "message": "عفواً، لقد تم استخدام التجربة المجانية لهذا الجهاز من قبل."
        }

    # توليد الكود والتسجيل
    trial_code = generate_trial_token(device_id)

    supabase.table("trial_devices").insert({
        "device_id": device_id,
        "ip_address": client_ip
    }).execute()

    return {
        "success": True,
        "message": "تم إنشاء كود التجربة المجانية بنجاح!",
        "trial_code": trial_code
    }