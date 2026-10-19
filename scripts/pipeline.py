# Version: 1.0.0
# Changelog: Google Flow Automated Batch Generation Pipeline Client (Connects to FlowKit Agent on 127.0.0.1:8100)

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional

class FlowPipelineClient:
    """
    Automated client for Google Flow video generation:
    1. Uploads keyframes to Google Flow Media Library via FlowKit Chrome Bridge
    2. Dispatches 10-second Omni 1.1 Flash generation jobs with Start/End frame daisy-chaining
    3. Monitors progress and downloads completed MP4 video clips
    """

    def __init__(self, agent_url: str = "http://127.0.0.1:8100", project_id: Optional[str] = None):
        self.agent_url = agent_url.rstrip("/")
        self.project_id = project_id or os.getenv("FLOW_PROJECT_ID")

    def check_health(self) -> bool:
        """Verify that the FlowKit agent and Chrome bridge are alive."""
        try:
            resp = requests.get(f"{self.agent_url}/health", timeout=5)
            data = resp.json()
            print(f"[FlowKit] Agent Status: {data.get('status')}, Extension Connected: {data.get('extension_connected', True)}")
            return resp.status_code == 200
        except Exception as e:
            print(f"[FlowKit Error] Cannot connect to FlowKit agent at {self.agent_url}: {e}")
            print("Please ensure `python -m agent.main` is running!")
            return False

    def upload_keyframe(self, file_path: str) -> Optional[str]:
        """Upload a local image file to Google Flow Media Library and return media_id."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Keyframe not found: {file_path}")

        print(f"[Upload] Uploading keyframe: {path.name}...")
        try:
            with open(path, "rb") as f:
                files = {"file": (path.name, f, "image/jpeg")}
                data = {"project_id": self.project_id} if self.project_id else {}
                resp = requests.post(f"{self.agent_url}/api/upload", files=files, data=data, timeout=60)
            
            if resp.status_code == 200:
                res = resp.json()
                media_id = res.get("media_id") or res.get("id")
                print(f"[Upload OK] {path.name} -> media_id: {media_id}")
                return media_id
            else:
                print(f"[Upload Failed] HTTP {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"[Upload Error] {e}")
            return None

    def generate_shot(self, prompt: str, start_media_id: Optional[str] = None, end_media_id: Optional[str] = None, duration: float = 10.0) -> Optional[str]:
        """Dispatch a single shot generation request."""
        payload = {
            "project_id": self.project_id,
            "prompt": prompt,
            "duration": duration,
            "start_media_id": start_media_id,
            "end_media_id": end_media_id,
            "model": "omni-1.1-flash"
        }
        try:
            resp = requests.post(f"{self.agent_url}/api/generate", json=payload, timeout=30)
            if resp.status_code in (200, 201, 202):
                job = resp.json()
                job_id = job.get("job_id") or job.get("id")
                print(f"[Generate] Job dispatched: {job_id}")
                return job_id
            else:
                print(f"[Generate Failed] HTTP {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            print(f"[Generate Error] {e}")
            return None

    def wait_for_job(self, job_id: str, poll_interval: int = 5, timeout: int = 300) -> Optional[str]:
        """Wait for video generation job to complete and return video URL."""
        start_time = time.time()
        print(f"[Polling] Waiting for job {job_id}...")
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.agent_url}/api/jobs/{job_id}", timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status")
                    if status in ("completed", "done", "success"):
                        video_url = data.get("video_url") or data.get("url")
                        print(f"[Job Complete] {job_id} -> {video_url}")
                        return video_url
                    elif status in ("failed", "error"):
                        print(f"[Job Failed] {job_id}: {data.get('error')}")
                        return None
                    else:
                        print(f"  ...status: {status} ({int(time.time() - start_time)}s)")
            except Exception as e:
                print(f"[Poll Error] {e}")
            time.sleep(poll_interval)
        print(f"[Timeout] Job {job_id} exceeded {timeout}s.")
        return None

if __name__ == "__main__":
    client = FlowPipelineClient()
    if client.check_health():
        print("FlowKit agent is ready for batch processing.")
    else:
        print("FlowKit agent not detected.")
