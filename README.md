# gitrunner
Simple repo to manage distributed jobs from a centralised cloud based queue
![gitrunner](./gitrunner.png)

🏃‍♂️ gitrunner: Lightweight Distributed Job Coordinator Using Git

## 🔧 What it does

gitrunner is a simple system to coordinate distributed jobs across multiple machines—without any centralized server or queue system. It uses a GitHub repository as the shared source of truth, tracking job statuses in a version-controlled file.

Each machine:
- Pulls a list of models (or jobs) from the repo.
- Claims an available job (marked ready) by setting its status to running.
- Runs the task (e.g. python evaluate_model.py --model X)
- Pushes results and updates the status to run (or resets to ready on failure).

This guarantees each job runs once, even across multiple independently managed machines.

⸻
## ⚙️ How it works
1. **Shared Repo:** A GitHub repo contains a CSV file like:
```
script,args,kwargs,status
dummy.py,"[""1""]","{""cheese"": ""on,toast""}",ready
dummy.py,"[""2""]","{""beans"": ""on,toast""}",ready
```


2. **Worker Script:** Each machine runs a script that:
   - Pulls the repo
   - Finds the first ready-to-run model
   - Sets its status to running and pushes the change
   - Runs the job locally
   - Updates the job status to run or back to ready (on failure)
   - Repeats
3. **Concurrency Strategy:** Since only ~8 machines are used and Git tracks conflicts, occasional race conditions are rare and manageable (e.g., via manual resets or re-tries).

⸻

## ✅ Why use gitrunner?
- 🧠 No Redis, no servers, no orchestration
- 🪄 Leverages Git as the coordination layer
- 🔁 Version-controlled job queue
- 🌍 Works anywhere Git works
- 🔧 Easy to set up and debug
- 💥 Crash-tolerant and restartable

## 📋 Getting Started

### Basic Usage

1. **Clone this repository:**
   ```bash
   git clone https://github.com/username/gitrunner.git
   cd gitrunner
   ```

2. **Add jobs to the queue:**
   ```bash
   # Add a job with arguments
   python gitrunner_utils.py add 'dummy.py 1 --cheese="on,toast"'
   
   # List jobs in the queue
   python gitrunner_utils.py list
   
   # List only jobs with a specific status
   python gitrunner_utils.py list --status ready
   ```

3. **Run the worker to process jobs:**
   ```bash
   python worker.py
   
   # Run the worker with debug logging
   python worker.py --debug
   
   # Specify a custom results directory
   python worker.py --results-dir /path/to/results
   
   # Configure the maximum job retry attempts
   python worker.py --max-job-attempts 5
   
   # Specify a custom queue file
   python worker.py --queue-file /path/to/queue.csv
   ```

### Using gitrunner in your own project

You can use gitrunner to manage jobs from your own project without relocating your code:

1. **Setup a dedicated queue repository:**
   - Create a new GitHub repository to store your job queue
   - Clone it to your local machine

2. **Create a job manager script in your project:**
   ```python
   #!/usr/bin/env python
   # job_manager.py
   
   import os
   import sys
   import subprocess
   from pathlib import Path
   
   # Path to gitrunner directory (adjust as needed)
   GITRUNNER_PATH = "/path/to/gitrunner"
   QUEUE_REPO_PATH = "/path/to/job_queue_repo"
   
   def add_job(command):
       """Add a job to the queue"""
       # Change to the queue repo
       os.chdir(QUEUE_REPO_PATH)
       
       # Use gitrunner's utility to add the job
       subprocess.run(f"python {GITRUNNER_PATH}/gitrunner_utils.py add '{command}'", shell=True, check=True)
       
       # Return to original directory
       os.chdir(os.environ.get("OLDPWD", "."))
   
   def run_worker():
       """Run the worker to process jobs"""
       # Change to the queue repo
       os.chdir(QUEUE_REPO_PATH)
       
       # Start the worker
       subprocess.run(f"python {GITRUNNER_PATH}/worker.py", shell=True)
   
   if __name__ == "__main__":
       if len(sys.argv) < 2:
           print("Usage: python job_manager.py [add|worker] [command]")
           sys.exit(1)
       
       if sys.argv[1] == "add":
           if len(sys.argv) < 3:
               print("Usage: python job_manager.py add 'command to run'")
               sys.exit(1)
           add_job(sys.argv[2])
       elif sys.argv[1] == "worker":
           run_worker()
       else:
           print(f"Unknown command: {sys.argv[1]}")
           print("Usage: python job_manager.py [add|worker] [command]")
           sys.exit(1)
   ```

3. **Add jobs for your project with relative paths:**
   ```bash
   # If your queue repo is separate from your project,
   # use relative paths to reference your scripts
   python job_manager.py add 'python ../../my_project/analyze_data.py --input="../../my_project/data/sample.csv"'
   ```

4. **Start the worker from any machine:**
   ```bash
   python job_manager.py worker
   ```

5. **Tips for using with your own project:**
   - Use absolute or carefully constructed relative paths in your job commands
   - Make your scripts flexible about where they're run from
   - Consider setting environment variables in your worker scripts to handle paths
   - If your scripts need specific dependencies, ensure they're installed on all worker machines

## 🚀 Advanced Usage

### Environment Variables

The worker respects these environment variables:
- `GIT_USER_EMAIL`: Email to use for git commits
- `GIT_USER_NAME`: Username to use for git commits
- `RESULTS_DIR`: Directory where results are stored
- `JOBS_QUEUE_FILE`: Path to the queue file
- `SLEEP_TIME`: Seconds to sleep between job checks
- `MAX_ATTEMPTS`: Maximum number of attempts to find a job before exiting
- `MAX_JOB_ATTEMPTS`: Maximum number of attempts to retry a failed job

### Using with multiple worker machines

1. Clone the queue repository on each machine
2. Start the worker on each machine
3. Each machine will claim jobs as they become available
4. Git handles conflicts if multiple machines try to claim the same job

### Automatic retry of failed jobs

The worker will automatically retry failed jobs up to a configurable maximum number of attempts. This can be set with the `--max-job-attempts` flag or the `MAX_JOB_ATTEMPTS` environment variable.

### Running tests

```bash
# Run the test suite
python -m unittest test_gitrunner.py
```

## 🔧 Troubleshooting

- **Git Conflicts**: If you encounter git conflicts, manually resolve them and reset job status if needed
- **Worker Crashes**: If a worker crashes, the job remains in "running" state - it will need to be manually reset to "ready"
- **Debugging**: Check the `gitrunner.log` file for detailed logs when troubleshooting issues