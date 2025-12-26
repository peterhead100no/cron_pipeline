#!/usr/bin/env python3
"""
Background daemon to run the pipeline every N minutes.
This is more reliable than cron on macOS.
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime

class PipelineDaemon:
    def __init__(self, interval_minutes=2):
        self.script_dir = Path(__file__).parent.absolute()
        self.interval = interval_minutes * 60  # Convert to seconds
        self.log_file = self.script_dir / "pipeline_execution.log"
        self.running = True
        self.pid_file = self.script_dir / "pipeline_daemon.pid"
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Daemon shutting down...")
        self.running = False
        if self.pid_file.exists():
            self.pid_file.unlink()
        sys.exit(0)
    
    def log(self, message):
        """Log message to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + "\n")
        
        print(log_message)
    
    def save_pid(self):
        """Save daemon PID to file"""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def run_pipeline(self):
        """Run the pipeline scripts"""
        scripts = [
            "exotel_api.py",
            "import_exotel_data.py",
            "get_recording.py",
            "audio_to_text.py",
            "descrption_generation_2.py"
        ]
        
        self.log("========== Pipeline execution started ==========")
        
        for i, script in enumerate(scripts, 1):
            script_path = self.script_dir / script
            
            if not script_path.exists():
                self.log(f"[{i}/{len(scripts)}] ERROR: {script} not found!")
                continue
            
            self.log(f"[{i}/{len(scripts)}] Running {script}...")
            
            try:
                result = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(self.script_dir),
                    capture_output=True,
                    timeout=300,  # 5 minute timeout
                    text=True
                )
                
                if result.returncode == 0:
                    self.log(f"[{i}/{len(scripts)}] ✓ {script} completed successfully")
                else:
                    self.log(f"[{i}/{len(scripts)}] ✗ {script} failed with exit code {result.returncode}")
                    if result.stderr:
                        self.log(f"  Error: {result.stderr[:200]}")
            
            except subprocess.TimeoutExpired:
                self.log(f"[{i}/{len(scripts)}] ✗ {script} timed out after 5 minutes")
            except Exception as e:
                self.log(f"[{i}/{len(scripts)}] ✗ Error running {script}: {e}")
        
        self.log("========== Pipeline execution completed ==========\n")
    
    def start(self):
        """Start the daemon"""
        self.save_pid()
        self.log(f"Pipeline daemon started (PID: {os.getpid()}, Interval: {self.interval}s)")
        self.log(f"Logs: {self.log_file}\n")
        
        try:
            while self.running:
                self.run_pipeline()
                
                # Sleep for the specified interval
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            self.signal_handler(None, None)
    
    @staticmethod
    def is_running():
        """Check if daemon is already running"""
        pid_file = Path(__file__).parent.absolute() / "pipeline_daemon.pid"
        
        if not pid_file.exists():
            return False
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, OSError):
            pid_file.unlink() if pid_file.exists() else None
            return False
    
    @staticmethod
    def stop():
        """Stop the daemon"""
        pid_file = Path(__file__).parent.absolute() / "pipeline_daemon.pid"
        
        if not pid_file.exists():
            print("Daemon is not running")
            return False
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read())
            
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            
            # Verify it's stopped
            try:
                os.kill(pid, 0)
                print(f"✗ Failed to stop daemon (PID: {pid})")
                return False
            except OSError:
                print(f"✓ Daemon stopped (PID: {pid})")
                pid_file.unlink()
                return True
        
        except Exception as e:
            print(f"✗ Error stopping daemon: {e}")
            return False


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        interval = 2  # Default 2 minutes
        
        if len(sys.argv) > 2:
            try:
                interval = int(sys.argv[2])
            except ValueError:
                pass
        
        if command == 'start':
            if PipelineDaemon.is_running():
                print("✓ Daemon is already running")
                return
            
            daemon = PipelineDaemon(interval_minutes=interval)
            daemon.start()
        
        elif command == 'stop':
            PipelineDaemon.stop()
        
        elif command == 'status':
            if PipelineDaemon.is_running():
                pid_file = Path(__file__).parent.absolute() / "pipeline_daemon.pid"
                with open(pid_file, 'r') as f:
                    pid = int(f.read())
                print(f"✓ Daemon is running (PID: {pid})")
            else:
                print("✗ Daemon is not running")
        
        elif command == 'logs':
            log_file = Path(__file__).parent.absolute() / "pipeline_execution.log"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    print(f.read())
            else:
                print(f"Log file not found: {log_file}")
        
        elif command == 'help':
            print("""
Usage: python3 run_pipeline_daemon.py [command] [interval]

Commands:
  start [interval]  Start daemon (interval in minutes, default: 2)
  stop              Stop the daemon
  status            Check daemon status
  logs              Show execution logs
  help              Show this help message

Examples:
  python3 run_pipeline_daemon.py start           # Start with 2 min interval
  python3 run_pipeline_daemon.py start 5         # Start with 5 min interval
  python3 run_pipeline_daemon.py stop            # Stop daemon
  python3 run_pipeline_daemon.py status          # Check if running
  python3 run_pipeline_daemon.py logs            # View logs
""")
        else:
            print(f"Unknown command: {command}")
            print("Use 'python3 run_pipeline_daemon.py help' for usage")
    else:
        # Default: start with 2 minute interval
        if PipelineDaemon.is_running():
            print("✓ Daemon is already running")
            return
        
        daemon = PipelineDaemon(interval_minutes=2)
        daemon.start()


if __name__ == "__main__":
    main()
