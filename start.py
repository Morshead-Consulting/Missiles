"""
Development launcher for the Solara app.
Clears port 8765 before starting to avoid WinError 10048.
"""
import subprocess
import sys


def kill_port(port):
    result = subprocess.run(
        f'netstat -ano | findstr :{port}',
        shell=True, capture_output=True, text=True
    )
    pids = set()
    for line in result.stdout.splitlines():
        if 'LISTENING' in line:
            pid = line.strip().split()[-1]
            pids.add(pid)
    for pid in pids:
        subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True)
        print(f"Killed process {pid} on port {port}")


kill_port(8765)
subprocess.run(["uv", "run", "solara", "run", "app.py"] + sys.argv[1:])
