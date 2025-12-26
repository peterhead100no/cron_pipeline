#!/usr/bin/env python3
"""
Demo/Test script for the Pipeline Cron Manager API
Shows how to use the API endpoints
"""

import requests
import time
import json
from typing import Optional


class CronAPIClient:
    """Simple client for the Cron API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def start(self, interval_seconds: int = 60) -> dict:
        """Start the cron daemon"""
        response = requests.post(
            f"{self.base_url}/api/cron/start",
            json={"interval_seconds": interval_seconds}
        )
        response.raise_for_status()
        return response.json()
    
    def stop(self) -> dict:
        """Stop the cron daemon"""
        response = requests.post(f"{self.base_url}/api/cron/stop")
        response.raise_for_status()
        return response.json()
    
    def status(self) -> dict:
        """Get cron status"""
        response = requests.get(f"{self.base_url}/api/cron/status")
        response.raise_for_status()
        return response.json()
    
    def get_logs(self, lines: Optional[int] = None) -> dict:
        """Get cron logs"""
        params = {"lines": lines} if lines else {}
        response = requests.get(f"{self.base_url}/api/cron/logs", params=params)
        response.raise_for_status()
        return response.json()
    
    def tail_logs(self, lines: int = 50) -> str:
        """Get tail of cron logs"""
        response = requests.get(
            f"{self.base_url}/api/cron/logs/tail",
            params={"lines": lines}
        )
        response.raise_for_status()
        return response.text
    
    def clear_logs(self) -> dict:
        """Clear cron logs"""
        response = requests.delete(f"{self.base_url}/api/cron/logs")
        response.raise_for_status()
        return response.json()
    
    def health(self) -> dict:
        """Health check"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_response(data):
    """Pretty print response"""
    print(json.dumps(data, indent=2))


def demo():
    """Run demo of API endpoints"""
    
    client = CronAPIClient()
    
    # Test 1: Health Check
    print_section("Test 1: Health Check")
    try:
        result = client.health()
        print_response(result)
    except requests.exceptions.ConnectionError:
        print("✗ Error: Cannot connect to API server")
        print("  Make sure the server is running: python3 cron_api.py")
        return
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 2: Check Current Status
    print_section("Test 2: Check Current Status")
    try:
        result = client.status()
        print_response(result)
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 3: Start Cron with 60 second interval
    print_section("Test 3: Start Cron (60 second interval)")
    try:
        result = client.start(interval_seconds=60)
        print_response(result)
        print("\n✓ Cron started successfully!")
        time.sleep(1)  # Give it a moment to start
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 4: Verify Status After Start
    print_section("Test 4: Verify Status After Start")
    try:
        result = client.status()
        print_response(result)
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 5: View Logs
    print_section("Test 5: View Logs (Last 20 lines)")
    try:
        result = client.tail_logs(lines=20)
        if result.strip():
            print(result)
        else:
            print("(No logs yet)")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 6: View All Logs with Count
    print_section("Test 6: View All Logs with Line Count")
    try:
        result = client.get_logs()
        print(f"Total lines: {result['line_count']}")
        print("\nFirst 500 characters of logs:")
        print(result['logs'][:500])
        if len(result['logs']) > 500:
            print("\n... (truncated)")
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 7: Wait and check status
    print_section("Test 7: Waiting 5 seconds, then checking status")
    print("Waiting...")
    time.sleep(5)
    try:
        result = client.status()
        print_response(result)
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 8: Stop Cron
    print_section("Test 8: Stop Cron")
    try:
        result = client.stop()
        print_response(result)
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 9: Verify Status After Stop
    print_section("Test 9: Verify Status After Stop")
    try:
        result = client.status()
        print_response(result)
    except Exception as e:
        print(f"✗ Error: {e}")
        return
    
    # Test 10: Summary
    print_section("Demo Complete!")
    print("""
✓ All tests completed successfully!

API is working correctly. You can now:

1. Start the cron with custom intervals:
   curl -X POST "http://localhost:8000/api/cron/start" \\
     -H "Content-Type: application/json" \\
     -d '{"interval_seconds": 300}'

2. Check status anytime:
   curl "http://localhost:8000/api/cron/status"

3. View logs:
   curl "http://localhost:8000/api/cron/logs/tail?lines=50"

4. Stop the cron:
   curl -X POST "http://localhost:8000/api/cron/stop"

5. Access interactive API documentation:
   http://localhost:8000/docs
    """)


def interactive_mode():
    """Interactive command mode"""
    client = CronAPIClient()
    
    print("\n" + "=" * 70)
    print("  Pipeline Cron Manager - Interactive Mode")
    print("=" * 70)
    print("\nCommands:")
    print("  1. start <seconds>   - Start cron with interval in seconds")
    print("  2. stop              - Stop the cron daemon")
    print("  3. status            - Check cron status")
    print("  4. logs              - View all logs")
    print("  5. tail <lines>      - View last N lines of logs")
    print("  6. clear             - Clear logs")
    print("  7. health            - Health check")
    print("  8. demo              - Run demo")
    print("  9. help              - Show this help")
    print("  0. exit              - Exit program")
    print("=" * 70)
    
    while True:
        try:
            cmd = input("\n> ").strip().split()
            
            if not cmd:
                continue
            
            command = cmd[0].lower()
            
            if command == "1" or command == "start":
                interval = int(cmd[1]) if len(cmd) > 1 else 60
                result = client.start(interval_seconds=interval)
                print_response(result)
            
            elif command == "2" or command == "stop":
                result = client.stop()
                print_response(result)
            
            elif command == "3" or command == "status":
                result = client.status()
                print_response(result)
            
            elif command == "4" or command == "logs":
                result = client.get_logs()
                print(f"Total lines: {result['line_count']}\n")
                print(result['logs'][-1000:] if len(result['logs']) > 1000 else result['logs'])
            
            elif command == "5" or command == "tail":
                lines = int(cmd[1]) if len(cmd) > 1 else 50
                result = client.tail_logs(lines=lines)
                print(result)
            
            elif command == "6" or command == "clear":
                result = client.clear_logs()
                print_response(result)
            
            elif command == "7" or command == "health":
                result = client.health()
                print_response(result)
            
            elif command == "8" or command == "demo":
                demo()
            
            elif command == "9" or command == "help":
                print("""
Commands:
  1. start <seconds>   - Start cron with interval in seconds (default: 60)
  2. stop              - Stop the cron daemon
  3. status            - Check cron status
  4. logs              - View all logs
  5. tail <lines>      - View last N lines of logs (default: 50)
  6. clear             - Clear logs
  7. health            - Health check
  8. demo              - Run full demo
  9. help              - Show this help
  0. exit              - Exit program

Examples:
  start 300         - Start with 5-minute interval
  tail 100          - View last 100 lines
  start             - Start with 60-second interval (default)
                """)
            
            elif command == "0" or command == "exit":
                print("Goodbye!")
                break
            
            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands")
        
        except IndexError:
            print("Missing arguments. Type 'help' for usage.")
        except ValueError:
            print("Invalid numeric argument.")
        except requests.exceptions.ConnectionError:
            print("✗ Error: Cannot connect to API server at http://localhost:8000")
            print("  Make sure the server is running: python3 cron_api.py")
        except Exception as e:
            print(f"✗ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == "demo":
            demo()
        elif sys.argv[1].lower() == "interactive":
            interactive_mode()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("\nUsage:")
            print("  python3 api_client.py              # Interactive mode")
            print("  python3 api_client.py demo         # Run demo tests")
            print("  python3 api_client.py interactive  # Explicit interactive mode")
    else:
        interactive_mode()
