# api/websocket.py
import json
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import APIRouter

router = APIRouter()

# Conexiones WebSocket activas { sesion_id: [WebSocket, ...] }
conexiones: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/{sesion_id}")
async def websocket_endpoint(websocket: WebSocket, sesion_id: str):
    await websocket.accept()

    if sesion_id not in conexiones:
        conexiones[sesion_id] = []
    conexiones[sesion_id].append(websocket)

    print(f"[ws] Cliente conectado a sesión {sesion_id}")

    try:
        while True:
            # Mantener conexión viva esperando mensajes del cliente
            await websocket.receive_text()
    except WebSocketDisconnect:
        conexiones[sesion_id].remove(websocket)
        print(f"[ws] Cliente desconectado de sesión {sesion_id}")


async def notificar_alerta(alerta: dict):
    """
    Envía una alerta a todos los clientes conectados a esa sesión.
    Lo llama session_manager cuando detecta una keyword.
    """
    sesion_id = alerta.get("sesion_id")
    if not sesion_id or sesion_id not in conexiones:
        return

    mensaje = json.dumps(alerta, ensure_ascii=False)
    clientes_muertos = []

    for ws in conexiones[sesion_id]:
        try:
            await ws.send_text(mensaje)
        except Exception:
            clientes_muertos.append(ws)

    for ws in clientes_muertos:
        conexiones[sesion_id].remove(ws)