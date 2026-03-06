"""
Clinical Triage Agent - Main Application
Flask API server implementing all required endpoints
"""

from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
import os
import json
from pathlib import Path

from dotenv import load_dotenv

from agent.triage_orchestrator import TriageOrchestrator
from config.team_info import TEAM_INFO, AGENT_INFO

# Load environment variables (override existing shell vars)
repo_root = Path(__file__).resolve().parent
dotenv_path = os.getenv("ENV_FILE", str(repo_root / ".env"))
load_dotenv(dotenv_path=dotenv_path, override=True)

app = Flask(__name__)
CORS(app)

# Initialize the triage agent
triage_agent = TriageOrchestrator()


@app.route('/api/team_info', methods=['GET'])
def get_team_info():
    """
    GET /api/team_info
    Returns student details with exact field order as required
    """
    # Force exact field order as required by assignment
    ordered_response = {
        "group_batch_order_number": TEAM_INFO["group_batch_order_number"],
        "team_name": TEAM_INFO["team_name"],
        "students": TEAM_INFO["students"]
    }
    return Response(
        json.dumps(ordered_response, ensure_ascii=False, indent=2),
        mimetype='application/json'
    )


@app.route('/api/agent_info', methods=['GET'])
def get_agent_info():
    """
    GET /api/agent_info
    Returns agent metadata, purpose, prompt templates and examples
    """
    # Force specific field order as required by teacher
    ordered_response = {
        "description": AGENT_INFO["description"],
        "purpose": AGENT_INFO["purpose"],
        "prompt_template": AGENT_INFO["prompt_template"],
        "prompt_examples": AGENT_INFO["prompt_examples"]
    }
    # Use Response with json.dumps to preserve dict order
    return Response(
        json.dumps(ordered_response, ensure_ascii=False, indent=2),
        mimetype='application/json'
    )


@app.route('/api/model_architecture', methods=['GET'])
def get_model_architecture():
    """
    GET /api/model_architecture
    Returns the architecture diagram as PNG
    """
    architecture_path = os.path.join(os.path.dirname(__file__), 'static', 'architecture.png')
    
    if not os.path.exists(architecture_path):
        return jsonify({"error": "Architecture diagram not found"}), 404
    
    return send_file(architecture_path, mimetype='image/png')


@app.route('/api/execute', methods=['POST'])
def execute_agent():
    """
    POST /api/execute
    Main entry point - executes the triage agent
    
    Input: {"prompt": "text"} OR {"chief_complaint": "...", "age": 72, "vitals": {...}}
    Output: {"status": "ok", "error": null, "response": "...", "steps": [...]}
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "error": "Missing request body",
                "response": None,
                "steps": []
            }), 400
        
        # Execute the triage agent with full request data
        # (orchestrator handles both text and structured input)
        result = triage_agent.execute(data)
        
        return jsonify({
            "status": "ok",
            "error": None,
            "response": result['response'],
            "steps": result['steps']
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "response": None,
            "steps": []
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


@app.route('/', methods=['GET'])
def index():
    """Serve the frontend"""
    return send_file('static/index.html')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
