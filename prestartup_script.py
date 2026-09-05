import importlib.util
import subprocess
import sys
import os
import folder_paths
import time
import shutil
import signal
import re
import requests
import dotenv
from pathlib import Path
from importlib.metadata import distribution, PackageNotFoundError

USER_DATA_DIR = os.path.join(folder_paths.get_user_directory(), "DadosNodes")
os.makedirs(USER_DATA_DIR, exist_ok=True)

def is_package_installed(package_name):
    try:
        distribution(package_name)
        return True
    except PackageNotFoundError:
        return False

def install_package_if_missing(package_spec):
    match = re.match(r'^([a-zA-Z0-9\-_]+)', package_spec)
    if not match:
        return
    base_name = match.group(1)
    if is_package_installed(base_name):
        print(f"✅ {base_name} already installed.")
    else:
        print(f"⬇️ Installing {package_spec}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])

def ensure_deepseek_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(base_dir, "deepseek_api")
    if not os.path.exists(api_dir):
        print("DeepSeek-API not found. Cloning from GitHub...")
        try:
            subprocess.check_call([
                "git", "clone", "https://github.com/sums001/Deepseek-API.git", api_dir
            ])
            print("DeepSeek-API cloned successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone DeepSeek-API: {e}")
            return
    req_path = os.path.join(api_dir, "requirements.txt")
    if os.path.exists(req_path):
        print("Checking DeepSeek dependencies...")
        with open(req_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                install_package_if_missing(line)
    else:
        print("⚠️ requirements.txt not found in deepseek_api folder.")
    home = Path.home()
    playwright_cache = home / ".cache" / "ms-playwright"
    chromium_found = False
    if playwright_cache.exists():
        for item in playwright_cache.iterdir():
            if item.is_dir() and item.name.startswith("chromium-"):
                chromium_found = True
                break
    if chromium_found:
        print("✅ Playwright Chromium already installed.")
    else:
        print("⬇️ Installing Playwright Chromium browser...")
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("Playwright Chromium installed.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install Playwright Chromium: {e}")

def ensure_py3pin():
    if importlib.util.find_spec("py3pin") is None:
        print("py3pin is not installed. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/GgAaYyAaNn/py3-pinterest.git"])
            print("py3pin installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install py3pin: {e}")
    else:
        print("✅ py3pin already installed.")

def ensure_dynamicprompts():
    if importlib.util.find_spec("dynamicprompts") is None:
        print("dynamicprompts is not installed. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "git+https://github.com/DadoIrie/dynamicprompts.git"])
            print("dynamicprompts installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install dynamicprompts: {e}")
    else:
        print("✅ dynamicprompts already installed.")

def check_deepseek_session():
    api_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deepseek_api")
    session_dir = os.path.join(api_dir, "session")
    if not os.path.exists(session_dir) or not os.listdir(session_dir):
        print("⚠️ DeepSeek session not found.")
        print("   Please run the following command once to authenticate:")
        print(f"   cd {api_dir} && python -m deepseek.auth")
        print("   This will open a browser for you to log into DeepSeek.")

def ensure_danyapi():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(base_dir, "danyapi")
    if not os.path.exists(api_dir):
        print("DanyAPI not found. Cloning from GitHub...")
        try:
            subprocess.check_call([
                "git", "clone", "https://github.com/FANATFANATA/DanyAPI.git", api_dir
            ])
            print("DanyAPI cloned successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone DanyAPI: {e}")
            return
    else:
        print("DanyAPI already exists.")
    req_path = os.path.join(api_dir, "requirements.txt")
    if os.path.exists(req_path):
        print("Checking DanyAPI dependencies...")
        with open(req_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                install_package_if_missing(line)
    else:
        print("⚠️ requirements.txt not found in danyapi folder.")
    env_example = os.path.join(api_dir, ".env.example")
    env_file = os.path.join(api_dir, ".env")
    if not os.path.exists(env_file):
        print("Creating .env from .env.example...")
        if os.path.exists(env_example):
            try:
                shutil.copy(env_example, env_file)
                print(".env created. Please edit it to add your credentials.")
            except OSError as e:
                print(f"Failed to create .env: {e}")
        else:
            print("⚠️ .env.example not found; skipping .env creation.")
    else:
        print(".env already exists.")
    try:
        dotenv.load_dotenv(env_file)
    except Exception as e:
        print(f"⚠️ Failed to load .env: {e}")

def get_danyapi_pid():
    """Return PID of running DanyAPI server, using PID file or pgrep as fallback."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(base_dir, "danyapi")
    pid_file = os.path.join(api_dir, "danyapi.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid_str = f.read().strip()
                if pid_str:
                    pid = int(pid_str)
                    try:
                        os.kill(pid, 0)
                        return pid
                    except OSError:
                        pass
        except (ValueError, OSError):
            pass
    try:
        result = subprocess.run(["pgrep", "-f", "python -m danyapi"], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split()
            if pids:
                return int(pids[0])
    except Exception:
        pass
    return None

def kill_danyapi_server():
    pid = get_danyapi_pid()
    if pid is None:
        print("No DanyAPI server found.")
        return
    print(f"Killing DanyAPI server (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
            print(f"✅ Forcibly killed PID {pid}.")
        except OSError:
            print(f"✅ Gracefully killed PID {pid}.")
    except OSError as e:
        print(f"⚠️ Could not kill PID {pid}: {e}")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pid_file = os.path.join(base_dir, "danyapi", "danyapi.pid")
    if os.path.exists(pid_file):
        os.remove(pid_file)

def start_danyapi_server():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(base_dir, "danyapi")
    env_file = os.path.join(api_dir, ".env")
    if not os.path.exists(env_file):
        print("❌ .env not found. Cannot start DanyAPI.")
        return
    host = os.getenv("DANYAPI_HOST")
    port = os.getenv("DANYAPI_PORT")
    if host and port:
        health_url = f"http://{host}:{port}/health"
    elif host:
        health_url = f"http://{host}:8000/health"
    elif port:
        health_url = f"http://127.0.0.1:{port}/health"
    else:
        health_url = "http://127.0.0.1:8000/health"
    try:
        resp = requests.get(health_url, timeout=2)
        if resp.status_code == 200:
            print(f"✅ DanyAPI is already running on {health_url}. Skipping start.")
            return
    except Exception:
        pass
    log_file = os.path.join(api_dir, "danyapi.log")
    print(f"Starting DanyAPI server (logs: {log_file})...")
    python_exe = sys.executable
    env = os.environ.copy()
    try:
        with open(log_file, "a") as log:
            proc = subprocess.Popen(
                [python_exe, "-m", "danyapi"],
                cwd=api_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                env=env,
                start_new_session=True,
                close_fds=True,
            )
        pid_file = os.path.join(api_dir, "danyapi.pid")
        with open(pid_file, 'w') as f:
            f.write(str(proc.pid))
        time.sleep(3)
        try:
            resp = requests.get(health_url, timeout=2)
            if resp.status_code == 200:
                print(f"✅ DanyAPI started (PID: {proc.pid}) at {health_url}.")
            else:
                print("⚠️ DanyAPI started but health check non-200.")
        except Exception:
            print("⚠️ DanyAPI may not be ready. Check logs.")
    except Exception as e:
        print(f"❌ Failed to start DanyAPI: {e}")

ensure_py3pin()
ensure_dynamicprompts()
ensure_deepseek_api()
check_deepseek_session()
ensure_danyapi()
kill_danyapi_server()
start_danyapi_server()