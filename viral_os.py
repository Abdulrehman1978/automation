#!/usr/bin/env python3
"""
Viral OS — Main Entry Point
Usage:
  python viral_os.py start-dashboard   # Start the web UI
  python viral_os.py start-scheduler   # Start the APScheduler
  python viral_os.py run-pipeline      # Run the pipeline once
  python viral_os.py health-check      # Run system diagnostics
"""
import sys
import subprocess
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
        
    command = sys.argv[1]
    
    # Ensure we run from the project root
    root_dir = Path(__file__).parent.absolute()
    os.chdir(root_dir)
    
    if command == "start-dashboard":
        print("Starting Viral OS Dashboard...")
        subprocess.run([sys.executable, "src/dashboard/app.py"])
    elif command == "start-scheduler":
        print("Starting Viral OS Scheduler...")
        subprocess.run([sys.executable, "src/scheduler.py"])
    elif command == "run-pipeline":
        print("Running Pipeline...")
        subprocess.run([sys.executable, "src/main.py"])
    elif command == "health-check":
        print("Running Health Check...")
        subprocess.run([sys.executable, "src/health_check.py"])
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
