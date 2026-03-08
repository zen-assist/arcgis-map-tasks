#!/usr/bin/env python3
"""
arc_queue_worker.py — Background Task Queue Worker

Polls tasks.json and processes pending map generation tasks.

Usage:
    python arc_queue_worker.py              # run once
    python arc_queue_worker.py --loop       # poll continuously
    python arc_queue_worker.py --loop --interval 5  # poll every 5s
"""

import argparse
import logging
import time
import json
from pathlib import Path

from task_queue import TaskQueue

# Try ArcPy; fall back to simulation
try:
    import arcpy
    ARCPY_AVAILABLE = True
except ImportError:
    ARCPY_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def process_task(task: dict) -> dict:
    """Execute a single map task."""
    input_path  = task["input"]
    style       = task["style"]
    output_path = task["output"]
    fmt         = task.get("format", "png")

    if ARCPY_AVAILABLE:
        from arc_task import run_arcpy_task
        return run_arcpy_task(input_path, style, output_path, fmt)
    else:
        from arc_task import run_simulation_task
        return run_simulation_task(input_path, style, output_path, fmt)


def run_once(queue: TaskQueue) -> bool:
    """Process one pending task. Returns True if a task was processed."""
    task = queue.dequeue_next()
    if task is None:
        logger.debug("Queue empty — no tasks to process")
        return False

    logger.info(f"Processing task {task['id']}: {task['input']} → {task['output']}")
    try:
        result = process_task(task)
        queue.mark_done(task["id"], result.get("output"))
        logger.info(f"✅ Task {task['id']} completed: {result}")
        return True
    except Exception as e:
        error_msg = str(e)
        queue.mark_failed(task["id"], error_msg)
        logger.error(f"❌ Task {task['id']} failed: {error_msg}")
        return True


def main():
    parser = argparse.ArgumentParser(description="arcgis-map-tasks queue worker")
    parser.add_argument("--loop",     action="store_true", help="Poll continuously until interrupted")
    parser.add_argument("--interval", type=float, default=3.0, help="Poll interval in seconds (default: 3)")
    parser.add_argument("--status",   action="store_true", help="Print queue status and exit")
    args = parser.parse_args()

    queue = TaskQueue()

    if args.status:
        tasks = queue.list_all()
        if not tasks:
            print("Queue is empty.")
        else:
            for t in tasks:
                print(f"  [{t['status']:8s}] {t['id'][:8]}... | {t['input']} → {t['output']}")
        return

    engine = "ArcPy" if ARCPY_AVAILABLE else "Simulation"
    logger.info(f"Worker starting (engine: {engine})")

    if args.loop:
        logger.info(f"Polling every {args.interval}s — press Ctrl+C to stop")
        try:
            while True:
                run_once(queue)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Worker stopped.")
    else:
        run_once(queue)


if __name__ == "__main__":
    main()
