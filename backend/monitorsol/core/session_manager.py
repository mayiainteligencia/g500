# core/session_manager.py
import asyncio
import uuid
from datetime import datetime
from typing import Callable
from core.stream_capture import capturar_chunk, limpiar_chunk
from core.transcriber import transcribir
from core.keyword_detector import detectar_keywords
from db.testigos_repo import guardar_testigo

# Diccionario global de sesiones activas
# { sesion_id: { "task": asyncio.Task, "config": {...}, "activa": bool } }
sesiones_activas: dict = {}

async def iniciar_sesion(
    emisora_url: str,
    emisora_nombre: str,
    keywords: list[str],
    on_alerta: Callable  # callback async para notificar al WebSocket
) -> str:
    """
    Crea una nueva sesión de monitoreo y arranca el loop en background.
    Retorna el sesion_id.
    """
    sesion_id = str(uuid.uuid4())

    sesiones_activas[sesion_id] = {
        "activa": True,
        "emisora_url": emisora_url,
        "emisora_nombre": emisora_nombre,
        "keywords": keywords,
        "iniciada_en": datetime.now().isoformat(),
        "total_chunks": 0,
        "total_detecciones": 0,
    }

    task = asyncio.create_task(
        _loop_monitoreo(sesion_id, emisora_url, emisora_nombre, keywords, on_alerta)
    )
    sesiones_activas[sesion_id]["task"] = task

    print(f"[session_manager] Sesión iniciada: {sesion_id} → {emisora_nombre}")
    return sesion_id


async def detener_sesion(sesion_id: str) -> bool:
    """Detiene una sesión activa. Retorna True si existía."""
    if sesion_id not in sesiones_activas:
        return False

    sesiones_activas[sesion_id]["activa"] = False
    task = sesiones_activas[sesion_id].get("task")
    if task and not task.done():
        task.cancel()

    del sesiones_activas[sesion_id]
    print(f"[session_manager] Sesión detenida: {sesion_id}")
    return True


def obtener_sesiones() -> list:
    """Retorna info de todas las sesiones activas (sin el task object)."""
    result = []
    for sid, data in sesiones_activas.items():
        result.append({
            "sesion_id": sid,
            "emisora_url": data["emisora_url"],
            "emisora_nombre": data["emisora_nombre"],
            "keywords": data["keywords"],
            "iniciada_en": data["iniciada_en"],
            "total_chunks": data["total_chunks"],
            "total_detecciones": data["total_detecciones"],
        })
    return result


async def _loop_monitoreo(
    sesion_id: str,
    emisora_url: str,
    emisora_nombre: str,
    keywords: list[str],
    on_alerta: Callable
):
    """
    Loop principal: captura → transcribe → detecta → alerta → repite.
    Corre indefinidamente hasta que la sesión se detenga.
    """
    chunk_index = 0

    while sesiones_activas.get(sesion_id, {}).get("activa", False):
        audio_path = None
        try:
            # 1. Capturar chunk de audio
            audio_path = await capturar_chunk(emisora_url, sesion_id, chunk_index)
            sesiones_activas[sesion_id]["total_chunks"] += 1

            if not audio_path:
                print(f"[loop] Chunk vacío en sesión {sesion_id}, reintentando...")
                await asyncio.sleep(2)
                continue

            # 2. Transcribir (en executor para no bloquear el event loop)
            loop = asyncio.get_event_loop()
            transcripcion = await loop.run_in_executor(
                None, transcribir, audio_path, keywords
            )

            print(f"[loop] [{emisora_nombre}] chunk {chunk_index}: {transcripcion[:80]}...")

            # 3. Detectar keywords
            encontradas = detectar_keywords(transcripcion, keywords)

            # 4. Si hay match → guardar testigo y notificar
            if encontradas:
                timestamp = datetime.now().isoformat()
                sesiones_activas[sesion_id]["total_detecciones"] += len(encontradas)

                for kw in encontradas:
                    await guardar_testigo(
                        sesion_id=sesion_id,
                        emisora_url=emisora_url,
                        emisora_nombre=emisora_nombre,
                        keyword=kw,
                        transcripcion=transcripcion,
                        timestamp=timestamp
                    )

                    alerta = {
                        "sesion_id": sesion_id,
                        "emisora_nombre": emisora_nombre,
                        "keyword": kw,
                        "transcripcion": transcripcion,
                        "timestamp": timestamp
                    }
                    await on_alerta(alerta)

        except asyncio.CancelledError:
            print(f"[loop] Sesión {sesion_id} cancelada.")
            break
        except Exception as e:
            print(f"[loop] Error en sesión {sesion_id}: {e}")
            await asyncio.sleep(3)
        finally:
            limpiar_chunk(audio_path)
            chunk_index += 1