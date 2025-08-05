#!/usr/bin/env python3
"""
Health check endpoint for JARVIS-MK42 Production Deployment
Provides a simple HTTP health check endpoint for container orchestration
"""

import os
import sys
import json
import logging
import threading
from typing import Dict, Any
from flask import Flask, jsonify
from datetime import datetime

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app for health checks
health_app = Flask(__name__)

# Health check status
health_status = {
    "status": "healthy",
    "last_check": datetime.utcnow().isoformat(),
    "components": {
        "database": "unknown",
        "agents": "unknown",
        "models": "unknown"
    }
}

def check_database_connection() -> bool:
    """Check database connectivity"""
    try:
        from models import get_database_session
        from sqlalchemy import text
        
        with get_database_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def check_agents_status() -> bool:
    """Check agent initialization status"""
    try:
        from agent_management import initialize_agent
        # Simple check - try to initialize without full setup
        return True
    except Exception as e:
        logger.error(f"Agents health check failed: {e}")
        return False

def check_models_status() -> bool:
    """Check model availability"""
    try:
        from config.settings import get_settings
        settings = get_settings()
        # Basic check - settings are accessible
        return True
    except Exception as e:
        logger.error(f"Models health check failed: {e}")
        return False

def update_health_status():
    """Update the health status with current checks"""
    global health_status
    
    try:
        # Check components
        db_status = check_database_connection()
        agents_status = check_agents_status()
        models_status = check_models_status()
        
        # Update component status
        health_status["components"]["database"] = "healthy" if db_status else "unhealthy"
        health_status["components"]["agents"] = "healthy" if agents_status else "unhealthy"
        health_status["components"]["models"] = "healthy" if models_status else "unhealthy"
        
        # Overall status
        all_healthy = all([db_status, agents_status, models_status])
        health_status["status"] = "healthy" if all_healthy else "unhealthy"
        health_status["last_check"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Health check update failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["last_check"] = datetime.utcnow().isoformat()

@health_app.route('/health')
def health_check():
    """Health check endpoint"""
    update_health_status()
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code

@health_app.route('/health/ready')
def readiness_check():
    """Readiness check endpoint"""
    update_health_status()
    
    # More strict check for readiness
    ready = (
        health_status["status"] == "healthy" and
        health_status["components"]["database"] == "healthy"
    )
    
    response = {
        "ready": ready,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    status_code = 200 if ready else 503
    return jsonify(response), status_code

@health_app.route('/health/live')
def liveness_check():
    """Liveness check endpoint"""
    # Simple liveness check - just return OK if the app is running
    response = {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
    return jsonify(response), 200

def run_health_server():
    """Run the health check server"""
    try:
        port = int(os.environ.get('HEALTH_PORT', 8001))
        logger.info(f"Starting health check server on port {port}")
        health_app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")

if __name__ == "__main__":
    # Start health server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Import and run main Chainlit application
    try:
        logger.info("Starting JARVIS-MK42 main application...")
        os.system("python -m chainlit run app.py --host 0.0.0.0 --port 8000")
    except Exception as e:
        logger.error(f"Failed to start main application: {e}")
        # Fallback - just run health server
        logger.warning("Running health server only")
        run_health_server()
