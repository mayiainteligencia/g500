# core/transcriber.py
import whisper
from config import MODELO_WHISPER

_modelo = None

def get_modelo():
    global _modelo
    if _modelo is None:
        print(f"[transcriber] Cargando modelo Whisper '{MODELO_WHISPER}'...")
        _modelo = whisper.load_model(MODELO_WHISPER)
        print(f"[transcriber] Modelo listo.")
    return _modelo

def transcribir(audio_path: str, keywords: list[str]) -> str:
    modelo = get_modelo()

    # Prompt con contexto de radio mexicana + keywords
    keywords_str = ", ".join(keywords) if keywords else ""
    prompt = (
        "Transcripción de radio mexicana en español. "
        "Locutor hablando en español claro. "
        f"Palabras clave a detectar: {keywords_str}. "
        "No uses otros idiomas."
    )

    resultado = modelo.transcribe(
        audio_path,
        language="es",
        initial_prompt=prompt,
        fp16=False,
        no_speech_threshold=0.6,   # descarta audio sin voz clara
        condition_on_previous_text=False,  # evita que "alucine" continuando texto anterior
        temperature=0.0,           # más determinista, menos creativo
    )

    texto = resultado["text"].strip()
    return texto