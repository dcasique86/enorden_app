import subprocess, os, sys, time

cmd = [
    sys.executable, "-m", "uvicorn", "main:app",
    "--host", "127.0.0.1", "--port", "8000",
    "--log-level", "warning"
]

creation_flags = 0x08000000 | 0x00000008

log = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log"), "w", encoding="utf-8")

proc = subprocess.Popen(
    cmd,
    cwd=os.path.dirname(os.path.abspath(__file__)),
    creationflags=creation_flags,
    stdout=log,
    stderr=log,
    close_fds=True,
)

time.sleep(2)
if proc.poll() is not None:
    log.write(f"\nProcess exited with code {proc.returncode}\n")
else:
    log.write(f"\nProcess running (PID {proc.pid})\n")
log.close()
print(f"PID: {proc.pid}, Running: {proc.poll() is None}")
