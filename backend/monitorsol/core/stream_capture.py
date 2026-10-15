# core/stream_capture.py
import asyncio
import os
import tempfile
from config import CHUNK_SEGUNDOS

async def capturar_chunk(url: str, sesion_id: str, chunk_index: int) -> str | None:
    """
    Captura CHUNK_SEGUNDOS de audio desde una URL de stream
    y lo guarda como archivo WAV temporal.
    Retorna la ruta del archivo o None si falló.
    """
    # Asegurar que el directorio temporal local existe
    tmp_dir = os.path.join(os.getcwd(), "temp_chunks")
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir, exist_ok=True)
    
    output_path = os.path.join(tmp_dir, f"chunk_{sesion_id}_{chunk_index}.wav")

    cmd = [
        "ffmpeg",
        "-y",
        "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "-tls_verify", "0",
        "-i", url,
        "-t", str(CHUNK_SEGUNDOS),
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        output_path,
        "-loglevel", "error"
    ]

    import subprocess

    def run_ffmpeg():
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=CHUNK_SEGUNDOS + 15
        )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_ffmpeg)

        if result.returncode != 0:
            err_msg = result.stderr.decode()
            print(f"[stream_capture] Error ffmpeg (código {result.returncode}) en sesión {sesion_id}: {err_msg}")
            return None

        if not os.path.exists(output_path):
            print(f"[stream_capture] El archivo no se creó: {output_path}")
            return None
            
        if os.path.getsize(output_path) == 0:
            print(f"[stream_capture] El archivo está vacío (0 bytes): {output_path}")
            return None

        return output_path

    except asyncio.TimeoutError:
        print(f"[stream_capture] Timeout capturando chunk {chunk_index} sesion {sesion_id}")
        try:
            proc.kill()
        except:
            pass
        return None
    except Exception as e:
        import traceback
        print(f"[stream_capture] Excepción detallada en sesión {sesion_id}:")
        traceback.print_exc()
        return None

def limpiar_chunk(path: str):
    """Elimina el archivo WAV temporal después de transcribirlo."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass