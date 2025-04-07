# config.py
import os

SUPERVISOR_PROMPT_NAME = "supervisor"
JARVIS_NAME = "Jarvis_MKIII"
RECURSION_LIMIT = 250

# Audio settings (example)
MPV_INSTALLED = os.environ.get("MPV_INSTALLED", "False").lower() == "true"
