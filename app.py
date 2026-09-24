import os
import subprocess
import time
import threading
from flask import Flask, request, render_template_string

app = Flask(__name__)

# আপলোড করা বটের জন্য ফোল্ডার
UPLOAD_FOLDER = 'user_bots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bot_threads = {}

# ওয়েবসাইটের ডিজাইন (HTML/CSS)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Bot Hosting Panel</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #fff; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 90vh; margin: 0; }
        .card { background: #1e293b; padding: 30px; border-radius: 16px; width: 100%; max-width: 420px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h2 { color: #38bdf8; text-align: center; margin-top: 0; font-size: 24px; }
        label { font-size: 14px; color: #cbd5e1; display: block; margin-bottom: 6px; }
        input[type="file"], input[type="text"] { width: 100%; padding: 12px; margin-bottom: 12px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: #fff; box-sizing: border-box; outline: none; }
        input[type="file"]::file-selector-button { background: #334155; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; }
        button { width: 100%; padding: 12px; border-radius: 8px; border: none; background: #38bdf8; color: #0f172a; font-weight: bold; font-size: 15px; cursor: pointer; transition: 0.2s; }
        button:hover { background: #0284c7; color: #fff; }
        .divider { border: 0.5px solid #334155; margin: 24px 0; }
        .msg { background: #1e293b; padding: 12px; border-radius: 8px; margin-top: 15px; text-align: center; color: #4ade80; border: 1px solid #22c55e; font-size: 14px; word-break: break-all; }
    </style>
</head>
<body>
<div class="card">
    <h2>🐍 Python Bot Hosting</h2>
    
    <form action="/upload" method="post" enctype="multipart/form-data">
        <label>১. বট ফাইল আপলোড করুন (.py):</label>
        <input type="file" name="file" accept=".py" required>
        <button type="submit">📁 আপলোড ফাইল</button>
    </form>

    <div class="divider"></div>

    <form action="/start" method="post">
        <label>২. ফাইলের নাম দিয়ে বট রান করুন:</label>
        <input type="text" name="filename" placeholder="উদাহরণ: main.py" required>
        <button type="submit">🚀 রান বট (Auto-Restart Active)</button>
    </form>

    {% if message %}
        <div class="msg">{{ message }}</div>
    {% endif %}
</div>
</body>
</html>
'''

def run_bot_with_auto_restart(bot_filename):
    """বট রান করবে এবং কোনো কারণে বন্ধ হলে ৩ সেকেন্ড পর অটো-রিস্টার্ট হবে"""
    filepath = os.path.join(UPLOAD_FOLDER, bot_filename)
    while True:
        print(f"[Hosting Panel] Starting Bot: {bot_filename}...")
        process = subprocess.Popen(['python3', filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        print(f"[Hosting Panel] Bot stopped or crashed:\n{stderr}")
        print("[Hosting Panel] Auto-restarting in 3 seconds...")
        time.sleep(3)

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if file and file.filename.endswith('.py'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        return render_template_string(HTML_TEMPLATE, message=f"✅ '{file.filename}' আপলোড সফল হয়েছে!")
    return render_template_string(HTML_TEMPLATE, message="❌ শুধুমাত্র .py ফাইল আপলোড করুন!")

@app.route('/start', methods=['POST'])
def start():
    filename = request.form.get('filename')
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return render_template_string(HTML_TEMPLATE, message=f"❌ '{filename}' ফাইলটি পাওয়া যায়নি!")

    if filename in bot_threads and bot_threads[filename].is_alive():
        return render_template_string(HTML_TEMPLATE, message=f"⚠️ '{filename}' বটটি অলরেডি রান করা আছে!")

    thread = threading.Thread(target=run_bot_with_auto_restart, args=(filename,), daemon=True)
    thread.start()
    bot_threads[filename] = thread

    return render_template_string(HTML_TEMPLATE, message=f"🚀 '{filename}' চালু হয়েছে! (অটো-রিস্টার্ট একটিভ)")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
