import argparse
import time
from pathlib import Path

def dummy_job(number, word):
    """Run a dummy job with the given parameters."""
    print(f"Running dummy job 2 with number {number} and word {word}")
    # Simulate some work
    time.sleep(3)
    print(f"Completed dummy job 2 with number {number} and word {word}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dummy job 2 for testing gitrunner")
    parser.add_argument('number', type=str, help='A number parameter')
    parser.add_argument('--beans', type=str, help='What to put beans on')
    
    args = parser.parse_args()
    
    # Run the job with parsed arguments
    success = dummy_job(args.number, args.beans)
    
    # Exit with appropriate status code
    exit(0 if success else 1)




