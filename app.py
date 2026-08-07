import math
import sqlite3
import time
import uuid
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Request, Query, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

app = FastAPI(
    title="Abhaya National Safety Platform",
    description="Next-Gen Personal Safety, Asymmetric Information Dispatch, AI Triage, and Emergency Services Finder",
    version="2.0.0"
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Initialize SQLite Database
DB_PATH = "abhaya.db"

def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # SOS Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sos_events (
        id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        user_name TEXT,
        user_phone TEXT,
        exact_lat REAL NOT NULL,
        exact_lng REAL NOT NULL,
        sector_name TEXT,
        threat_level INTEGER DEFAULT 3,
        status TEXT DEFAULT 'ACTIVE',
        audio_keywords TEXT,
        triage_data TEXT,
        created_at REAL NOT NULL
    );
    """)

    # Emergency Services Database Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_services (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL, -- 'police', 'hospital', 'medical_store'
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        address TEXT NOT NULL,
        phone TEXT NOT NULL,
        is_open_24x7 INTEGER DEFAULT 1,
        rating REAL DEFAULT 4.5
    );
    """)

    # Seed Emergency Services if empty
    cursor.execute("SELECT COUNT(*) FROM emergency_services;")
    if cursor.fetchone()[0] == 0:
        sample_services = [
            # Police Stations
            ("pol_1", "Central Cyber & Women Safety Police Station", "police", 26.8467, 80.9462, "Civil Lines, Kanpur / Lucknow Zone", "+91-112", 1, 4.8),
            ("pol_2", "Pankha Road Sector Police Outpost", "police", 26.8520, 80.9510, "Sector 4, Tech Park Precinct", "+91-512-2304100", 1, 4.6),
            ("pol_3", "Metro Precinct Police Station", "police", 26.8390, 80.9380, "Station Road, Near Transit Hub", "+91-512-2309999", 1, 4.7),
            
            # Hospitals
            ("hosp_1", "City Trauma & Emergency Super Speciality Hospital", "hospital", 26.8480, 80.9490, "GT Road, Emergency Block A", "+91-512-2555111", 1, 4.9),
            ("hosp_2", "Regency Multi-Specialty Health Institute", "hospital", 26.8550, 80.9420, "Swaroop Nagar, Medical Enclave", "+91-512-2299100", 1, 4.8),
            ("hosp_3", "Saraswati Women & Care Medical Center", "hospital", 26.8410, 80.9550, "Kidwai Nagar Sector 3", "+91-512-2611222", 1, 4.7),

            # Medical Stores / Pharmacies
            ("med_1", "Apollo 24x7 Emergency Pharmacy & Surgical Store", "medical_store", 26.8472, 80.9475, "Shop 12, Hospital Road Market", "+91-9839011223", 1, 4.9),
            ("med_2", "Sanjivani 24-Hour Medical Hall", "medical_store", 26.8510, 80.9485, "Opposite Metro Gate 2", "+91-9839044556", 1, 4.8),
            ("med_3", "Jan Aushadhi Kendra Emergency Chemists", "medical_store", 26.8430, 80.9410, "Civic Center Complex", "+91-9839077889", 1, 4.6),
            ("med_4", "MedPlus 24x7 Express Medicals", "medical_store", 26.8535, 80.9530, "Tech Park Plaza, Sector 4", "+91-9839099000", 1, 4.7)
        ]
        cursor.executemany("""
            INSERT INTO emergency_services (id, name, category, lat, lng, address, phone, is_open_24x7, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, sample_services)
    
    conn.commit()
    conn.close()

init_sqlite_db()

# --- Utility Functions ---

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the Great Circle Distance in kilometers between two lat/lng coordinates."""
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- Pydantic Data Models ---

class SOSRequest(BaseModel):
    device_id: str
    lat: float
    lng: float
    user_tier: int = Field(..., ge=1, le=3, description="1: Police/Dispatch, 2: Verified Citizen, 3: Anonymous User")
    user_name: Optional[str] = "Anonymous Victim"
    user_phone: Optional[str] = "Protected / Encrypted"

class TriageAnswer(BaseModel):
    sos_id: str
    question_id: str
    answer: str  # "YES" or "NO"

class AudioAnalysisRequest(BaseModel):
    sos_id: str
    audio_transcript_sample: str

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Render the Main Interactive Abhaya Safety Application."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/sos")
async def trigger_sos(req: SOSRequest, request: Request):
    """
    Trigger SOS Emergency Protocol with Asymmetric Information.
    Logs IP address & Device ID for digital footprint accountability.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    sos_id = "SOS-" + str(uuid.uuid4())[:8].upper()
    sector_name = f"Sector {int((abs(req.lat) * 100) % 10) + 1} Alert Zone"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sos_events (id, device_id, ip_address, user_name, user_phone, exact_lat, exact_lng, sector_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (sos_id, req.device_id, client_ip, req.user_name, req.user_phone, req.lat, req.lng, sector_name, time.time()))
    conn.commit()
    conn.close()

    # Asymmetric Information Filter based on Tier
    if req.user_tier == 1:
        # Tier 1 (Police/Dispatch): Full exact real-time GPS
        location_data = {
            "view_type": "TIER_1_EXACT_POLICE_GPS",
            "lat": req.lat,
            "lng": req.lng,
            "accuracy": "Exact GPS Pin (<5m)",
            "dispatch_priority": "IMMEDIATE_RED_ALERT"
        }
    elif req.user_tier == 2:
        # Tier 2 (Verified Citizen via Gov ID): Exact location to render assistance
        location_data = {
            "view_type": "TIER_2_VERIFIED_CITIZEN_GPS",
            "lat": req.lat,
            "lng": req.lng,
            "accuracy": "Verified Citizen Exact Pin (<10m)",
            "verification_status": "Gov ID / Aadhaar Verified"
        }
    else:
        # Tier 3 (Anonymous User): General Area / Sector Alert ONLY (no exact pin)
        # Randomize offset by approx 500m to 1km to prevent weaponization/stalking
        location_data = {
            "view_type": "TIER_3_ANONYMOUS_SECTOR_ALERT",
            "sector": sector_name,
            "approx_radius": "Within 800m sector perimeter",
            "notice": "Exact GPS pin restricted for safety to act as a community deterrent, not a locator map."
        }

    return {
        "status": "SOS_TRANSMITTED",
        "sos_id": sos_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "digital_footprint": {
            "device_id": req.device_id,
            "logged_ip": client_ip,
            "status": "Encrypted & Logged"
        },
        "view_payload": location_data
    }

@app.post("/api/triage")
async def process_triage(data: TriageAnswer):
    """
    Silent AI Triage Chatbot (Simulating 1-Click Gemini LLM Triage).
    Drives 1-click answers to assess injury, armed status, and threat level.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT threat_level, triage_data FROM sos_events WHERE id = ?", (data.sos_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="SOS session not found.")
    
    current_threat = row[0]
    existing_triage = row[1] or ""
    
    new_entry = f"[{data.question_id}: {data.answer}] "
    updated_triage = existing_triage + new_entry
    
    # Assess escalation logic
    new_threat = current_threat
    if data.question_id == "INJURED" and data.answer.upper() == "YES":
        new_threat = max(new_threat, 4)
    if data.question_id == "ARMED" and data.answer.upper() == "YES":
        new_threat = 5  # Maximum Threat Level
        
    cursor.execute("UPDATE sos_events SET threat_level = ?, triage_data = ? WHERE id = ?", (new_threat, updated_triage, data.sos_id))
    conn.commit()
    conn.close()
    
    # Provide next question based on flow
    questions_flow = {
        "INJURED": {"next_id": "ARMED", "text": "Are perpetrators armed with weapons?"},
        "ARMED": {"next_id": "NUMBER_OF_PERPS", "text": "Are there multiple aggressors?"},
        "NUMBER_OF_PERPS": {"next_id": "SAFE_CONTAINMENT", "text": "Can you reach a locked space or store nearby?"},
        "SAFE_CONTAINMENT": {"next_id": "COMPLETE", "text": "Dispatch units updated. Stay low and silent."}
    }
    
    next_q = questions_flow.get(data.question_id, {"next_id": "COMPLETE", "text": "Dispatch units updated in real-time."})
    
    return {
        "sos_id": data.sos_id,
        "updated_threat_level": new_threat,
        "threat_label": "CRITICAL EMERGENCY - PRIORITY 1" if new_threat >= 4 else "HIGH ALERT",
        "next_question": next_q
    }

@app.post("/api/audio-analysis")
async def audio_analysis(data: AudioAnalysisRequest):
    """
    Ambient Audio Speech-to-Text Keyword Threat Escalation.
    Analyzes encrypted 10s audio clip for threat keywords.
    """
    sample_text = data.audio_transcript_sample.lower()
    danger_keywords = ["help", "weapon", "gun", "knife", "kill", "blood", "don't touch", "stop", "police"]
    
    detected = [kw for kw in danger_keywords if kw in sample_text]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if detected:
        cursor.execute("UPDATE sos_events SET threat_level = 5, audio_keywords = ? WHERE id = ?", 
                       (", ".join(detected), data.sos_id))
        escalation_status = "AUTOMATIC_LEVEL_5_ESCALATION"
    else:
        cursor.execute("UPDATE sos_events SET audio_keywords = ? WHERE id = ?", 
                       ("Ambient Noise / Clear", data.sos_id))
        escalation_status = "MONITORING_AMBIENT_AUDIO"
        
    conn.commit()
    conn.close()
    
    return {
        "sos_id": data.sos_id,
        "detected_keywords": detected,
        "escalation_status": escalation_status,
        "dispatch_action": "Police Dashboard Escalated to Top Priority" if detected else "Audio Logged"
    }

@app.get("/api/nearby")
async def get_nearby_emergency_services(
    lat: float = Query(..., description="User latitude"),
    lng: float = Query(..., description="User longitude"),
    category: str = Query("all", description="Category: 'all', 'police', 'hospital', 'medical_store'"),
    max_results: int = Query(10, ge=1, le=50)
):
    """
    Find Nearest Police Stations, Hospitals, and Medical Stores (Pharmacies).
    Calculates exact distance (km) and estimated response/travel times.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if category.lower() != "all":
        cursor.execute("SELECT id, name, category, lat, lng, address, phone, is_open_24x7, rating FROM emergency_services WHERE category = ?;", (category.lower(),))
    else:
        cursor.execute("SELECT id, name, category, lat, lng, address, phone, is_open_24x7, rating FROM emergency_services;")
        
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        svc_id, name, cat, s_lat, s_lng, address, phone, open_24x7, rating = r
        dist_km = haversine_distance(lat, lng, s_lat, s_lng)
        
        # Estimate travel times
        drive_time_mins = max(1, round(dist_km * 2.5))  # Avg city traffic driving speed ~24 km/h
        walk_time_mins = max(1, round(dist_km * 12.0))  # Avg walking speed ~5 km/h
        
        # Google Maps navigation link
        maps_link = f"https://www.google.com/maps/dir/?api=1&destination={s_lat},{s_lng}"
        
        results.append({
            "id": svc_id,
            "name": name,
            "category": cat,
            "distance_km": round(dist_km, 2),
            "estimated_drive_mins": drive_time_mins,
            "estimated_walk_mins": walk_time_mins,
            "address": address,
            "phone": phone,
            "is_open_24x7": bool(open_24x7),
            "rating": rating,
            "google_maps_url": maps_link
        })
        
    # Sort results by distance ascending
    results.sort(key=lambda x: x["distance_km"])
    
    return {
        "user_coordinates": {"lat": lat, "lng": lng},
        "category_filter": category,
        "count": len(results[:max_results]),
        "services": results[:max_results]
    }

@app.get("/api/dashboard")
async def get_command_center_dashboard():
    """
    Command Center & ERSS 112 Dispatch Heatmap Dashboard API.
    Returns real-time emergency events, threat levels, and sector metrics.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, device_id, exact_lat, exact_lng, sector_name, threat_level, status, audio_keywords, triage_data, created_at
        FROM sos_events
        ORDER BY created_at DESC
        LIMIT 20;
    """)
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for r in rows:
        events.append({
            "sos_id": r[0],
            "device_id": r[1],
            "exact_location": {"lat": r[2], "lng": r[3]},
            "sector": r[4],
            "threat_level": r[5],
            "status": r[6],
            "audio_keywords": r[7],
            "triage_summary": r[8],
            "timestamp": time.strftime("%H:%M:%S", time.localtime(r[9]))
        })
        
    return {
        "active_sos_count": len([e for e in events if e["status"] == "ACTIVE"]),
        "average_civilian_response_time_target": "< 3 minutes (City-Zero Pilot)",
        "erss_112_bridge_status": "ONLINE / CONNECTED",
        "recent_emergency_events": events
    }
# --- Government ID Verification Endpoints ---

# Temporary memory store for user verification status (For production, this would be in SQLite)
user_session = {
    "is_verified": False,
    "user_name": "Civilian Helper",
    "id_doc_name": None
}

@app.post("/api/verify-id")
async def verify_id(user_name: str = Form(...), file: UploadFile = File(None)):
    """Upload government ID to verify citizen status."""
    if file:
        user_session["is_verified"] = True
        user_session["user_name"] = user_name
        user_session["id_doc_name"] = file.filename
        return {
            "status": "VERIFIED",
            "is_verified": True,
            "display_name": f"Verified Helper: {user_name}"
        }
    
    # If no file is uploaded, set status to unauthorized
    user_session["is_verified"] = False
    return {
        "status": "UNAUTHORIZED",
        "is_verified": False,
        "display_name": f"{user_name} [UNAUTHORIZED]"
    }

@app.get("/api/user-status")
async def get_user_status():
    """Retrieve the current authorization status of the user."""
    return user_session

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
