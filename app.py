import os
import sys
import subprocess
import time
import threading
import json
import signal
from datetime import datetime
from flask import Flask, request, render_template_string, jsonify

app = Flask(__name__)

# ==================== CONFIGURATION ====================
UPLOAD_FOLDER = 'user_bots'
LOG_FOLDER = 'logs'
CONFIG_FILE = 'bot_config.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# Owner Details
OWNER_NAME = "@M1NXGAMINGVIP"
OWNER_DM = "@M1NXGAMINGVIP1"
ADMIN_ID = "8952615815"
BOT_TOKEN = "8955893915:AAGedlU7aj2CiBJ7y35z-zSqgobgB9LJfMI"

# Bot Process Manager
bot_processes = {}   # filename -> {process, thread, status, start_time, restarts, logs}
bot_lock = threading.Lock()

# ==================== LOAD / SAVE CONFIG ====================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# ==================== AUTO-DEPENDENCY INSTALLER ====================
def auto_install_dependencies(bot_filepath):
    """Automatically detect and install missing dependencies from the bot file."""
    install_log = []
    try:
        with open(bot_filepath, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except Exception as e:
        return [f"Could not read file: {e}"]

    # Common import name -> pip package mapping
    import_map = {
        'telegram': 'python-telegram-bot',
        'telebot': 'pyTelegramBotAPI',
        'pyrogram': 'pyrogram',
        'telethon': 'telethon',
        'discord': 'discord.py',
        'flask': 'Flask',
        'requests': 'requests',
        'aiohttp': 'aiohttp',
        'bs4': 'beautifulsoup4',
        'PIL': 'Pillow',
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'pandas': 'pandas',
        'dotenv': 'python-dotenv',
        'pymongo': 'pymongo',
        'psutil': 'psutil',
        'yt_dlp': 'yt-dlp',
        'youtube_dl': 'youtube-dl',
        'moviepy': 'moviepy',
        'sqlalchemy': 'SQLAlchemy',
        'pydantic': 'pydantic',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'httpx': 'httpx',
        'paramiko': 'paramiko',
        'redis': 'redis',
        'selenium': 'selenium',
        'playwright': 'playwright',
        'openai': 'openai',
        'google.generativeai': 'google-generativeai',
    }

    # Extract imports
    import re
    imports = set()
    for line in code.splitlines():
        line = line.strip()
        m = re.match(r'^import\s+([a-zA-Z0-9_\.]+)', line)
        if m:
            imports.add(m.group(1).split('.')[0])
        m = re.match(r'^from\s+([a-zA-Z0-9_\.]+)\s+import', line)
        if m:
            imports.add(m.group(1).split('.')[0])

    # Check each import
    for module in imports:
        if module in ('os', 'sys', 'time', 'json', 're', 'random', 'threading',
                      'subprocess', 'datetime', 'math', 'collections', 'typing',
                      'asyncio', 'logging', 'traceback', 'io', 'base64', 'hashlib',
                      'uuid', 'glob', 'shutil', 'pathlib', 'urllib', 'http', 'socket',
                      'struct', 'copy', 'itertools', 'functools', 'warnings', 'pickle'):
            continue  # built-in
        try:
            __import__(module)
        except ImportError:
            pkg = import_map.get(module, module)
            install_log.append(f"Installing missing package: {pkg}")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', pkg],
                               capture_output=True, text=True, timeout=180)
                install_log.append(f"✅ Installed: {pkg}")
            except Exception as e:
                install_log.append(f"❌ Failed to install {pkg}: {e}")
    return install_log

# ==================== BOT RUNNER WITH AUTO-RESTART ====================
def run_bot(bot_filename):
    """Run bot with auto-restart and full logging."""
    filepath = os.path.join(UPLOAD_FOLDER, bot_filename)
    log_path = os.path.join(LOG_FOLDER, f"{bot_filename}.log")

    while True:
        with bot_lock:
            if bot_filename not in bot_processes:
                return
            if bot_processes[bot_filename]['status'] == 'stopped':
                return

        # Auto-install dependencies before first run
        if bot_processes[bot_filename].get('deps_installed') is False:
            deps_log = auto_install_dependencies(filepath)
            with bot_lock:
                if bot_filename in bot_processes:
                    bot_processes[bot_filename]['deps_log'] = deps_log
                    bot_processes[bot_filename]['deps_installed'] = True
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n===== AUTO INSTALL @ {datetime.now()} =====\n")
                for l in deps_log:
                    f.write(l + "\n")

        try:
            with open(log_path, 'a', encoding='utf-8') as logf:
                logf.write(f"\n===== STARTING @ {datetime.now()} =====\n")

            process = subprocess.Popen(
                [sys.executable, '-u', filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=UPLOAD_FOLDER
            )

            with bot_lock:
                if bot_filename in bot_processes:
                    bot_processes[bot_filename]['process'] = process
                    bot_processes[bot_filename]['status'] = 'running'
                    bot_processes[bot_filename]['start_time'] = datetime.now().isoformat()

            # Stream logs
            with open(log_path, 'a', encoding='utf-8') as logf:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        logf.write(line)
                        logf.flush()
                    with bot_lock:
                        if bot_filename not in bot_processes:
                            process.kill()
                            return
                        if bot_processes[bot_filename]['status'] == 'stopped':
                            process.kill()
                            return

            process.wait()
            exit_code = process.returncode

            with open(log_path, 'a', encoding='utf-8') as logf:
                logf.write(f"\n===== STOPPED (exit code {exit_code}) @ {datetime.now()} =====\n")

        except Exception as e:
            with open(log_path, 'a', encoding='utf-8') as logf:
                logf.write(f"\n[ERROR] {e}\n")

        with bot_lock:
            if bot_filename not in bot_processes:
                return
            if bot_processes[bot_filename]['status'] == 'stopped':
                return
            bot_processes[bot_filename]['restarts'] += 1

        time.sleep(3)

# ==================== HTML TEMPLATE (PREMIUM UI) ====================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M1NX HOSTING PANEL</title>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        color: #e2e8f0;
        min-height: 100vh;
        padding: 20px;
    }
    .container { max-width: 1100px; margin: 0 auto; }

    /* Header */
    .header {
        display: flex; align-items: center; justify-content: space-between;
        background: rgba(30, 41, 59, 0.85);
        padding: 18px 24px; border-radius: 14px;
        border: 1px solid rgba(56, 189, 248, 0.3);
        box-shadow: 0 8px 30px rgba(0,0,0,0.4);
        margin-bottom: 22px;
        backdrop-filter: blur(10px);
    }
    .header h1 {
        font-size: 22px; font-weight: 700;
        background: linear-gradient(90deg, #38bdf8, #a855f7, #ec4899);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .owner-info { display: flex; gap: 14px; align-items: center; font-size: 13px; }
    .owner-badge {
        background: linear-gradient(90deg, #22c55e, #16a34a);
        padding: 6px 12px; border-radius: 20px; font-weight: 600;
        color: #fff; text-decoration: none;
    }
    .dm-badge {
        background: linear-gradient(90deg, #3b82f6, #6366f1);
        padding: 6px 12px; border-radius: 20px; font-weight: 600;
        color: #fff; text-decoration: none;
    }

    /* Cards */
    .card {
        background: rgba(30, 41, 59, 0.75);
        border: 1px solid rgba(56, 189, 248, 0.2);
        border-radius: 16px; padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.35);
        backdrop-filter: blur(12px);
    }
    .card h2 {
        font-size: 17px; margin-bottom: 16px;
        color: #38bdf8; font-weight: 600;
        display: flex; align-items: center; gap: 8px;
    }

    /* Inputs */
    label { font-size: 13px; color: #94a3b8; display: block; margin-bottom: 6px; }
    input[type="file"], input[type="text"] {
        width: 100%; padding: 12px 14px; border-radius: 10px;
        border: 1px solid #334155; background: #0f172a;
        color: #fff; font-size: 14px; outline: none;
        transition: 0.2s; margin-bottom: 12px;
    }
    input:focus { border-color: #38bdf8; box-shadow: 0 0 0 3px rgba(56,189,248,0.15); }

    button {
        padding: 12px 20px; border-radius: 10px; border: none;
        background: linear-gradient(90deg, #38bdf8, #0ea5e9);
        color: #0f172a; font-weight: 700; font-size: 14px;
        cursor: pointer; transition: 0.2s; margin-right: 8px;
    }
    button:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(56,189,248,0.4); }
    .btn-danger { background: linear-gradient(90deg, #ef4444, #dc2626); color: #fff; }
    .btn-warn { background: linear-gradient(90deg, #f59e0b, #d97706); color: #fff; }
    .btn-success { background: linear-gradient(90deg, #22c55e, #16a34a); color: #fff; }
    .btn-purple { background: linear-gradient(90deg, #a855f7, #7c3aed); color: #fff; }

    /* Messages */
    .msg {
        padding: 12px 16px; border-radius: 10px; margin-top: 14px;
        font-size: 14px; word-break: break-word;
    }
    .msg-ok { background: rgba(34,197,94,0.15); border: 1px solid #22c55e; color: #4ade80; }
    .msg-err { background: rgba(239,68,68,0.15); border: 1px solid #ef4444; color: #f87171; }
    .msg-warn { background: rgba(245,158,11,0.15); border: 1px solid #f59e0b; color: #fbbf24; }

    /* Bot list */
    .bot-item {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid #334155; border-radius: 12px;
        padding: 16px; margin-bottom: 12px;
    }
    .bot-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
    .bot-name { font-weight: 700; color: #e2e8f0; font-size: 15px; }
    .status-pill {
        padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .status-running { background: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid #22c55e; }
    .status-stopped { background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid #ef4444; }
    .bot-meta { font-size: 12px; color: #94a3b8; margin-top: 10px; line-height: 1.7; }
    .bot-actions { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
    .bot-actions button { padding: 8px 14px; font-size: 12px; }

    /* Logs */
    .log-box {
        background: #000; color: #4ade80; font-family: 'Consolas', monospace;
        font-size: 12px; padding: 14px; border-radius: 10px;
        max-height: 340px; overflow-y: auto; margin-top: 12px;
        border: 1px solid #1e293b; white-space: pre-wrap; word-break: break-word;
    }
    .log-line-err { color: #f87171; }
    .log-line-ok { color: #4ade80; }

    /* Install status bar */
    .install-bar {
        background: rgba(15,23,42,0.7); border: 1px solid #334155;
        border-radius: 10px; padding: 12px; margin-top: 10px;
        font-size: 12px; color: #94a3b8;
    }
    .install-item { padding: 4px 0; border-bottom: 1px dashed #1e293b; }
    .install-item:last-child { border-bottom: none; }

    /* Copy button */
    .copy-btn {
        background: #334155; color: #e2e8f0; border: none;
        padding: 6px 12px; border-radius: 6px; font-size: 11px;
        cursor: pointer; margin-left: 8px;
    }
    .copy-btn:hover { background: #475569; }

    .hidden { display: none; }
    .flex-between { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
    .file-input-wrap { position: relative; }
</style>
</head>
<body>
<div class="container">

    <!-- HEADER -->
    <div class="header">
        <h1>⚡ M1NX HOSTING PANEL</h1>
        <div class="owner-info">
            <span>👤 Owner:</span>
            <a href="https://t.me/M1NXGAMINGVIP" target="_blank" class="owner-badge">{{ owner_name }}</a>
            <a href="https://t.me/M1NXGAMINGVIP1" target="_blank" class="dm-badge">💬 DM {{ owner_dm }}</a>
        </div>
    </div>

    <!-- UPLOAD CARD -->
    <div class="card">
        <h2>📁 Upload Bot File (.py)</h2>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <label>Select Python File</label>
            <input type="file" name="file" accept=".py" required>
            <button type="submit" class="btn-success">⬆ Upload Bot</button>
        </form>
    </div>

    <!-- START CARD -->
    <div class="card">
        <h2>🚀 Start Bot (Auto Install Dependencies + Auto Restart)</h2>
        <form action="/start" method="post">
            <label>Bot Filename (e.g. main.py)</label>
            <input type="text" name="filename" placeholder="main.py" required>
            <button type="submit" class="btn-purple">▶ Start Bot</button>
        </form>
        <div style="font-size:12px;color:#94a3b8;margin-top:10px;">
            ℹ Missing packages will be installed automatically before starting.
        </div>
    </div>

    <!-- MESSAGE -->
    {% if message %}
        <div class="msg {{ msg_class }}">{{ message }}</div>
    {% endif %}

    <!-- BOT LIST -->
    <div class="card">
        <h2>🤖 Active Bots ({{ bots|length }})</h2>
        {% if bots %}
            {% for bot in bots %}
            <div class="bot-item">
                <div class="bot-head">
                    <div class="bot-name">🐍 {{ bot.name }}</div>
                    <span class="status-pill {{ 'status-running' if bot.status == 'running' else 'status-stopped' }}">
                        {{ '● Running' if bot.status == 'running' else '● Offline' }}
                    </span>
                </div>
                <div class="bot-meta">
                    <div>🔄 Restarts: <b>{{ bot.restarts }}</b></div>
                    <div>⏱ Started: <b>{{ bot.start_time or 'N/A' }}</b></div>
                    <div>📦 Dependencies: <b>{{ 'Installed' if bot.deps_installed else 'Pending' }}</b></div>
                </div>
                {% if bot.deps_log %}
                <div class="install-bar">
                    <div style="color:#38bdf8;font-weight:600;margin-bottom:6px;">📦 Auto Install Log</div>
                    {% for line in bot.deps_log %}
                        <div class="install-item">{{ line }}</div>
                    {% endfor %}
                </div>
                {% endif %}
                <div class="bot-actions">
                    {% if bot.status == 'running' %}
                        <form action="/stop" method="post" style="display:inline;">
                            <input type="hidden" name="filename" value="{{ bot.name }}">
                            <button type="submit" class="btn-danger">⏹ Stop</button>
                        </form>
                    {% else %}
                        <form action="/restart" method="post" style="display:inline;">
                            <input type="hidden" name="filename" value="{{ bot.name }}">
                            <button type="submit" class="btn-success">▶ Start</button>
                        </form>
                    {% endif %}
                    <button type="button" class="btn-warn" onclick="toggleLog('log-{{ loop.index }}')">📜 View Logs</button>
                    <button type="button" class="copy-btn" onclick="copyLog('log-{{ loop.index }}')">📋 Copy Logs</button>
                    <form action="/delete" method="post" style="display:inline;" onsubmit="return confirm('Delete this bot permanently?');">
                        <input type="hidden" name="filename" value="{{ bot.name }}">
                        <button type="submit" class="btn-danger">🗑 Delete</button>
                    </form>
                </div>
                <div id="log-{{ loop.index }}" class="log-box hidden">{{ bot.logs }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div style="color:#64748b;font-size:14px;text-align:center;padding:20px;">
                No bots uploaded yet.
            </div>
        {% endif %}
    </div>

    <!-- FOOTER -->
    <div style="text-align:center;font-size:12px;color:#64748b;margin-top:30px;">
        © {{ year }} M1NX HOSTING PANEL · Powered by {{ owner_name }}
    </div>
</div>

<script>
function toggleLog(id) {
    const el = document.getElementById(id);
    el.classList.toggle('hidden');
}
function copyLog(id) {
    const el = document.getElementById(id);
    const text = el.innerText;
    navigator.clipboard.writeText(text).then(() => {
        alert('Logs copied to clipboard!');
    });
}
</script>
</body>
</html>
'''

# ==================== HELPERS ====================
def get_bots_list():
    bots = []
    with bot_lock:
        for name, info in bot_processes.items():
            bots.append({
                'name': name,
                'status': info['status'],
                'restarts': info['restarts'],
                'start_time': info.get('start_time', ''),
                'deps_installed': info.get('deps_installed', False),
                'deps_log': info.get('deps_log', []),
                'logs': get_log_tail(name, 200),
            })
    return bots

def get_log_tail(bot_name, lines=200):
    log_path = os.path.join(LOG_FOLDER, f"{bot_name}.log")
    if not os.path.exists(log_path):
        return "No logs yet."
    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().splitlines()
        return "\n".join(content[-lines:])
    except:
        return "Could not read logs."

def render_page(message=None, msg_class='msg-ok'):
    return render_template_string(
        HTML_TEMPLATE,
        owner_name=OWNER_NAME,
        owner_dm=OWNER_DM,
        bots=get_bots_list(),
        message=message,
        msg_class=msg_class,
        year=datetime.now().year
    )

# ==================== ROUTES ====================
@app.route('/')
def home():
    return render_page()

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.py'):
        return render_page("❌ Only .py files are allowed!", "msg-err")
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Init bot entry (offline until started)
    with bot_lock:
        if file.filename not in bot_processes:
            bot_processes[file.filename] = {
                'process': None,
                'thread': None,
                'status': 'stopped',
                'start_time': None,
                'restarts': 0,
                'deps_installed': False,
                'deps_log': [],
            }
    return render_page(f"✅ '{file.filename}' uploaded successfully!", "msg-ok")

@app.route('/start', methods=['POST'])
def start():
    filename = request.form.get('filename', '').strip()
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return render_page(f"❌ File '{filename}' not found!", "msg-err")

    with bot_lock:
        if filename in bot_processes and bot_processes[filename]['status'] == 'running':
            return render_page(f"⚠️ '{filename}' is already running!", "msg-warn")

        bot_processes[filename] = {
            'process': None,
            'thread': None,
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'restarts': 0,
            'deps_installed': False,
            'deps_log': [],
        }

    thread = threading.Thread(target=run_bot, args=(filename,), daemon=True)
    thread.start()
    with bot_lock:
        bot_processes[filename]['thread'] = thread

    return render_page(f"🚀 '{filename}' started! Auto-install + Auto-restart active.", "msg-ok")

@app.route('/stop', methods=['POST'])
def stop():
    filename = request.form.get('filename', '').strip()
    with bot_lock:
        if filename not in bot_processes:
            return render_page(f"❌ '{filename}' not running!", "msg-err")
        info = bot_processes[filename]
        info['status'] = 'stopped'
        proc = info.get('process')
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(0.5)
                if proc.poll() is None:
                    proc.kill()
            except:
                pass
    return render_page(f"⏹ '{filename}' stopped.", "msg-warn")

@app.route('/restart', methods=['POST'])
def restart():
    filename = request.form.get('filename', '').strip()
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return render_page(f"❌ File '{filename}' not found!", "msg-err")

    with bot_lock:
        if filename in bot_processes:
            info = bot_processes[filename]
            info['status'] = 'stopped'
            proc = info.get('process')
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except:
                    pass
            time.sleep(1)
        bot_processes[filename] = {
            'process': None,
            'thread': None,
            'status': 'running',
            'start_time': datetime.now().isoformat(),
            'restarts': 0,
            'deps_installed': False,
            'deps_log': [],
        }

    thread = threading.Thread(target=run_bot, args=(filename,), daemon=True)
    thread.start()
    with bot_lock:
        bot_processes[filename]['thread'] = thread

    return render_page(f"🔄 '{filename}' restarted!", "msg-ok")

@app.route('/delete', methods=['POST'])
def delete():
    filename = request.form.get('filename', '').strip()
    with bot_lock:
        if filename in bot_processes:
            info = bot_processes[filename]
            info['status'] = 'stopped'
            proc = info.get('process')
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except:
                    pass
            del bot_processes[filename]
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
    return render_page(f"🗑 '{filename}' deleted.", "msg-warn")

# ==================== MAIN ====================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)