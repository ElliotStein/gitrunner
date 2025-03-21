import unittest
import os
import pandas as pd
from pathlib import Path
import shutil
import subprocess
import json
import sys
import tempfile

# Add directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
from worker import Config, job_to_command, set_job_status, check_job_success
import gitrunner_utils

class TestGitrunner(unittest.TestCase):
    """Test the gitrunner functionality."""
    
    def setUp(self):
        """Set up a test environment."""
        # Create a temp directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.old_dir = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a test queue file
        self.queue_file = os.path.join(self.test_dir, "test_queue.csv")
        with open(self.queue_file, "w") as f:
            f.write("script,args,kwargs,status\n")
        
        # Update configuration for testing
        Config.JOBS_QUEUE_FILE = self.queue_file
        Config.RESULTS_DIR = os.path.join(self.test_dir, "results")
        os.makedirs(Config.RESULTS_DIR, exist_ok=True)
    
    def tearDown(self):
        """Clean up the test environment."""
        os.chdir(self.old_dir)
        shutil.rmtree(self.test_dir)
    
    def test_job_to_command(self):
        """Test that job_to_command correctly converts a job to a command."""
        job = {
            "script": "test_script",
            "args": json.dumps(["arg1", "arg2"]),
            "kwargs": json.dumps({"key1": "value1", "key2": "value2"}),
            "status": "ready"
        }
        
        command, script, args_str, kwargs_str = job_to_command(job)
        
        self.assertEqual(command, "python test_script.py arg1 arg2 --key1=value1 --key2=value2")
        self.assertEqual(script, "test_script.py")
        self.assertEqual(args_str, "arg1 arg2")
        self.assertEqual(kwargs_str, "--key1=value1 --key2=value2")
    
    def test_set_job_status(self):
        """Test that set_job_status correctly updates a job's status."""
        # Add a test job
        gitrunner_utils.add_job_to_queue("test_script.py arg1 --key1=value1", queue_path=self.queue_file)
        
        # Get the job
        df = pd.read_csv(self.queue_file)
        job = df.iloc[0].to_dict()
        
        # Update the status
        set_job_status(job, "running")
        
        # Check that the status was updated
        df = pd.read_csv(self.queue_file)
        self.assertEqual(df.iloc[0]["status"], "running")
    
    def test_check_job_success(self):
        """Test that check_job_success correctly determines if a job was successful."""
        self.assertTrue(check_job_success(0))
        self.assertFalse(check_job_success(1))

if __name__ == "__main__":
    unittest.main() 