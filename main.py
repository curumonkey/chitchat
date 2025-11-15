import time
import json
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()


# --- Connection management ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)


manager = ConnectionManager()


# --- Inline HTML + JS client ---
html = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>FastAPI WebSocket Chat</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet" />
  <style>
    body { background: #0b0f19; color: #e6edf3; font-family: 'Segoe UI', sans-serif; }
    .card { background: #11162a; border: 1px solid #24314f; border-radius: 12px; }
    .form-control, .btn { border-radius: 8px; }
    .chat-bubble { padding: 10px 14px; border-radius: 12px; margin-bottom: 8px; max-width: 80%; word-wrap: break-word; }
    .message-you { background-color: #1e2a4a; align-self: flex-end; color: #9cdcfe; text-align: right; }
    .message-other { background-color: #24314f; align-self: flex-start; color: #c3d2ff; text-align: left; }
    .chat-container { display: flex; flex-direction: column; gap: 6px; }
    .small { color: #9aa3b0; }
    .status-badge { font-size: 0.8rem; padding: 4px 8px; border-radius: 6px; }
    .connected { background-color: #198754; }
    .disconnected { background-color: #dc3545; }
    .error { background-color: #ffc107; color: #000; }
  </style>
</head>
<body>
<div class="container py-4">
  <div class="row justify-content-center">
    <div class="col-12 col-md-10 col-lg-8">
      <div class="card p-4">
        <h1 class="h4 mb-2">FastAPI WebSocket Chat</h1>
        <div class="d-flex justify-content-between align-items-center mb-3">
          <div class="small">Your ID: <span id="clientId"></span></div>
          <div id="status" class="status-badge disconnected">Connecting...</div>
        </div>

        <div id="messages" class="chat-container mb-3" style="min-height: 200px;"></div>

        <form id="chatForm" class="d-flex gap-2" onsubmit="sendMessage(event)">
          <input type="text" class="form-control" id="messageText" placeholder="Type a message..." autocomplete="off" />
          <button class="btn btn-outline-primary" type="submit">Send</button>
        </form>
      </div>
    </div>
  </div>
</div>

<script>
  const clientId = Date.now();
  document.getElementById("clientId").textContent = clientId;

  const wsUrl = `ws://${location.host}/ws/${clientId}`;
  const ws = new WebSocket(wsUrl);

  const statusEl = document.getElementById("status");
  const messagesEl = document.getElementById("messages");
  const inputEl = document.getElementById("messageText");

  ws.onopen = () => {
    updateStatus("Connected", "connected");
    inputEl.focus();
  };

  ws.onclose = () => updateStatus("Disconnected", "disconnected");
  ws.onerror = () => updateStatus("Error", "error");

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const isYou = data.client_id === clientId;
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${isYou ? "message-you" : "message-other"}`;
    bubble.innerHTML = `<strong>${data.client_id}</strong> <span class="small">${data.timestamp}</span><br>${data.message}`;
    messagesEl.appendChild(bubble);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  };

  function sendMessage(event) {
    event.preventDefault();
    const value = inputEl.value.trim();
    if (!value || ws.readyState !== WebSocket.OPEN) return;
    ws.send(value);
    inputEl.value = "";
    inputEl.focus();
  }

  function updateStatus(text, className) {
    statusEl.textContent = text;
    statusEl.className = `status-badge ${className}`;
  }

  setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send("__ping__");
    }
  }, 25000);
</script>
</body>
</html>
"""


# --- Routes ---
@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "__ping__":
                continue
            timestamp = time.strftime("%H:%M")
            payload = json.dumps({
                "client_id": client_id,
                "timestamp": timestamp,
                "message": data
            })
            await manager.broadcast(payload)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# --- Dev entrypoint ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
