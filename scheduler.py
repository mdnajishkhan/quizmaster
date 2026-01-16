import time
import subprocess
import sys
import datetime

def run_scheduler():
    print("Starting Class Notification Scheduler...")
    print("Press Ctrl+C to stop.")
    
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Running notification check...")
        
        try:
            # Run the management command
            # Using sys.executable ensures we use the same python interpreter
            result = subprocess.run(
                [sys.executable, "manage.py", "send_class_notifications"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"Errors: {result.stderr}")
                
        except Exception as e:
            print(f"Error running command: {e}")
            
        print("Sleeping for 1 minute...")
        time.sleep(60)  # 60 seconds = 1 minute

if __name__ == "__main__":
    run_scheduler()
