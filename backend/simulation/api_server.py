from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from orchestrator import advance_fire_cycle

app = Flask(__name__)
CORS(app) # Allow frontend to call the API

@app.route('/api/advance_cycle', methods=['POST'])
def api_advance_cycle():
    data = request.json
    fire_id = data.get('fire_id')
    demo_mode = data.get('demo_mode', True)
    
    if not fire_id:
        return jsonify({"error": "fire_id is required"}), 400
        
    try:
        result = advance_fire_cycle(fire_id, demo_mode=demo_mode)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_status', methods=['POST'])
def api_update_status():
    """
    Sets the final resolution status (e.g., Contained).
    """
    data = request.json
    fire_id = data.get('fire_id')
    status = data.get('status')
    
    archive_path = os.path.join("fire_archive", f"{fire_id}.json")
    if os.path.exists(archive_path):
        with open(archive_path, 'r') as f:
            record = json.load(f)
            
        record["final_status"] = status
        with open(archive_path, 'w') as f:
            json.dump(record, f, indent=4)
            
        # Update Supabase if possible
        try:
            from orchestrator import supabase
            if supabase:
                supabase.table('alerts').update({'status': status.lower().replace(' ', '_')}).eq('id', fire_id).execute()
        except Exception as e:
            print("Failed to update supabase:", e)
            
        return jsonify({"status": "success", "message": f"Fire marked as {status}"})
    else:
        return jsonify({"error": "Archive not found"}), 404

if __name__ == '__main__':
    # Run on port 5001 to avoid conflicts with frontend dev server
    app.run(port=5001, debug=True)
