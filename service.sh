#!/bin/bash

# Set variables
PROJECT_DIR="/home/n8n/jarvis-mk42"
APP_NAME="app.py"
HOST="jarvis.omni-corp.tech"
PORT="8003"
ROOT_PATH="/jarvis-mk42"
LOG_FILE="chainlit.log"
PID_FILE="chainlit.pid"

# Function to find and kill existing Chainlit processes for this specific app
kill_existing_process() {
    # Find processes matching the specific criteria
    # Use multiple filters to ensure we're killing the right process
    PIDS=$(ps aux | grep -E "chainlit run.*--port ${PORT}" | grep -v grep | awk '{print $2}')
    
    if [ ! -z "$PIDS" ]; then
        echo "Killing existing Chainlit processes for ${APP_NAME}"
        for PID in $PIDS; do
            kill -9 $PID
            echo "Killed process with PID $PID"
        done
        
        # Wait a moment to ensure processes are terminated
        sleep 2
    else
	echo "No previous process was found"
    fi
}

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Set SSL environment variables
export CHAINLIT_SSL_KEY=/home/n8n/omni-corp_key.key
export CHAINLIT_SSL_CERT=/home/n8n/omni-corp_cert_full.cer

# Kill any existing processes first
kill_existing_process

# Start Chainlit
echo "Starting Chainlit for ${APP_NAME}"
chainlit run --host "$HOST" --port "$PORT" --root-path "$ROOT_PATH" "$APP_NAME" > "$LOG_FILE" 2>&1 &

# Optional: Verify the process started
sleep 2
STARTED_PID=$(ps aux | grep -E "chainlit run.*--port ${PORT}" | grep -v grep | awk '{print $2}')
if [ ! -z "$STARTED_PID" ]; then
    echo "Chainlit started successfully with PID $STARTED_PID"
    echo $STARTED_PID > $PID_FILE
else
    echo "Failed to start Chainlit"
    exit 1
fi

