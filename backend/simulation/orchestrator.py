import json
import os
import datetime
from stage5_refinement import run_stage5_refinement
from escalation_engine import evaluate_escalation
from notifications import send_escalation_email
from part_a_simulation import run_ensemble_simulation

# Attempt to initialize Supabase
SUPABASE_URL = "https://nxmcutaokxyrnvhyjvsj.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
supabase = None
try:
    from supabase import create_client
    if SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except ImportError:
    pass

def load_config(config_path="config.json"):
    with open(config_path, 'r') as f:
        return json.load(f)

def advance_fire_cycle(fire_id, demo_mode=True):
    """
    Orchestrator to advance the fire cycle.
    1. Loads archive JSON.
    2. Determines next state (Trigger Stage 5 if not run, else advance simulation).
    3. Evaluates Escalation.
    4. Sends Email if escalated.
    5. Updates Supabase for Realtime UI.
    """
    archive_path = os.path.join("fire_archive", f"{fire_id}.json")
    if not os.path.exists(archive_path):
        return {"error": f"No active fire archive found for {fire_id}. Must start from Stage 4."}
        
    with open(archive_path, 'r') as f:
        record = json.load(f)
        
    status = record.get("final_status", "active")
    if status in ["Contained", "False Alarm", "No Fire"]:
        return {"error": f"Fire {fire_id} is already marked as {status}. Stopping cycles."}
        
    cycle_count = record.get("cycle_count", 0) + 1
    record["cycle_count"] = cycle_count
    
    config = load_config()
    lat = record.get("original_lat")
    lng = record.get("original_lng")
    
    changes = []
    
    # Logic for State Progression
    if cycle_count == 1:
        # Trigger Stage 5 FIRMS Refinement
        print("Cycle 1: Triggering Stage 5 FIRMS Refinement...")
        # We temporarily save a stage4-only json to pass to run_stage5
        tmp_s4 = "tmp_s4.json"
        with open(tmp_s4, 'w') as f: json.dump(record["stage4_original"], f)
        
        _, stage5_rec = run_stage5_refinement(tmp_s4, lat, lng, demo_mode=demo_mode)
        
        record["stage5_refinement"] = stage5_rec.get("stage5_refinement")
        record["stage5_corrected_simulation"] = stage5_rec.get("stage5_corrected_simulation")
        
        # Check if confidence dropped / flagged
        flags = record["stage5_refinement"].get("flags", {})
        if flags.get("simulation_deviation"):
            record["confidence"] = "Low (Simulation Deviation)"
            changes.append("Confidence adjusted due to simulation deviation.")
        elif flags.get("partial_deviation"):
            changes.append("Partial deviation flagged by FIRMS.")
            
        changes.append("Stage 5 FIRMS data integrated.")
        
    else:
        # Re-run corrected simulation for more steps
        print(f"Cycle {cycle_count}: Pushing simulation horizon further...")
        cfg_steps = config.get("stage5_refinement", {}).get("resimulate_steps", 6)
        total_steps = cfg_steps + (cycle_count - 1) * 3  # Add 30 mins each cycle
        
        firms_poly_geojson = record.get("stage5_refinement", {}).get("firms_perimeter")
        if firms_poly_geojson:
            from shapely.geometry import shape
            firms_poly = shape(firms_poly_geojson)
            sim_res = run_ensemble_simulation(
                lat, lng, 
                config_path="config.json", 
                num_steps_override=total_steps, 
                firms_polygon=firms_poly
            )
            record["stage5_corrected_simulation"] = sim_res
            changes.append(f"Simulation advanced to +{total_steps * 10} minutes.")
            
    # Evaluate Escalation
    stg4_data = record.get("stage4_original")
    new_level = evaluate_escalation(config, stg4_data, record)
    
    current_level = record.get("escalation_level_sent", "None")
    
    hierarchy = {"None": 0, "Range": 1, "Division": 2, "SDMA_NDMA": 3}
    
    if hierarchy.get(new_level, 0) > hierarchy.get(current_level, 0):
        print(f"Escalating from {current_level} to {new_level}!")
        loc_str = f"Lat: {lat:.4f}, Lng: {lng:.4f}"
        conf = record.get("confidence", "Medium")
        intensity = record.get("stage5_refinement", {}).get("intensity", "Unknown")
        
        sent = send_escalation_email(config, new_level, fire_id, loc_str, conf, intensity)
        if sent:
            record["escalation_level_sent"] = new_level
            record["escalation_log"] = record.get("escalation_log", []) + [
                {"level": new_level, "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}
            ]
            changes.append(f"Escalation email sent to {new_level} authority.")
    
    record["last_updated"] = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Save Archive
    with open(archive_path, 'w') as f:
        json.dump(record, f, indent=4)
        
    # Update Supabase for Realtime UI
    if supabase:
        try:
            # We assume there is a 'fire_events_archive' table
            # Alternatively we just update the 'alerts' table
            update_payload = {
                "confidence": record.get("confidence", "Medium"),
                "notes": f"Escalation: {record.get('escalation_level_sent', 'Range')} | {len(changes)} new updates."
            }
            # Attempt to update alerts table
            supabase.table('alerts').update(update_payload).eq('id', fire_id).execute()
            
            # Upsert into fire_events_archive
            supabase.table('fire_events_archive').upsert({
                "id": fire_id,
                "data": record
            }).execute()
        except Exception as e:
            print(f"Supabase update failed: {e}")
            
    return {
        "status": "success",
        "fire_id": fire_id,
        "cycle_count": cycle_count,
        "escalation_level": record.get("escalation_level_sent", "Range"),
        "changes": changes
    }
