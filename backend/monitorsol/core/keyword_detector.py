# core/keyword_detector.py
import re

def detectar_keywords(transcripcion: str, keywords: list[str]) -> list[str]:
    """
    Compara la transcripción contra la lista de keywords.
    Busca palabra completa — evita falsos positivos como 
    'enamora' cuando la keyword es 'amor'.
    """
    texto = transcripcion.lower()
    encontradas = []

    for kw in keywords:
        kw_lower = kw.lower()
        # Si la keyword tiene más de una palabra, buscar frase exacta
        if ' ' in kw_lower:
            patron = re.escape(kw_lower)
        else:
            # Palabra completa con word boundaries
            patron = r'\b' + re.escape(kw_lower) + r'\b'
        
        if re.search(patron, texto):
            encontradas.append(kw)

    return encontradas