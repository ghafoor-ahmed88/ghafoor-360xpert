# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>FastAPI WebSocket Chat</title>
</head>
<body>
<h1>FastAPI WebSocket Chat</h1>
<form onsubmit="sendMessage(event)">
    <input type="text" id="messageText" autocomplete="off"/>
    <button>Send</button>
</form>
<ul id="messages"></ul>

<script>
    const ws = new WebSocket("ws://127.0.0.1:8000/ws");

    ws.onopen = () => console.log("Connected to WebSocket");

    ws.onmessage = function(event) {
        const messages = document.getElementById('messages');
        const li = document.createElement('li');
        li.textContent = event.data;
        messages.appendChild(li);
    };

    function sendMessage(event) {
        const input = document.getElementById("messageText");
        if(input.value.trim() !== "") {
            ws.send(input.value);
            input.value = '';
        }
        event.preventDefault();
    }
</script>
</body>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Message: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("A client left the chat")