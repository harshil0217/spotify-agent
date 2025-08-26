import subprocess
import os

# Set environment variables
env = os.environ.copy()
env["SPOTIFY_CLIENT_ID"] = "c86f7613eb3c42318201c2e24625ab71"
env["SPOTIFY_CLIENT_SECRET"] = "84ddcc1d0cd046d4be5122a8f9e453c0"
env["SPOTIFY_REDIRECT_URI"] = "http://127.0.0.1:8090/callback"

# Command and arguments
cmd = [
    "--directory",
    "/home/harshil0216/spotify-mcp",
    "run",
    "spotify-mcp"
]

# Run the command
process = subprocess.Popen(
    cmd,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Print output in real-time
for line in process.stdout:
    print(line, end='')

for line in process.stderr:
    print(line, end='')

process.wait()