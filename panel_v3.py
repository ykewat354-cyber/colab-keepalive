"""Minecraft Colab Panel v3.0 — Start/Stop/Restart + Console + Live Log + Services + double panel links (ngrok permanent + cloudflared backup)."""
from flask import Flask, jsonify, request
import subprocess, os, threading, time
from datetime import datetime

app = Flask(__name__)

JAVA = '/opt/java25/bin/java'
FLAG = 'STOP_FLAG'

def is_running():
    r = subprocess.run(['screen', '-ls'], capture_output=True, text=True)
    return 'mcserver' in r.stdout

def do_start():
    if is_running():
        if os.path.exists(FLAG):
            os.remove(FLAG)
        return
    subprocess.run(['screen', '-S', 'mcserver', '-X', 'quit'], capture_output=True)
    subprocess.run(['screen', '-wipe'], capture_output=True)
    subprocess.Popen(['screen', '-dmS', 'mcserver', 'bash', '-c',
                      JAVA + ' -Xmx2G -Xms2G -jar server.jar nogui 2>&1 | tee server_console.log'])
    if os.path.exists(FLAG):
        os.remove(FLAG)

def do_stop():
    open(FLAG, 'w').write('1')
    subprocess.run(['screen', '-S', 'mcserver', '-X', 'stuff', 'stop\n'])

def do_restart():
    open(FLAG, 'w').write('1')
    subprocess.run(['screen', '-S', 'mcserver', '-X', 'stuff', 'stop\n'])
    for _ in range(20):
        time.sleep(3)
        if not is_running():
            break
    subprocess.run(['screen', '-S', 'mcserver', '-X', 'quit'], capture_output=True)
    subprocess.run(['screen', '-wipe'], capture_output=True)
    subprocess.Popen(['screen', '-dmS', 'mcserver', 'bash', '-c',
                      JAVA + ' -Xmx2G -Xms2G -jar server.jar nogui 2>&1 | tee server_console.log'])
    if os.path.exists(FLAG):
        os.remove(FLAG)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MC Panel</title>
<style>
body{font-family:system-ui,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:16px}
.wrap{max-width:520px;margin:0 auto}
h1{font-size:20px;text-align:center;margin:8px 0 16px}
.card{background:#1e293b;border-radius:14px;padding:16px;margin:12px 0}
.dot{display:inline-block;width:12px;height:12px;border-radius:50%;background:#ef4444;margin-right:8px}
.dot.on{background:#22c55e}
button{border:0;border-radius:10px;padding:12px 14px;font-size:15px;font-weight:600;cursor:pointer;margin:4px 2px}
.b-start{background:#22c55e;color:#052e16}
.b-stop{background:#ef4444;color:#fff}
.b-restart{background:#f59e0b;color:#451a03}
.b-send{background:#3b82f6;color:#fff;width:100%}
input{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #334155;background:#0f172a;color:#fff;font-size:15px}
pre{background:#020617;border-radius:10px;padding:12px;font-size:12px;overflow:auto;max-height:260px;white-space:pre-wrap;margin:0}
.muted{color:#94a3b8;font-size:12px}
.center{text-align:center}
.lk a{color:#7dd3fc;word-break:break-all;font-size:13px}
</style>
</head>
<body>
<div class="wrap">
<h1>🎮 Minecraft Panel v3</h1>
<div class="card">
  <div style="font-size:18px;font-weight:700"><span class="dot" id="dot"></span><span id="st">Check ho raha...</span></div>
  <div class="muted" id="tm"></div>
  <div class="muted" id="svc"></div>
</div>
<div class="card">
  <div style="font-weight:700;margin-bottom:6px">🌐 Panel Links</div>
  <div class="muted" style="margin-bottom:4px">Permanent (bookmark karo):</div>
  <div id="png" class="lk">check...</div>
  <div class="muted" style="margin:10px 0 4px">Backup (emergency — ye hamesha chalta hai):</div>
  <div id="pcf" class="lk">check...</div>
</div>
<div class="card center">
  <button class="b-start" onclick="ctl('start')">▶️ Start</button>
  <button class="b-stop" onclick="ctl('stop')">⏹️ Stop</button>
  <button class="b-restart" onclick="ctl('restart')">🔄 Restart</button>
</div>
<div class="card">
  <input id="cmd" placeholder="Command: say hello / time set day">
  <div style="margin-top:8px"><button class="b-send" onclick="send()">📨 Send Command</button></div>
</div>
<div class="card">
  <div style="font-weight:700;margin-bottom:8px">📜 Server Log (live)</div>
  <pre id="log">loading...</pre>
</div>
<div class="muted center">Auto-refresh 5 sec • Server chal raha hai to dot GREEN hoga</div>
</div>
<script>
async function refresh(){
 try{
  const s = await (await fetch('/api/status')).json();
  document.getElementById('dot').className = 'dot' + (s.running ? ' on' : '');
  document.getElementById('st').textContent = s.running ? 'Server ONLINE ✅' : 'Server OFFLINE ❌';
  document.getElementById('tm').textContent = 'Last check: ' + s.time;
  document.getElementById('svc').textContent = 'playit: ' + (s.playit ? '✅' : '❌') +
    ' | ngrok: ' + (s.ngrok ? '✅' : '❌') + ' | cloudflared: ' + (s.cloudflared ? '✅' : '❌') +
    ' | world backup: ' + (s.backup || '-');
  document.getElementById('png').innerHTML = s.url_ngrok
    ? ('<a href="' + s.url_ngrok + '">' + s.url_ngrok + '</a> ✅ live')
    : '⏳ abhi busy hai (purana session) — kuch nahi karna, khud LIVE ho jayega';
  document.getElementById('pcf').innerHTML = s.url_cf
    ? ('<a href="' + s.url_cf + '">' + s.url_cf + '</a> ✅ live')
    : '⏳ starting... (5-10 sec baad refresh hoga)';
  const l = await (await fetch('/api/log')).json();
  const el = document.getElementById('log');
  el.textContent = l.log;
  el.scrollTop = el.scrollHeight;
 }catch(e){
  document.getElementById('st').textContent = '⚠️ Panel error';
 }
}
async function ctl(c){
  if(c === 'stop' && !confirm('Server band karna hai?')) return;
  await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:c})});
  refresh();
}
async function send(){
  const v = document.getElementById('cmd').value;
  if(!v) return;
  await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:v})});
  document.getElementById('cmd').value = '';
  refresh();
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return PAGE

def proc_alive(name):
    try:
        return subprocess.run(['pgrep', '-x', name], capture_output=True).returncode == 0
    except Exception:
        return False

def proc_alive_f(pattern):
    try:
        return subprocess.run(['pgrep', '-f', pattern], capture_output=True).returncode == 0
    except Exception:
        return False

def read_file(name):
    try:
        return open(name, errors='ignore').read().strip()
    except Exception:
        return ''

@app.route('/api/status')
def status():
    backup = read_file('LAST_BACKUP') or '-'
    return jsonify({'running': is_running(),
                    'playit': proc_alive('playit'),
                    'ngrok': proc_alive('ngrok'),
                    'cloudflared': proc_alive_f('cloudflared'),
                    'backup': backup,
                    'url_ngrok': read_file('NGROK_URL'),
                    'url_cf': read_file('CF_URL'),
                    'time': datetime.now().strftime('%H:%M:%S')})

@app.route('/api/log')
def log():
    try:
        txt = open('server_console.log', errors='ignore').read()[-1500:]
    except Exception:
        txt = '(server_console.log abhi nahi hai)'
    return jsonify({'log': txt})

@app.route('/api/control', methods=['POST'])
def control():
    c = (request.json or {}).get('command', '')
    if c == 'start':
        threading.Thread(target=do_start, daemon=True).start()
    elif c == 'stop':
        do_stop()
    elif c == 'restart':
        threading.Thread(target=do_restart, daemon=True).start()
    return jsonify({'ok': True})

@app.route('/api/command', methods=['POST'])
def command():
    c = (request.json or {}).get('command', '')
    if c:
        subprocess.run(['screen', '-S', 'mcserver', '-X', 'stuff', c + '\n'])
    return jsonify({'ok': True})

app.run(host='0.0.0.0', port=8081, threaded=True)
