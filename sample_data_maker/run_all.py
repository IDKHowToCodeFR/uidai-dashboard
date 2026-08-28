import subprocess
import sys
import os

scripts = [
    "apr.py",
    "cdr.py",
    "unimate.py",
    "ccf.py"
]

def run_script(script):
    print(f"\n========================================")
    print(f"Running {script} (using defaults: 50k/day, 180 days)")
    print(f"========================================\n")
    script_path = os.path.join(os.path.dirname(__file__), script)
    
    # We pipe newlines to stdin so it accepts the default inputs
    process = subprocess.Popen(
        [sys.executable, script_path],
        stdin=subprocess.PIPE,
        text=True
    )
    process.communicate(input="\n\n")
    if process.returncode != 0:
        print(f"Error running {script}")
    else:
        print(f"Finished {script}")

if __name__ == "__main__":
    for script in scripts:
        run_script(script)
    print("\nAll data generation complete!")
