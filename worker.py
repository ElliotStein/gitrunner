import os
import pandas as pd
import subprocess
import time
import argparse
import json
import sys
import shutil
import logging
from pathlib import Path
from gitrunner_utils import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gitrunner.log')
    ]
)
logger = logging.getLogger('gitrunner')


STATUS_CHOICES = ['ready', 'running', 'done', 'failed']

# Setup git configuration
def setup_git():
    if Config.GIT_USER_EMAIL and Config.GIT_USER_NAME:
        logger.info(f"Setting up git with user {Config.GIT_USER_NAME} <{Config.GIT_USER_EMAIL}>")
        subprocess.run(f"git config user.email '{Config.GIT_USER_EMAIL}'", shell=True)
        subprocess.run(f"git config user.name '{Config.GIT_USER_NAME}'", shell=True)
    else:
        logger.warning("GIT_USER_EMAIL or GIT_USER_NAME not set. Git commits will use system defaults.")

# Clone or pull latest repo
def pull_repo():
    try:
        logger.debug("Pulling latest changes from repository")
        subprocess.run("git pull", shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        logger.error("Failed to pull repository", exc_info=True)
        return False

def job_to_command(job):
    script = job["script"]
    if not script.endswith(".py"):
        script = script + ".py"
    
    # Parse JSON arguments
    args_list = json.loads(job["args"])
    kwargs_dict = json.loads(job["kwargs"])
    
    # Build command arguments
    args_str = " ".join([str(arg) for arg in args_list])
    kwargs_str = " ".join([f"--{k}={v}" for k, v in kwargs_dict.items()])
    
    return f"python {script} {args_str} {kwargs_str}", script, args_str, kwargs_str

def check_job_success(return_code):
    """Check if the job was successful based on the return code."""
    return return_code == 0 #X

def set_job_status(job, status):
    logger.info(f"Setting job status: {job['script']} -> {status}")
    df = pd.read_csv(Config.JOBS_QUEUE_FILE)
    df.loc[(df["script"] == job["script"]) & 
           (df["args"] == job["args"]) & 
           (df["kwargs"] == job["kwargs"]), "status"] = status
    df.to_csv(Config.JOBS_QUEUE_FILE, index=False)

def subprocess_run(command, debug=False, check=False):
    if debug:
        logger.info(f"Would run: {command}")
        return 0
    else:
        try:
            logger.debug(f"Running command: {command}")
            result = subprocess.run(command, shell=True, check=check)
            logger.debug(f"Command completed with return code: {result.returncode}")
            return result.returncode
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}", exc_info=True)
            return e.returncode

def push_results(job):
    """Push changes in the results directory to the repository.
    Let Git handle the case where there are no changes."""
    
    script_name = job["script"]
    if script_name.endswith(".py"):
        script_name = script_name[:-3]
    
    args_list = json.loads(job["args"])
    args_str = "_".join(args_list) if args_list else "no_args"
    
    commit_msg = f"Add results for {script_name}_{args_str}"
    
    try:
        # Add any new files to git tracking
        subprocess.run(f"git add {Config.RESULTS_DIR}", shell=True, check=True)
        
        # Attempt to commit changes - Git will do nothing if there are no changes
        result = subprocess.run(f'git commit -m "{commit_msg}"', shell=True, capture_output=True, text=True)
        
        # Check if anything was committed
        if "nothing to commit" in result.stdout or "nothing added to commit" in result.stdout:
            print("No changes in results directory to push")
            return True
        
        # Push to remote
        subprocess.run("git push", shell=True, check=True)
        
        print(f"✅ Pushed results to repository: {commit_msg}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to push results: {e}")
        return False

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true")
parser.add_argument("--results-dir", type=str, help="Directory to track results in")
parser.add_argument("--max-job-attempts", type=int, help="Maximum number of attempts per job before giving up")
parser.add_argument("--queue-file", type=str, help="Path to the queue file")
parser.add_argument("--sleep-time", type=int, help="Seconds to sleep between job checks")
if __name__ == "__main__":
    args = parser.parse_args()
    debug = args.debug
    
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")
    
    # Update configuration from arguments
    Config.update_from_args(args)
    
    # Ensure results directory exists
    Path(Config.RESULTS_DIR).mkdir(exist_ok=True)
    logger.info(f"Results will be stored in: {Config.RESULTS_DIR}")
    
    # Setup git configuration
    setup_git()
    pull_repo()

    attempts = 0
    logger.info("Starting job processing loop")
    while True:
        # Read job file
        try:
            df = pd.read_csv(Config.JOBS_QUEUE_FILE)
        except Exception as e:
            print(f"Error reading job file: {e}")
            time.sleep(Config.SLEEP_TIME * (attempts + 1))
            attempts += 1
            if attempts >= Config.MAX_ATTEMPTS:
                print(f"Failed to read job file after {Config.MAX_ATTEMPTS} attempts. Exiting...")
                sys.exit(1)
            continue

        # Find a model that hasn't been run
        available_jobs = df[df["status"] == "ready"]
        if available_jobs.empty:
            print(f"No available jobs. ({attempts + 1}/{Config.MAX_ATTEMPTS}) Sleeping...")
            time.sleep(Config.SLEEP_TIME * (attempts + 1))
            pull_repo()
            attempts += 1
            if attempts >= Config.MAX_ATTEMPTS:
                print(f"No jobs available after {Config.MAX_ATTEMPTS} attempts. Exiting...")
                sys.exit(0)
            continue

        attempts = 0

        # Select a model and mark as running
        job = available_jobs.iloc[0].to_dict()
        command, script, args_str, kwargs_str = job_to_command(job)
        print(f"Claiming job: {command}")

        set_job_status(job, "running")

        # Commit and push status update
        git_cmd = f"git pull && git add {Config.JOBS_QUEUE_FILE} && git commit -m 'Started {script} {args_str} {kwargs_str}' && git push"
        if subprocess_run(git_cmd, debug) != 0:
            print("Failed to update job status to running. Retrying...")
            pull_repo()
            set_job_status(job, "ready")  # Reset job status since we couldn't claim it
            time.sleep(Config.SLEEP_TIME)
            continue #X

        # Run the model
        return_code = subprocess_run(command, debug)

        # Update status based on success/failure
        if check_job_success(return_code):
            set_job_status(job, "done")
            status_msg = "Finished"
            
            # Push results if any changes
            push_results(job)
        else:
            set_job_status(job, "failed")
            status_msg = "Failed"

        # Push final status
        git_cmd = f"git pull && git add {Config.JOBS_QUEUE_FILE} && git commit -m '{status_msg} {script} {args_str} {kwargs_str}' && git push"
        if subprocess_run(git_cmd, debug) != 0:
            print(f"Failed to update job status to {status_msg}. Continuing...")

        print(f"{status_msg} processing {script} {args_str} {kwargs_str}. Sleeping before next check...")
        time.sleep(Config.SLEEP_TIME)
        pull_repo()
