# Pipeline Cron Manager API

FastAPI server for managing the data generation pipeline daemon/cron. This API provides endpoints to start, stop, check status, and retrieve logs of the pipeline cron job.

## Features

- **Start Cron**: Start the pipeline daemon with custom time intervals (in seconds)
- **Stop Cron**: Stop the running daemon gracefully
- **Check Status**: Get the current status of the daemon (running/stopped, PID, etc.)
- **View Logs**: Retrieve full logs or tail recent logs
- **Clear Logs**: Clear the log file
- **Health Check**: Simple health check endpoint

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- `fastapi==0.104.1`
- `uvicorn==0.24.0`
- `pydantic==2.5.0`

## Running the API Server

### Method 1: Direct Execution
```bash
python3 cron_api.py
```

The server will start on `http://localhost:8000`

### Method 2: Using Uvicorn Directly
```bash
uvicorn cron_api:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Run in Background
```bash
nohup python3 cron_api.py > api_server.log 2>&1 &
```

## API Endpoints

### 1. Start Cron
**Endpoint**: `POST /api/cron/start`

**Description**: Start the pipeline cron daemon with specified interval

**Request Body**:
```json
{
  "interval_seconds": 60
}
```

**Parameters**:
- `interval_seconds` (integer, required): Interval in seconds (minimum: 10 seconds)
  - Examples: `60` (1 minute), `300` (5 minutes), `3600` (1 hour)

**Response**:
```json
{
  "success": true,
  "message": "Daemon started successfully with interval: 60 seconds (PID: 12345)",
  "timestamp": "2025-12-26T10:30:45.123456"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/cron/start" \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 60}'
```

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/cron/start",
    json={"interval_seconds": 60}
)
print(response.json())
```

---

### 2. Stop Cron
**Endpoint**: `POST /api/cron/stop`

**Description**: Stop the running pipeline cron daemon

**Request Body**: None

**Response**:
```json
{
  "success": true,
  "message": "Daemon stopped successfully",
  "timestamp": "2025-12-26T10:35:20.654321"
}
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/api/cron/stop"
```

**Python Example**:
```python
import requests

response = requests.post("http://localhost:8000/api/cron/stop")
print(response.json())
```

---

### 3. Get Cron Status
**Endpoint**: `GET /api/cron/status`

**Description**: Get the current status of the pipeline cron daemon

**Query Parameters**: None

**Response**:
```json
{
  "is_running": true,
  "pid": 12345,
  "message": "Daemon is running (PID: 12345)"
}
```

**cURL Example**:
```bash
curl "http://localhost:8000/api/cron/status"
```

**Python Example**:
```python
import requests

response = requests.get("http://localhost:8000/api/cron/status")
print(response.json())
```

---

### 4. Get Cron Logs
**Endpoint**: `GET /api/cron/logs`

**Description**: Get the pipeline cron execution logs

**Query Parameters**:
- `lines` (integer, optional): Number of recent lines to fetch

**Response**:
```json
{
  "logs": "[2025-12-26 10:30:45] ========== Pipeline execution started ==========\n[2025-12-26 10:30:46] [1/5] Running exotel_api.py...\n...",
  "line_count": 45
}
```

**cURL Examples**:
```bash
# Get all logs
curl "http://localhost:8000/api/cron/logs"

# Get last 20 lines
curl "http://localhost:8000/api/cron/logs?lines=20"
```

**Python Example**:
```python
import requests

# Get all logs
response = requests.get("http://localhost:8000/api/cron/logs")
print(response.json())

# Get last 50 lines
response = requests.get("http://localhost:8000/api/cron/logs?lines=50")
print(response.json())
```

---

### 5. Tail Cron Logs
**Endpoint**: `GET /api/cron/logs/tail`

**Description**: Get the last N lines of cron logs (plain text format)

**Query Parameters**:
- `lines` (integer, optional, default: 50): Number of lines to fetch from the end

**Response**: Plain text (last N lines)

**cURL Example**:
```bash
# Get last 50 lines (default)
curl "http://localhost:8000/api/cron/logs/tail"

# Get last 100 lines
curl "http://localhost:8000/api/cron/logs/tail?lines=100"
```

**Python Example**:
```python
import requests

response = requests.get("http://localhost:8000/api/cron/logs/tail?lines=50")
print(response.text)
```

---

### 6. Clear Cron Logs
**Endpoint**: `DELETE /api/cron/logs`

**Description**: Clear the pipeline cron execution logs

**Request Body**: None

**Response**:
```json
{
  "success": true,
  "message": "Logs cleared successfully",
  "timestamp": "2025-12-26T10:40:10.987654"
}
```

**cURL Example**:
```bash
curl -X DELETE "http://localhost:8000/api/cron/logs"
```

**Python Example**:
```python
import requests

response = requests.delete("http://localhost:8000/api/cron/logs")
print(response.json())
```

---

### 7. Health Check
**Endpoint**: `GET /health`

**Description**: Simple health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-26T10:45:30.111111"
}
```

**cURL Example**:
```bash
curl "http://localhost:8000/health"
```

---

## Interactive API Documentation

Once the server is running, you can access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Example Usage Scenarios

### Scenario 1: Start cron with 1-minute interval
```bash
curl -X POST "http://localhost:8000/api/cron/start" \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 60}'
```

### Scenario 2: Start cron with 5-minute interval
```bash
curl -X POST "http://localhost:8000/api/cron/start" \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 300}'
```

### Scenario 3: Monitor cron with status checks and log viewing
```bash
# Check status
curl "http://localhost:8000/api/cron/status"

# View last 50 lines of logs
curl "http://localhost:8000/api/cron/logs/tail?lines=50"

# View all logs with line count
curl "http://localhost:8000/api/cron/logs"
```

### Scenario 4: Stop and clear logs
```bash
# Stop the cron
curl -X POST "http://localhost:8000/api/cron/stop"

# Clear logs
curl -X DELETE "http://localhost:8000/api/cron/logs"
```

## Python Client Library

Here's a simple Python client to interact with the API:

```python
import requests
from typing import Optional

class CronAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def start(self, interval_seconds: int) -> dict:
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


# Usage Example
if __name__ == "__main__":
    client = CronAPIClient()
    
    # Start cron with 60 second interval
    print("Starting cron...")
    print(client.start(interval_seconds=60))
    
    # Check status
    print("\nChecking status...")
    print(client.status())
    
    # View logs
    print("\nViewing recent logs...")
    print(client.tail_logs(lines=20))
    
    # Stop cron
    print("\nStopping cron...")
    print(client.stop())
```

## Error Handling

The API returns appropriate HTTP status codes:

- **200 OK**: Request successful
- **400 Bad Request**: Invalid parameters (e.g., interval < 10 seconds)
- **500 Internal Server Error**: Server error during operation

Error response format:
```json
{
  "error": true,
  "detail": "Error message describing what went wrong",
  "timestamp": "2025-12-26T10:50:00.000000"
}
```

## Configuration

### Server Configuration

Edit the `if __name__ == "__main__":` section in `cron_api.py` to change:
- **host**: Default is `0.0.0.0` (accessible from any IP)
- **port**: Default is `8000`
- **log_level**: Default is `info` (can be `debug`, `warning`, `error`, `critical`)

### Interval Constraints

- **Minimum**: 10 seconds
- **Default**: 120 seconds (2 minutes)
- **Maximum**: No limit (but reasonable values are recommended)

## Integration with Existing Systems

### Running API and Daemon Together

You can run the API server and pipeline daemon simultaneously:

```bash
# Terminal 1: Start the API server
python3 cron_api.py

# Terminal 2: Or use the API to start the daemon
curl -X POST "http://localhost:8000/api/cron/start" \
  -H "Content-Type: application/json" \
  -d '{"interval_seconds": 300}'
```

### Systemd Service (Optional)

Create `/etc/systemd/system/pipeline-api.service`:
```ini
[Unit]
Description=Pipeline Cron Manager API
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 /path/to/cron_api.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:
```bash
sudo systemctl daemon-reload
sudo systemctl start pipeline-api
sudo systemctl enable pipeline-api
```

## Troubleshooting

### Port Already in Use
If port 8000 is already in use, change it:
```bash
python3 -m uvicorn cron_api:app --port 8001
```

### Daemon Not Starting
Check the logs:
```bash
curl "http://localhost:8000/api/cron/logs"
```

### Cannot Connect to API
Ensure:
1. The API server is running
2. The correct host and port are used
3. Firewall allows the connection

## Support

For issues or questions, check:
1. The error message in the API response
2. The logs via `/api/cron/logs` endpoint
3. The daemon logs in `pipeline_execution.log`
