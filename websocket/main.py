from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi import Body
from datetime import datetime, timezone
import asyncio, json, os, base64, hmac, hashlib, time, gzip, uuid

import redis.asyncio as redis  # pip install redis

app = FastAPI()

# ----------------------------
# Config
# ----------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APP_SECRET = os.getenv("APP_SECRET", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))  # 1 hour
ONLINE_TTL_SECONDS = 25  # presence TTL in redis (renewed by heartbeat)
PUBSUB_CHANNEL = "chat:global:v1"

INSTANCE_ID = os.getenv("INSTANCE_ID", str(uuid.uuid4())[:8])

# Demo users (replace with a real DB + hashed passwords in production)
USERS = {
    "ali": "1234",
    "sara": "1234",
    "admin": "admin",
}

r: redis.Redis | None = None

# local connected clients: username -> websocket
local_clients: dict[str, WebSocket] = {}

# ----------------------------
# Helpers
# ----------------------------
def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))

def sign_token(username: str, exp_unix: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "exp": exp_unix}

    h = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    msg = f"{h}.{p}".encode("utf-8")

    sig = hmac.new(APP_SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
    s = b64url(sig)
    return f"{h}.{p}.{s}"

def verify_token(token: str) -> str:
    try:
        h, p, s = token.split(".")
        msg = f"{h}.{p}".encode("utf-8")
        expected = hmac.new(APP_SECRET.encode("utf-8"), msg, hashlib.sha256).digest()
        if not hmac.compare_digest(b64url_decode(s), expected):
            raise ValueError("bad signature")

        payload = json.loads(b64url_decode(p).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        username = str(payload.get("sub", "")).strip()
        if not username:
            raise ValueError("missing sub")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def validate_username(u: str) -> bool:
    if not (3 <= len(u) <= 24):
        return False
    for ch in u:
        if not (ch.isalnum() or ch in "_-"):
            return False
    return True

# ----------------------------
# Wire protocol (binary frames)
# mode byte:
#   0 = UTF-8 JSON bytes
#   1 = GZIP(UTF-8 JSON bytes)
# ----------------------------
def encode_frame(payload: dict, compress: bool = False) -> bytes:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if compress and len(raw) >= 200:
        return bytes([1]) + gzip.compress(raw)
    return bytes([0]) + raw

def decode_frame(data: bytes) -> dict:
    if not data:
        raise ValueError("empty frame")
    mode = data[0]
    body = data[1:]
    if mode == 1:
        body = gzip.decompress(body)
    return json.loads(body.decode("utf-8"))

async def ws_send(ws: WebSocket, payload: dict, compress: bool = False):
    await ws.send_bytes(encode_frame(payload, compress=compress))

# ----------------------------
# Redis presence keys
# ----------------------------
def online_key(username: str) -> str:
    return f"online:{username}"

async def set_online(username: str):
    # Set a TTL presence marker. If key already exists, user is "already online somewhere".
    # We allow reconnect by overwriting (reliability), but we still keep a single online slot.
    await r.set(online_key(username), INSTANCE_ID, ex=ONLINE_TTL_SECONDS)

async def refresh_online(username: str):
    await r.expire(online_key(username), ONLINE_TTL_SECONDS)

async def del_online(username: str):
    await r.delete(online_key(username))

async def list_online_users() -> list[str]:
    # Scan keys online:* (fine for small projects; for large scale use a Redis Set instead)
    users = []
    async for key in r.scan_iter("online:*"):
        try:
            u = key.decode("utf-8").split("online:", 1)[1]
            users.append(u)
        except Exception:
            pass
    return sorted(users)

# ----------------------------
# Pub/Sub broadcast helpers
# ----------------------------
async def publish(payload: dict):
    # Always add server timestamp
    payload.setdefault("ts", iso_now())
    await r.publish(PUBSUB_CHANNEL, json.dumps(payload, separators=(",", ":")))

async def broadcast_local(payload: dict):
    dead = []
    msg = encode_frame(payload, compress=True)
    for u, ws in local_clients.items():
        try:
            await ws.send_bytes(msg)
        except Exception:
            dead.append(u)
    for u in dead:
        local_clients.pop(u, None)

async def send_presence_to_local():
    users = await list_online_users()
    await broadcast_local({"type": "presence", "users": users, "ts": iso_now()})

# ----------------------------
# Startup: connect Redis + start pubsub listener
# ----------------------------
@app.on_event("startup")
async def startup():
    global r
    r = redis.from_url(REDIS_URL, decode_responses=False)

    # background task: listen for messages and forward to local clients
    async def listener():
        pubsub = r.pubsub()
        await pubsub.subscribe(PUBSUB_CHANNEL)
        try:
            async for msg in pubsub.listen():
                if msg is None or msg.get("type") != "message":
                    continue
                data = msg.get("data")
                if not data:
                    continue
                try:
                    payload = json.loads(data.decode("utf-8"))
                    await broadcast_local(payload)
                except Exception:
                    continue
        finally:
            try:
                await pubsub.unsubscribe(PUBSUB_CHANNEL)
            except Exception:
                pass
            try:
                await pubsub.close()
            except Exception:
                pass

    asyncio.create_task(listener())

@app.on_event("shutdown")
async def shutdown():
    if r is not None:
        await r.close()

# ----------------------------
# HTTP: Login endpoint (username+password -> token)
# ----------------------------
@app.post("/login")
async def login(data: dict = Body(...)):
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    if not validate_username(username):
        raise HTTPException(status_code=400, detail="Username must be 3–24 chars (letters/numbers/_/-).")

    if USERS.get(username) != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    exp = int(time.time()) + TOKEN_TTL_SECONDS
    token = sign_token(username, exp)
    return {"token": token, "exp": exp}

# ----------------------------
# UI
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Realtime Chat</title>
<style>
  :root{
    --bg:#0b1220; --card:rgba(255,255,255,.06); --border:rgba(255,255,255,.14);
    --text:rgba(255,255,255,.92); --muted:rgba(255,255,255,.68);
    --shadow:0 20px 60px rgba(0,0,0,.45); --r:18px;
    --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444;
    --me:rgba(99,102,241,.95); --other:rgba(255,255,255,.10); --otherBorder:rgba(255,255,255,.16);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
    color:var(--text);
    background:
      radial-gradient(1200px 600px at 20% 10%, rgba(99,102,241,0.35), transparent 55%),
      radial-gradient(900px 500px at 85% 25%, rgba(34,197,94,0.22), transparent 55%),
      radial-gradient(1000px 700px at 60% 110%, rgba(245,158,11,0.18), transparent 55%),
      var(--bg);
    display:grid; place-items:center; padding:18px;
  }
  .app{width:min(1100px,100%); display:grid; grid-template-columns:340px 1fr; gap:16px}
  @media (max-width: 900px){ .app{grid-template-columns:1fr} }
  .card{
    background:var(--card); border:1px solid var(--border); border-radius:var(--r);
    box-shadow:var(--shadow); overflow:hidden; backdrop-filter: blur(10px);
    min-height: 580px; display:flex; flex-direction:column;
  }
  .header{
    padding:16px 18px; display:flex; justify-content:space-between; align-items:center; gap:12px;
    border-bottom:1px solid var(--border);
    background: linear-gradient(180deg, rgba(255,255,255,.06), transparent);
  }
  .title{display:flex; flex-direction:column; gap:2px; min-width:0}
  .title h1{font-size:16px; margin:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
  .title p{font-size:12px; margin:0; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
  .pill{
    display:inline-flex; align-items:center; gap:8px; padding:6px 10px; border-radius:999px;
    font-size:12px; background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.12); color:var(--muted);
  }
  .dot{width:9px;height:9px;border-radius:999px;background:var(--warn); box-shadow:0 0 0 4px rgba(245,158,11,.15)}
  .pill.ok .dot{background:var(--ok); box-shadow:0 0 0 4px rgba(34,197,94,.15)}
  .pill.bad .dot{background:var(--bad); box-shadow:0 0 0 4px rgba(239,68,68,.15)}
  .content{padding:16px 18px; display:grid; gap:14px}
  .field label{display:block; font-size:12px; color:var(--muted); margin-bottom:8px}
  input[type="text"], input[type="password"]{
    width:100%; padding:12px; border-radius:12px;
    border:1px solid rgba(255,255,255,.14);
    background:rgba(0,0,0,.25); color:var(--text); outline:none;
  }
  input:focus{border-color: rgba(99,102,241,.55); background: rgba(0,0,0,.35)}
  .row{display:flex; gap:10px; align-items:center; flex-wrap:wrap}
  .btn{
    padding:11px 12px; border-radius:12px; border:1px solid rgba(255,255,255,.14);
    background:rgba(255,255,255,.08); color:var(--text); cursor:pointer; font-weight:600; font-size:13px;
  }
  .btn:hover{background:rgba(255,255,255,.12)}
  .btn:disabled{opacity:.5; cursor:not-allowed}
  .btn.primary{background:rgba(99,102,241,.35); border-color:rgba(99,102,241,.55)}
  .btn.primary:hover{background:rgba(99,102,241,.45)}
  .btn.danger{background:rgba(239,68,68,.20); border-color:rgba(239,68,68,.35)}
  .btn.danger:hover{background:rgba(239,68,68,.28)}
  .hint{font-size:12px; color:var(--muted); line-height:1.4}
  .users{display:flex; flex-wrap:wrap; gap:8px}
  .tag{
    font-size:12px; padding:6px 10px; border-radius:999px;
    background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12);
  }
  .tag.me{background: rgba(99,102,241,.25); border-color: rgba(99,102,241,.45)}
  .chat{
    padding:16px; overflow:auto; flex:1; display:flex; flex-direction:column; gap:10px;
    background: radial-gradient(700px 420px at 30% 0%, rgba(255,255,255,0.05), transparent 60%), rgba(0,0,0,0.12);
  }
  .msg{max-width:78%; display:flex; flex-direction:column; gap:4px}
  .bubble{
    padding:10px 12px; border-radius:16px; border:1px solid var(--otherBorder);
    background:var(--other); font-size:14px; line-height:1.35; white-space:pre-wrap; word-wrap:break-word;
  }
  .meta{font-size:11px; color:var(--muted); padding-left:6px}
  .me{align-self:flex-end}
  .me .bubble{background:var(--me); border-color:rgba(255,255,255,.12)}
  .me .meta{text-align:right; padding-right:6px; padding-left:0}
  .system{align-self:center; max-width:92%}
  .system .bubble{
    background:rgba(255,255,255,.06); border-color:rgba(255,255,255,.10); font-size:12px;
    border-radius:999px; padding:8px 12px;
  }
  .composer{
    display:grid; grid-template-columns: 1fr auto; gap:10px;
    padding:14px 16px; border-top:1px solid var(--border);
    background: linear-gradient(0deg, rgba(255,255,255,.06), transparent);
  }
</style>
</head>
<body>
<div class="app">
  <section class="card">
    <div class="header">
      <div class="title">
        <h1>Secure Realtime Chat</h1>
        <p>Redis Pub/Sub • gzip frames • token auth</p>
      </div>
      <div id="statusPill" class="pill bad">
        <span class="dot"></span><span id="statusText">Offline</span>
      </div>
    </div>

    <div class="content">
      <div class="field">
        <label>Username</label>
        <input id="username" type="text" placeholder="ali" maxlength="24" />
      </div>
      <div class="field">
        <label>Password</label>
        <input id="password" type="password" placeholder="••••" />
      </div>

      <div class="row">
        <button id="loginBtn" class="btn primary" onclick="doLogin()">Login</button>
        <button id="logoutBtn" class="btn danger" onclick="logout()" disabled>Logout</button>
        <button id="reconnectBtn" class="btn" onclick="reconnect()" disabled>Reconnect</button>
      </div>

      <div class="hint" id="connHint">Login to join. (Demo users: ali/1234, sara/1234)</div>

      <div class="field">
        <label>Online users</label>
        <div id="users" class="users"></div>
      </div>

      <div class="hint">Send with Enter • Newline with Shift+Enter</div>
    </div>
  </section>

  <section class="card">
    <div class="header">
      <div class="title">
        <h1>Room</h1>
        <p>Server timestamps • online/offline presence</p>
      </div>
      <button class="btn" onclick="clearChat()">Clear</button>
    </div>

    <div id="chat" class="chat" aria-live="polite"></div>

    <div class="composer">
      <input id="msg" type="text" placeholder="Type a message..." disabled />
      <button id="sendBtn" class="btn primary" onclick="sendMsg()" disabled>Send</button>
    </div>
  </section>
</div>

<script>
  let ws = null;
  let token = "";
  let authed = false;
  let myUser = "";
  let heartbeatTimer = null;

  const el = (id) => document.getElementById(id);

  function setStatus(state, text) {
    const pill = el("statusPill");
    pill.classList.remove("ok", "bad");
    pill.classList.add(state === "ok" ? "ok" : "bad");
    el("statusText").textContent = text;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[c]));
  }

  function formatTime(iso) {
    try { return new Date(iso).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"}); }
    catch { return ""; }
  }

  function addMessage({ kind="other", text="", meta="" }) {
    const chat = el("chat");
    const wrap = document.createElement("div");
    wrap.className = "msg " + kind;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = escapeHtml(text);
    wrap.appendChild(bubble);

    if (meta) {
      const m = document.createElement("div");
      m.className = "meta";
      m.textContent = meta;
      wrap.appendChild(m);
    }
    chat.appendChild(wrap);
    chat.scrollTop = chat.scrollHeight;
  }

  function addSystem(text) { addMessage({ kind: "system", text }); }

  function renderUsers(users) {
    const box = el("users");
    box.innerHTML = "";
    if (!users || users.length === 0) {
      const d = document.createElement("div");
      d.className = "hint";
      d.textContent = "No one online.";
      box.appendChild(d);
      return;
    }
    users.forEach(u => {
      const t = document.createElement("div");
      t.className = "tag" + (u === myUser ? " me" : "");
      t.textContent = u + (u === myUser ? " (you)" : "");
      box.appendChild(t);
    });
  }

  function syncUI() {
    el("loginBtn").disabled = authed;
    el("logoutBtn").disabled = !authed;
    el("reconnectBtn").disabled = authed || !token;
    el("username").disabled = authed;
    el("password").disabled = authed;

    el("msg").disabled = !authed;
    el("sendBtn").disabled = !authed;

    el("connHint").textContent = authed ? "Online. Messages are live." : "Login to join. (Demo users: ali/1234, sara/1234)";
  }

  // ---- gzip frame protocol matching server ----
  async function encodeFrame(obj) {
    const jsonStr = JSON.stringify(obj);
    const raw = new TextEncoder().encode(jsonStr);

    // If CompressionStream exists, gzip larger payloads
    const canGzip = ("CompressionStream" in window) && raw.length >= 200;

    if (canGzip) {
      const cs = new CompressionStream("gzip");
      const compressedStream = new Blob([raw]).stream().pipeThrough(cs);
      const compressed = new Uint8Array(await new Response(compressedStream).arrayBuffer());

      const out = new Uint8Array(1 + compressed.length);
      out[0] = 1;
      out.set(compressed, 1);
      return out.buffer;
    } else {
      const out = new Uint8Array(1 + raw.length);
      out[0] = 0;
      out.set(raw, 1);
      return out.buffer;
    }
  }

  async function decodeFrame(arrayBuffer) {
    const data = new Uint8Array(arrayBuffer);
    const mode = data[0];
    let body = data.slice(1);

    if (mode === 1 && ("DecompressionStream" in window)) {
      const ds = new DecompressionStream("gzip");
      const decompressedStream = new Blob([body]).stream().pipeThrough(ds);
      body = new Uint8Array(await new Response(decompressedStream).arrayBuffer());
    }
    const text = new TextDecoder().decode(body);
    return JSON.parse(text);
  }

  function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = setInterval(async () => {
      if (!ws || ws.readyState !== 1) return;
      ws.send(await encodeFrame({ type: "ping" }));
    }, 8000);
  }
  function stopHeartbeat() {
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }

  async function connectSocket() {
    const scheme = (location.protocol === "https:") ? "wss" : "ws";
    const url = `${scheme}://${location.host}/ws?token=${encodeURIComponent(token)}`;
    ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";

    setStatus("bad", "Connecting…");
    syncUI();

    ws.onopen = () => {
      setStatus("bad", "Authorizing…");
    };

    ws.onmessage = async (e) => {
      const payload = await decodeFrame(e.data);

      if (payload.type === "auth_ok") {
        authed = true;
        myUser = payload.username;
        setStatus("ok", "Online");
        addSystem(`Logged in as ${myUser}`);
        syncUI();
        startHeartbeat();
        el("msg").focus();
        return;
      }

      if (payload.type === "auth_error") {
        authed = false;
        setStatus("bad", "Offline");
        addSystem(payload.message || "Auth failed");
        syncUI();
        try { ws.close(); } catch {}
        return;
      }

      if (payload.type === "presence") {
        renderUsers(payload.users || []);
        return;
      }

      if (payload.type === "user_join") { addSystem(`${payload.username} joined`); return; }
      if (payload.type === "user_leave") { addSystem(`${payload.username} left`); return; }

      if (payload.type === "chat") {
        const isMine = payload.username === myUser;
        addMessage({
          kind: isMine ? "me" : "other",
          text: `${payload.username}: ${payload.message}`,
          meta: formatTime(payload.ts)
        });
        return;
      }

      if (payload.type === "error") { addSystem(payload.message || "Server error"); }
    };

    ws.onerror = () => {
      setStatus("bad", "Network error");
      addSystem("Network error");
      syncUI();
    };

    ws.onclose = () => {
      const wasAuthed = authed;
      authed = false;
      setStatus("bad", "Offline");
      if (wasAuthed) addSystem("Disconnected");
      stopHeartbeat();
      syncUI();
    };
  }

  async function doLogin() {
    const u = (el("username").value || "").trim();
    const p = (el("password").value || "").trim();
    if (!u || !p) { addSystem("Enter username and password."); return; }

    // Basic client validation; server enforces too
    if (!/^[A-Za-z0-9_\\-]{3,24}$/.test(u)) {
      addSystem("Username must be 3–24 chars (letters/numbers/_/-).");
      return;
    }

    try {
      const res = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");
      token = data.token;
      addSystem("Login OK. Connecting…");
      await connectSocket();
      syncUI();
    } catch (err) {
      addSystem(String(err.message || err));
    }
  }

  function logout() {
    try { ws?.close(); } catch {}
    ws = null;
    authed = false;
    myUser = "";
    renderUsers([]);
    setStatus("bad", "Offline");
    stopHeartbeat();
    syncUI();
  }

  async function reconnect() {
    if (!token) { addSystem("No token. Login first."); return; }
    addSystem("Reconnecting…");
    await connectSocket();
  }

  async function sendMsg() {
    if (!ws || ws.readyState !== 1 || !authed) return;
    const input = el("msg");
    const msg = (input.value || "").trim();
    if (!msg) return;

    ws.send(await encodeFrame({ type: "chat", message: msg }));
    input.value = "";
    input.focus();
  }

  function clearChat() {
    el("chat").innerHTML = "";
    addSystem("Chat cleared");
  }

  el("msg").addEventListener("keydown", async (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      await sendMsg();
    }
  });

  setStatus("bad", "Offline");
  addSystem("Welcome! Login to join.");
  syncUI();
</script>
</body>
</html>
"""

# ----------------------------
# WebSocket endpoint
# ----------------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    username = None

    # Token is passed as query param: /ws?token=...
    token = ws.query_params.get("token", "")
    try:
        username = verify_token(token)
    except HTTPException:
        await ws_send(ws, {"type": "auth_error", "message": "Invalid or expired token"}, compress=False)
        await ws.close()
        return

    # Register locally
    local_clients[username] = ws

    # Mark online globally (Redis TTL)
    await set_online(username)

    # Notify client + broadcast join + presence
    await ws_send(ws, {"type": "auth_ok", "username": username, "ts": iso_now()}, compress=True)
    await publish({"type": "user_join", "username": username})
    await publish({"type": "presence", "users": await list_online_users()})

    try:
        while True:
            data = await ws.receive()
            if "bytes" not in data or data["bytes"] is None:
                # ignore non-binary frames for this protocol
                continue

            try:
                msg = decode_frame(data["bytes"])
            except Exception:
                await ws_send(ws, {"type": "error", "message": "Bad frame/JSON"}, compress=False)
                continue

            mtype = msg.get("type")

            if mtype == "ping":
                # refresh presence TTL
                await refresh_online(username)
                await ws_send(ws, {"type": "pong", "ts": iso_now()}, compress=False)

            elif mtype == "chat":
                text = (msg.get("message") or "").strip()
                if not text:
                    continue
                # publish chat (server timestamp added in publish)
                await publish({"type": "chat", "username": username, "message": text})

            else:
                await ws_send(ws, {"type": "error", "message": "Unknown message type"}, compress=False)

    except WebSocketDisconnect:
        pass
    except Exception:
        # basic reliability/error handling
        try:
            await ws_send(ws, {"type": "error", "message": "Server error"}, compress=False)
        except Exception:
            pass
    finally:
        # cleanup
        if username:
            if local_clients.get(username) is ws:
                local_clients.pop(username, None)
            await del_online(username)
            await publish({"type": "user_leave", "username": username})
            await publish({"type": "presence", "users": await list_online_users()})
