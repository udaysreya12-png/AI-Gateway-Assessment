
import subprocess
import sys
import json

request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "ping",
    "params": {}
}

process = subprocess.run(
    [sys.executable, "server.py"],
    input=json.dumps(request) + "\n",
    capture_output=True,
    text=True,
    timeout=10
)

print("=== STDOUT ===")
print(repr(process.stdout))

print("\n=== STDERR ===")
print(process.stderr)

print("\n=== VALIDATION ===")

for line in process.stdout.splitlines():
    try:
        message = json.loads(line)
        print("Valid JSON:", message)
    except json.JSONDecodeError:
        print("INVALID STDOUT CONTENT:", repr(line))
