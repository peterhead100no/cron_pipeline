#!/usr/bin/env python3
"""
FastAPI server for managing the pipeline daemon/cron
Provides endpoints to start, stop, check status, and get logs of the cron job
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
import os
import subprocess
import sys
import signal
import time
from datetime import datetime
from typing import Optional

# Import the PipelineDaemon class
sys.path.insert(0, str(Path(__file__).parent.absolute()))
from run_pipeline_daemon import PipelineDaemon

# Create FastAPI app
app = FastAPI(
    title="Pipeline Cron Manager API",
    description="API to manage the data generation pipeline cron/daemon",
    version="1.0.0"
)

# ==================== Models ====================

class StartCronRequest(BaseModel):
    """Request model for starting cron"""
    interval_seconds: int = 120
    
    class Config:
        json_schema_extra = {
            "example": {
                "interval_seconds": 60
            }
        }


class CronStatusResponse(BaseModel):
    """Response model for cron status"""
    is_running: bool
    pid: Optional[int] = None
    message: str


class CronLogsResponse(BaseModel):
    """Response model for cron logs"""
    logs: str
    line_count: int


class CronActionResponse(BaseModel):
    """Response model for cron actions"""
    success: bool
    message: str
    timestamp: str


# ==================== Endpoints ====================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint - returns API information"""
    return {
        "name": "Pipeline Cron Manager API",
        "version": "1.0.0",
        "description": "Manage the data generation pipeline daemon/cron",
        "endpoints": {
            "POST /api/cron/start": "Start the cron daemon with specified interval",
            "POST /api/cron/stop": "Stop the running cron daemon",
            "GET /api/cron/status": "Get the status of the cron daemon",
            "GET /api/cron/logs": "Get the cron execution logs",
            "GET /docs": "Interactive API documentation"
        }
    }


@app.post("/api/cron/start", response_model=CronActionResponse, tags=["Cron Management"])
async def start_cron(request: StartCronRequest):
    """
    Start the pipeline cron daemon with specified interval
    
    Args:
        interval_seconds: Interval in seconds (e.g., 60, 300, 3600)
    
    Returns:
        Status of the operation
    """
    try:
        # Validate interval
        if request.interval_seconds < 10:
            raise HTTPException(status_code=400, detail="Interval must be at least 10 seconds")
        
        # Check if already running
        if PipelineDaemon.is_running():
            return CronActionResponse(
                success=False,
                message="Daemon is already running. Stop it first with /api/cron/stop",
                timestamp=datetime.now().isoformat()
            )
        
        # Convert seconds to minutes for PipelineDaemon
        interval_minutes = max(1, request.interval_seconds // 60)
        
        # Start the daemon in background
        script_dir = Path(__file__).parent.absolute()
        
        # Use nohup to run in background
        result = subprocess.Popen(
            [sys.executable, str(script_dir / "run_pipeline_daemon.py"), "start", str(interval_minutes)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # This creates a new process group on macOS
            cwd=str(script_dir)
        )
        
        # Give it a moment to start
        time.sleep(1)
        
        # Verify it started
        if PipelineDaemon.is_running():
            pid_file = script_dir / "pipeline_daemon.pid"
            pid = None
            if pid_file.exists():
                with open(pid_file, 'r') as f:
                    pid = int(f.read())
            
            return CronActionResponse(
                success=True,
                message=f"Daemon started successfully with interval: {request.interval_seconds} seconds (PID: {pid})",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start daemon - process did not start correctly")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting cron: {str(e)}")


@app.post("/api/cron/stop", response_model=CronActionResponse, tags=["Cron Management"])
async def stop_cron():
    """
    Stop the running pipeline cron daemon
    
    Returns:
        Status of the operation
    """
    try:
        if not PipelineDaemon.is_running():
            return CronActionResponse(
                success=False,
                message="Daemon is not running",
                timestamp=datetime.now().isoformat()
            )
        
        # Stop the daemon
        success = PipelineDaemon.stop()
        
        if success:
            return CronActionResponse(
                success=True,
                message="Daemon stopped successfully",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to stop daemon")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping cron: {str(e)}")


@app.get("/api/cron/status", response_model=CronStatusResponse, tags=["Cron Management"])
async def get_cron_status():
    """
    Get the current status of the pipeline cron daemon
    
    Returns:
        Current status including running state and PID
    """
    try:
        is_running = PipelineDaemon.is_running()
        pid = None
        
        if is_running:
            script_dir = Path(__file__).parent.absolute()
            pid_file = script_dir / "pipeline_daemon.pid"
            
            if pid_file.exists():
                with open(pid_file, 'r') as f:
                    try:
                        pid = int(f.read())
                    except ValueError:
                        pass
            
            message = f"Daemon is running (PID: {pid})"
        else:
            message = "Daemon is not running"
        
        return CronStatusResponse(
            is_running=is_running,
            pid=pid,
            message=message
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")


@app.get("/api/cron/logs", response_model=CronLogsResponse, tags=["Cron Management"])
async def get_cron_logs(lines: Optional[int] = None):
    """
    Get the pipeline cron execution logs
    
    Query Parameters:
        lines: Optional number of recent lines to fetch (if not specified, returns all)
    
    Returns:
        Logs content and line count
    """
    try:
        script_dir = Path(__file__).parent.absolute()
        log_file = script_dir / "pipeline_execution.log"
        
        if not log_file.exists():
            return CronLogsResponse(
                logs="No logs available yet",
                line_count=0
            )
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_logs = f.read()
        
        # Get line count
        total_lines = len(all_logs.split('\n'))
        
        # Return last N lines if specified
        if lines and lines > 0:
            log_lines = all_logs.split('\n')
            recent_logs = '\n'.join(log_lines[-lines:])
            return CronLogsResponse(
                logs=recent_logs,
                line_count=len(recent_logs.split('\n'))
            )
        
        return CronLogsResponse(
            logs=all_logs,
            line_count=total_lines
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@app.delete("/api/cron/logs", tags=["Cron Management"])
async def clear_cron_logs():
    """
    Clear the pipeline cron execution logs
    
    Returns:
        Status of the operation
    """
    try:
        script_dir = Path(__file__).parent.absolute()
        log_file = script_dir / "pipeline_execution.log"
        
        if log_file.exists():
            log_file.unlink()
            return CronActionResponse(
                success=True,
                message="Logs cleared successfully",
                timestamp=datetime.now().isoformat()
            )
        else:
            return CronActionResponse(
                success=False,
                message="No log file to clear",
                timestamp=datetime.now().isoformat()
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing logs: {str(e)}")


@app.get("/api/cron/logs/tail", tags=["Cron Management"])
async def tail_cron_logs(lines: int = 50):
    """
    Get the last N lines of cron logs (tail functionality)
    
    Query Parameters:
        lines: Number of lines to fetch from the end (default: 50)
    
    Returns:
        Recent logs in plain text format
    """
    try:
        script_dir = Path(__file__).parent.absolute()
        log_file = script_dir / "pipeline_execution.log"
        
        if not log_file.exists():
            return "No logs available yet"
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_logs = f.read()
        
        log_lines = all_logs.split('\n')
        recent_logs = '\n'.join(log_lines[-lines:])
        
        return recent_logs
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


# ==================== Health Check ====================

@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "detail": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
