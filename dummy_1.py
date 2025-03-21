import argparse
from pathlib import Path
import json
import uuid
import time

def dummy_job(number, word):
    """Run a dummy job with the given parameters."""
    print(f"Running dummy job 1 with number {number} and word {word}")
    # Simulate some work
    time.sleep(2)
    print(f"Completed dummy job 1 with number {number} and word {word}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dummy job 1 for testing gitrunner")
    parser.add_argument('number', type=str, help='A number parameter')
    parser.add_argument('--cheese', type=str, help='What to put cheese on')
    
    args = parser.parse_args()
    
    # Run the job with parsed arguments
    success = dummy_job(args.number, args.cheese)
    
    # Exit with appropriate status code
    exit(0 if success else 1)




