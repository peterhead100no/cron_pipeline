#!/usr/bin/env python3
"""
Cron Job Setup Script for Data Generation Pipeline
This script sets up a cron job to run the data generation pipeline every hour.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class CronSetup:
    def __init__(self):
        self.script_dir = Path(__file__).parent.absolute()
        self.pipeline_script = self.script_dir / "run_pipeline.sh"
        self.log_file = self.script_dir / "pipeline_execution.log"
        
    def create_pipeline_script(self):
        """Create the main pipeline execution script"""
        pipeline_content = """#!/bin/bash

# Pipeline script to run all data generation scripts sequentially
# This script runs every hour via cron

# Set the working directory
cd "$(dirname "$0")" || exit 1

# Get the Python executable path
PYTHON_EXEC=$(which python3)

# Log file for tracking execution
LOG_FILE="pipeline_execution.log"

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start logging
log_message "========== Pipeline execution started =========="

# Array of scripts to run in sequence
scripts=(
    "exotel_api.py"
    "import_exotel_data.py"
    "get_recording.py"
    "audio_to_text.py"
    "descrption_generation_2.py"
)

# Counter for tracking which script is running
script_count=0
total_scripts=${#scripts[@]}

# Run each script in sequence
for script in "${scripts[@]}"; do
    script_count=$((script_count + 1))
    log_message "[$script_count/$total_scripts] Running $script..."
    
    # Check if script exists
    if [ ! -f "$script" ]; then
        log_message "ERROR: $script not found!"
        continue
    fi
    
    # Run the script and capture exit code
    $PYTHON_EXEC "$script"
    exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_message "[$script_count/$total_scripts] ✓ $script completed successfully"
    else
        log_message "[$script_count/$total_scripts] ✗ $script failed with exit code $exit_code"
    fi
    
    # Optional: Add a small delay between scripts (in seconds)
    # sleep 5
done

log_message "========== Pipeline execution completed =========="
log_message ""
"""
        
        try:
            with open(self.pipeline_script, 'w') as f:
                f.write(pipeline_content)
            os.chmod(self.pipeline_script, 0o755)
            print(f"✓ Created pipeline script: {self.pipeline_script}")
            return True
        except Exception as e:
            print(f"✗ Error creating pipeline script: {e}")
            return False
    
    def check_pipeline_script_exists(self):
        """Check if pipeline script exists"""
        return self.pipeline_script.exists()
    
    def get_current_crontab(self):
        """Get the current crontab entries"""
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception as e:
            print(f"Error reading crontab: {e}")
            return None
    
    def get_cron_entry(self):
        """Generate the cron job entry"""
        # Cron format: minute hour day month day_of_week command
        # */10 * * * * means every 10 minutes
        return f"*/2 * * * * {self.pipeline_script} >> {self.log_file} 2>&1"
    
    def cron_job_exists(self):
        """Check if the cron job already exists"""
        current_crontab = self.get_current_crontab()
        if current_crontab is None:
            return False
        return str(self.pipeline_script) in current_crontab
    
    def add_cron_job(self):
        """Add the cron job to crontab"""
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            # Add new cron job
            new_cron_entry = self.get_cron_entry()
            new_crontab = current_crontab + new_cron_entry + "\n"
            
            # Write to crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
            
            if process.returncode == 0:
                print(f"✓ Cron job added successfully!")
                return True
            else:
                print(f"✗ Failed to add cron job")
                return False
        except Exception as e:
            print(f"✗ Error adding cron job: {e}")
            return False
    
    def remove_cron_job(self):
        """Remove the cron job from crontab"""
        try:
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode != 0:
                print("No crontab entries found")
                return False
            
            current_crontab = result.stdout
            pipeline_path = str(self.pipeline_script)
            
            # Remove the cron job
            new_crontab = "\n".join([
                line for line in current_crontab.split("\n")
                if pipeline_path not in line
            ])
            
            # Write to crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
            
            if process.returncode == 0:
                print(f"✓ Cron job removed successfully!")
                return True
            else:
                print(f"✗ Failed to remove cron job")
                return False
        except Exception as e:
            print(f"✗ Error removing cron job: {e}")
            return False
    
    def display_info(self):
        """Display current cron setup information"""
        print("\n" + "="*60)
        print("DATA GENERATION PIPELINE - CRON SETUP")
        print("="*60)
        print(f"\nScript Directory: {self.script_dir}")
        print(f"Pipeline Script: {self.pipeline_script}")
        print(f"Log File: {self.log_file}")
        print(f"\nCron Job Entry:")
        print(f"  {self.get_cron_entry()}")
        print(f"\nSchedule: Every 10 minutes")
        print(f"          (runs 144 times per day)")
        
        # Show current crontab
        current_crontab = self.get_current_crontab()
        if current_crontab:
            print(f"\nCurrent Crontab Entries:")
            print("-"*60)
            print(current_crontab)
        else:
            print(f"\nNo crontab entries found (first time setup)")
        
        # Check if job exists
        if self.cron_job_exists():
            print(f"\n✓ Cron job is ACTIVE")
        else:
            print(f"\n✗ Cron job is NOT active")
        print("="*60 + "\n")
    
    def run_pipeline_now(self):
        """Run the pipeline scripts immediately"""
        print("\nStep 4: Running pipeline scripts now...")
        print("-"*60)
        try:
            result = subprocess.run([str(self.pipeline_script)], capture_output=False, text=True)
            if result.returncode == 0:
                print("-"*60)
                print("✓ Pipeline execution completed successfully!")
                return True
            else:
                print("-"*60)
                print(f"⚠ Pipeline completed with exit code: {result.returncode}")
                return True  # Still return True as cron is set up
        except Exception as e:
            print(f"✗ Error running pipeline: {e}")
            return False
    
    def setup(self):
        """Setup the cron job"""
        print("\n" + "="*60)
        print("DATA GENERATION PIPELINE - CRON SETUP WIZARD")
        print("="*60 + "\n")
        
        # Step 1: Create pipeline script
        print("Step 1: Creating pipeline script...")
        if self.check_pipeline_script_exists():
            print(f"✓ Pipeline script already exists: {self.pipeline_script}")
        else:
            if not self.create_pipeline_script():
                print("✗ Failed to create pipeline script")
                return False
        
        # Step 2: Display information
        print("\nStep 2: Current setup information:")
        self.display_info()
        
        # Step 3: Check if already exists
        if self.cron_job_exists():
            print("⚠ Cron job already exists!")
            response = input("Do you want to replace it? (y/n): ").strip().lower()
            if response != 'y':
                print("Setup cancelled.")
                return False
            else:
                if not self.remove_cron_job():
                    return False
        
        # Step 4: Add cron job
        print("\nStep 3: Adding cron job...")
        if self.add_cron_job():
            print("\nStep 5: Verifying setup...")
            if self.cron_job_exists():
                print("✓ Cron job verified and active!")
                print("\nYour pipeline will run automatically every hour.")
                print(f"Check logs at: {self.log_file}")
                
                # Step 5: Run pipeline now
                print("\n" + "="*60)
                response = input("Do you want to run the pipeline now? (y/n): ").strip().lower()
                if response == 'y':
                    self.run_pipeline_now()
                else:
                    print("Pipeline will start on the next scheduled time.")
                
                print("="*60)
                return True
            else:
                print("✗ Verification failed")
                return False
        else:
            return False


def main():
    """Main function"""
    cron = CronSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'status':
            cron.display_info()
        elif command == 'start':
            if cron.cron_job_exists():
                print("✓ Cron job is already active")
            else:
                cron.setup()
        elif command == 'stop':
            cron.remove_cron_job()
        elif command == 'logs':
            if cron.log_file.exists():
                with open(cron.log_file, 'r') as f:
                    print(f.read())
            else:
                print(f"Log file not found: {cron.log_file}")
        elif command == 'logs-follow':
            print(f"Following logs... (Ctrl+C to exit)")
            os.system(f"tail -f '{cron.log_file}'")
        elif command == 'help':
            print(f"""
Usage: python3 setup_cron.py [command]

Commands:
  (no argument)     Run interactive setup wizard (sets up cron + runs pipeline)
  start             Start the cron job
  stop              Stop/remove the cron job
  status            Show current cron job status
  logs              Display execution logs
  logs-follow       Follow logs in real-time
  help              Show this help message

Examples:
  python3 setup_cron.py                # Interactive setup with immediate pipeline run
  python3 setup_cron.py start          # Start cron job
  python3 setup_cron.py status         # Check status
  python3 setup_cron.py logs           # View logs
  python3 setup_cron.py logs-follow    # Follow logs

Note: The interactive setup wizard will ask if you want to run the pipeline immediately
after setting up the cron job.
""")
        else:
            print(f"Unknown command: {command}")
            print("Use 'python3 setup_cron.py help' for usage information")
    else:
        # Interactive setup
        success = cron.setup()
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
