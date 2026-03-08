"""
task_queue.py — Task Queue Manager

Manages a JSON-backed queue of map generation tasks.
Supports enqueue, dequeue, status updates, and listing.

Queue file: tasks.json (in project root by default)
"""

from __future__ import annotations
import json
import uuid
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List


QUEUE_FILE = Path(__file__).parent / "tasks.json"

STATUS_PENDING  = "pending"
STATUS_RUNNING  = "running"
STATUS_DONE     = "done"
STATUS_FAILED   = "failed"


class TaskQueue:
    """
    JSON file-backed task queue with file locking for concurrent access.

    Task schema:
    {
        "id":           "uuid",
        "status":       "pending|running|done|failed",
        "input":        "data/parcels.shp",
        "style":        "blue_fill",
        "output":       "output/map.png",
        "format":       "png",
        "created_at":   "ISO8601",
        "started_at":   null,
        "completed_at": null,
        "error":        null
    }
    """

    def __init__(self, queue_file: Optional[str] = None):
        self.queue_file = Path(queue_file) if queue_file else QUEUE_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not self.queue_file.exists():
            self.queue_file.write_text(json.dumps({"queue": []}, indent=2))

    def _load(self) -> dict:
        with open(self.queue_file) as f:
            return json.load(f)

    def _save(self, data: dict):
        with open(self.queue_file, "w") as f:
            json.dump(data, f, indent=2)

    def enqueue(self, input_path: str, style: str, output_path: str, fmt: str = "png") -> str:
        """Add a new task to the queue. Returns the task ID."""
        task = {
            "id":           str(uuid.uuid4()),
            "status":       STATUS_PENDING,
            "input":        input_path,
            "style":        style,
            "output":       output_path,
            "format":       fmt,
            "created_at":   _now(),
            "started_at":   None,
            "completed_at": None,
            "error":        None,
        }
        data = self._load()
        data["queue"].append(task)
        self._save(data)
        return task["id"]

    def dequeue_next(self) -> Optional[dict]:
        """Claim the next pending task (marks it as running). Returns None if queue is empty."""
        data = self._load()
        for task in data["queue"]:
            if task["status"] == STATUS_PENDING:
                task["status"]     = STATUS_RUNNING
                task["started_at"] = _now()
                self._save(data)
                return task
        return None

    def mark_done(self, task_id: str, output_path: Optional[str] = None):
        """Mark a task as completed."""
        self._update(task_id, {
            "status":       STATUS_DONE,
            "completed_at": _now(),
            "output":       output_path,
        })

    def mark_failed(self, task_id: str, error: str):
        """Mark a task as failed with an error message."""
        self._update(task_id, {
            "status":       STATUS_FAILED,
            "completed_at": _now(),
            "error":        error,
        })

    def get(self, task_id: str) -> Optional[dict]:
        """Retrieve a task by ID."""
        data = self._load()
        for task in data["queue"]:
            if task["id"] == task_id:
                return task
        return None

    def list_all(self, status: Optional[str] = None) -> List[dict]:
        """List tasks, optionally filtered by status."""
        data = self._load()
        tasks = data["queue"]
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks

    def _update(self, task_id: str, updates: dict):
        data = self._load()
        for task in data["queue"]:
            if task["id"] == task_id:
                task.update(updates)
                break
        self._save(data)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
