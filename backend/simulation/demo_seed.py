import json
import os
import datetime
import requests
from run_stage4 import run_stage4_pipeline

# From supabaseClient.js
SUPABASE_URL = 'https://nxmcutaokxyrnvhyjvsj.supabase.co'
SUPABASE_ANON_KEY = 'sb_publishable_t-kse4BP5x_GuHSAP-UwiQ_auOcZ4Qz'

def seed_demo_fire():
    fire_id = "sample_fire_01"
    lat, lng = 30.1472, 78.5925
    
    print(f"Setting up Demo Fire: {fire_id} at [{lat}, {lng}]")
    
    # 1. Generate Stage 4 Base Data
    tmp_json = "tmp_demo_stage4.json"
    print("Generating base Stage 4 simulation...")
    run_stage4_pipeline(fire_id, lat, lng, tmp_json, no_map=True)
    
    with open(tmp_json, 'r') as f:
        stage4_data = json.load(f)
        
    os.remove(tmp_json)
    
    # 2. Create Archive Record at Cycle 0
    record = {
        "fire_id": fire_id,
        "original_lat": lat,
        "original_lng": lng,
        "cycle_count": 0,
        "confidence": "Medium",
        "stage4_original": stage4_data,
        "final_status": "active",
        "escalation_level_sent": "None",
        "escalation_log": [],
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    os.makedirs("fire_archive", exist_ok=True)
    archive_path = os.path.join("fire_archive", f"{fire_id}.json")
    with open(archive_path, 'w') as f:
        json.dump(record, f, indent=4)
        
    print(f"Local archive seeded at {archive_path}")
    
    # 3. Seed Supabase Alerts Table
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    
    payload = {
        "id": fire_id,
        "created_at": (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).isoformat() + "Z",
        "lat": lat,
        "lng": lng,
        "radius_m": 250,
        "confidence": "Medium",
        "zone_id": "ZONE_NORTH",
        "status": "confirmed",
        "confirmed_by": "demo_ranger@vanaraksha.in",
        "confirmed_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    # We use upsert (POST with Prefer: resolution=merge-duplicates requires unique constraint, 
    # if not we might just do a UPSERT via POST if supported, else assume it works or fails cleanly)
    # Supabase REST API for UPSERT
    url = f"{SUPABASE_URL}/rest/v1/alerts"
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            print("Successfully seeded Supabase 'alerts' table.")
        elif res.status_code == 409:
            # Conflict, let's update instead
            patch_url = f"{url}?id=eq.{fire_id}"
            res_patch = requests.patch(patch_url, headers=headers, json=payload)
            if res_patch.status_code in [200, 204]:
                print("Successfully updated existing record in Supabase 'alerts' table.")
            else:
                print(f"Failed to update Supabase. Code: {res_patch.status_code}, Body: {res_patch.text}")
        else:
             print(f"Failed to seed Supabase. Code: {res.status_code}, Body: {res.text}")
    except Exception as e:
        print("Could not reach Supabase:", e)
        
    # Also attempt to seed fire_events_archive table if it exists
    try:
        archive_payload = {
            "id": fire_id,
            "data": record
        }
        res_arch = requests.post(f"{SUPABASE_URL}/rest/v1/fire_events_archive", headers=headers, json=archive_payload)
        if res_arch.status_code == 409:
            requests.patch(f"{SUPABASE_URL}/rest/v1/fire_events_archive?id=eq.{fire_id}", headers=headers, json=archive_payload)
    except:
        pass
        
    print("\n✅ Demo Seed Complete!")
    print("You can now open the Ranger Dashboard, select the confirmed fire, and click 'Simulate Next Update'.")

if __name__ == "__main__":
    seed_demo_fire()
