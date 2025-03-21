import csv
import json
import shlex
import argparse
import pandas as pd
from pathlib import Path
import subprocess
import sys
import os


JOB_STATUSES = ["ready", "running", "done", "failed"]

# Configuration
class Config:
    """Centralized configuration settings for gitrunner."""
    JOBS_QUEUE_FILE = os.environ.get('JOBS_QUEUE_FILE', 'queue.csv')
    SLEEP_TIME = int(os.environ.get('SLEEP_TIME', 2))  # seconds between job checks
    MAX_ATTEMPTS = int(os.environ.get('MAX_ATTEMPTS', 3))
    GIT_USER_EMAIL = os.environ.get('GIT_USER_EMAIL', '<>')
    GIT_USER_NAME = os.environ.get('GIT_USER_NAME', 'eval-bot')
    RESULTS_DIR = os.environ.get('RESULTS_DIR', 'results')
    MAX_JOB_ATTEMPTS = int(os.environ.get('MAX_JOB_ATTEMPTS', 3))
    
    @classmethod
    def update_from_args(cls, args):
        """Update configuration from command-line arguments."""
        if args.results_dir:
            cls.RESULTS_DIR = args.results_dir
        if args.max_job_attempts:
            cls.MAX_JOB_ATTEMPTS = args.max_job_attempts
        if args.queue_file:
            cls.JOBS_QUEUE_FILE = args.queue_file
        if args.sleep_time:
            cls.SLEEP_TIME = args.sleep_time

def ensure_queue_exists(queue_path=None):
    """Ensure the queue file exists with headers."""
    if queue_path is None:
        queue_path = Config.JOBS_QUEUE_FILE
        
    if not Path(queue_path).exists():
        with open(queue_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["script", "args", "kwargs", "status"])
            writer.writeheader()
        return True
    return False

def add_job_to_queue(command_string, queue_path=None):
    """Add a job to the queue file from a command string."""
    if queue_path is None:
        queue_path = Config.JOBS_QUEUE_FILE
        
    # Parse the command using shell-like splitting
    tokens = shlex.split(command_string)
    
    # Strip off the "python" if it's the first token
    if tokens[0] == "python":
        tokens = tokens[1:]
    
    script = tokens[0]
    # Remove .py extension if present for consistency
    if script.endswith(".py"):
        script = script[:-3]
    
    args = []
    kwargs = {}

    # Parse arguments
    i = 1
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--"):
            # Handle --key=value format
            if "=" in token:
                key, value = token[2:].split("=", 1)
                kwargs[key] = value
            # Handle --key value format
            elif i + 1 < len(tokens):
                key = token[2:]
                value = tokens[i + 1]
                kwargs[key] = value
                i += 1
        else:
            args.append(token)
        i += 1

    # Prepare CSV-safe values
    row = {
        "script": script,
        "args": json.dumps(args),
        "kwargs": json.dumps(kwargs),
        "status": "ready"
    }

    # Ensure queue file exists
    ensure_queue_exists(queue_path)
    
    try:
        with open(queue_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["script", "args", "kwargs", "status"])
            writer.writerow(row)
    except Exception as e:
        print(f"❌ Error adding job to queue: {e}")
        raise e
    
    print(f"✅ Added job to queue: {script} {args} {kwargs}")
    
    # Try to commit the change
    try:
        subprocess.run(f"git add {queue_path} && git commit -m 'Added job: {script}' && git push", 
                      shell=True, check=True)
        print("✅ Committed and pushed job to remote")
    except subprocess.CalledProcessError:
        print("⚠️ Failed to commit/push job. You'll need to commit manually.")

def list_queue(queue_path=None, status_filter=None):
    """List all jobs in the queue, optionally filtered by status."""
    if queue_path is None:
        queue_path = Config.JOBS_QUEUE_FILE
        
    ensure_queue_exists(queue_path)
    
    try:
        df = pd.read_csv(queue_path)
        if status_filter:
            df = df[df["status"] == status_filter]
            
        if df.empty:
            print(f"No jobs found{' with status: '+status_filter if status_filter else ''}")
            return
            
        print(f"Found {len(df)} jobs{' with status: '+status_filter if status_filter else ''}:")
        for i, row in df.iterrows():
            script = row["script"]
            args = json.loads(row["args"])
            kwargs = json.loads(row["kwargs"])
            status = row["status"]
            
            kwargs_str = " ".join([f"--{k}={v}" for k, v in json.loads(row["kwargs"]).items()])
            print(f"{i+1}. [{status}] python {script}.py {' '.join(args)} {kwargs_str}")
    except Exception as e:
        print(f"❌ Error listing queue: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage the gitrunner job queue.")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add job command
    add_parser = subparsers.add_parser("add", help="Add a job to the queue")
    add_parser.add_argument("job_command", type=str, help='The full command string (in quotes) to run')
    add_parser.add_argument("--queue", type=str, help='Path to queue file')
    
    # List jobs command
    list_parser = subparsers.add_parser("list", help="List jobs in the queue")
    list_parser.add_argument("--status", type=str, choices=JOB_STATUSES, help="Filter by status")
    list_parser.add_argument("--queue", type=str, help='Path to queue file')
    
    args = parser.parse_args()
    
    # Use the provided queue path or the default
    queue_path = args.queue if hasattr(args, 'queue') and args.queue else None
    
    if args.command == "add":
        add_job_to_queue(args.job_command, queue_path=queue_path)
    elif args.command == "list":
        list_queue(queue_path=queue_path, status_filter=args.status)
    else:
        parser.print_help()