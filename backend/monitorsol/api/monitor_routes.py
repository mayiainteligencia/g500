# api/monitor_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.session_manager import (
    iniciar_sesion, detener_sesion, obtener_sesiones, sesiones_activas
)
from db.testigos_repo import obtener_testigos
from api.websocket import notificar_alerta
from config import MAX_SESIONES

router = APIRouter()

class IniciarRequest(BaseModel):
    emisora_url: str
    emisora_nombre: str = "Sin nombre"
    keywords: list[str]

class ExportRequest(BaseModel):
    sesion_id: str | None = None


@router.post("/start")
async def start_monitor(req: IniciarRequest):
    if len(sesiones_activas) >= MAX_SESIONES:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {MAX_SESIONES} sesiones simultáneas permitidas"
        )
    if not req.keywords:
        raise HTTPException(status_code=400, detail="Debes definir al menos una keyword")
    if not req.emisora_url:
        raise HTTPException(status_code=400, detail="URL de emisora requerida")

    sesion_id = await iniciar_sesion(
        emisora_url=req.emisora_url,
        emisora_nombre=req.emisora_nombre,
        keywords=req.keywords,
        on_alerta=notificar_alerta
    )
    return {"sesion_id": sesion_id, "status": "iniciada"}


@router.delete("/stop/{sesion_id}")
async def stop_monitor(sesion_id: str):
    ok = await detener_sesion(sesion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"sesion_id": sesion_id, "status": "detenida"}


@router.get("/sessions")
async def get_sessions():
    return {"sesiones": obtener_sesiones()}


@router.get("/testigos")
async def get_testigos(sesion_id: str | None = None):
    testigos = await obtener_testigos(sesion_id)
    return {"testigos": testigos, "total": len(testigos)}