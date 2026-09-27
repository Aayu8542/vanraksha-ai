from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import os
import json
try:
    from .orchestrator import advance_fire_cycle
    from .simulation_service import SimulationError, create_simulation, get_simulation, run_simulation
    from .events import sse_encode
except ImportError:
    from orchestrator import advance_fire_cycle
    from simulation_service import SimulationError, create_simulation, get_simulation, run_simulation
    from events import sse_encode

app = Flask(__name__)
CORS(app) # Allow frontend to call the API


def _simulation_error(error):
    return jsonify({"error": str(error)}), 400


@app.route('/api/simulation/start', methods=['POST'])
def api_simulation_start():
    try:
        return jsonify(create_simulation(request.get_json(silent=True) or {})), 201
    except SimulationError as error:
        return _simulation_error(error)


@app.route('/api/simulation/<simulation_id>/run', methods=['POST'])
def api_simulation_run(simulation_id):
    try:
        return jsonify(run_simulation(simulation_id))
    except SimulationError as error:
        return _simulation_error(error)


@app.route('/api/simulation/<simulation_id>', methods=['GET'])
def api_simulation_get(simulation_id):
    try:
        return jsonify(get_simulation(simulation_id))
    except SimulationError as error:
        return jsonify({"error": str(error)}), 404


@app.route('/api/simulation/<simulation_id>/<output>', methods=['GET'])
def api_simulation_output(simulation_id, output):
    if output not in {'timeline', 'fire-spread', 'risk-map', 'biodiversity-impact', 'response-plan'}:
        return jsonify({"error": "Unknown simulation output"}), 404
    try:
        state = get_simulation(simulation_id)
    except SimulationError as error:
        return jsonify({"error": str(error)}), 404
    output_key = {'fire-spread': 'fire_spread', 'risk-map': 'risk_map', 'biodiversity-impact': 'biodiversity', 'response-plan': 'response'}.get(output, output)
    return jsonify(state[output_key])


@app.route('/api/simulation/<simulation_id>/events', methods=['GET'])
def api_simulation_events(simulation_id):
    try:
        state = get_simulation(simulation_id)
    except SimulationError as error:
        return jsonify({"error": str(error), "code": "SIMULATION_NOT_FOUND"}), 404
    return Response(sse_encode(state.get("events", [])), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

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
