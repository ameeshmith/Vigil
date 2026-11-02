import sys
import subprocess
import time
import os

def main():
    print("==================================================================")
    print("      Starting Vigil AI (FastMCP Server + FastAPI Web Server)     ")
    print("==================================================================")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # Start MCP Server on port 8001
    print("[1/2] Launching FastMCP Server on http://127.0.0.1:8001...")
    mcp_proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.server"],
        env=env
    )

    time.sleep(1.5)

    # Start FastAPI App on port 8000
    print("[2/2] Launching FastAPI Web App on http://127.0.0.1:8000...")
    try:
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"],
            env=env
        )
        api_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        mcp_proc.terminate()
        try:
            mcp_proc.wait(timeout=2)
        except Exception:
            mcp_proc.kill()

if __name__ == "__main__":
    main()

