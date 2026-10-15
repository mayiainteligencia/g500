# MonitorSol

Servicio de transcripción de radio en vivo. FastAPI + Whisper + WebSocket.
Es la única pieza del sistema que necesita infraestructura corriendo.

```bash
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
brew install ffmpeg                       # binario del sistema, obligatorio
venv/bin/python -m uvicorn main:app --port 8001
```

Verificado funcionando el 2026-08-13: transcribe MVS Noticias 102.5 FM en vivo,
23 chunks en 60 s, con el modelo `base` de Whisper.

---

## ⚠ Sólo hay bytecode, no código fuente

Lo que está versionado son **11 archivos `.pyc` compilados**, no `.py`. Funcionan
—Python 3 importa módulos sin fuente y el magic number (3531) coincide con el
Python 3.12.3 del venv— pero eso trae tres problemas:

1. **No se puede leer ni revisar.** Lo que sabemos del comportamiento salió de
   desensamblar el bytecode y de probar los endpoints a mano.
2. **No se puede corregir.** Los desajustes de contrato que están más abajo se
   arreglan del lado del frontend o no se arreglan.
3. **Se rompe al cambiar de Python.** Un `.pyc` de 3.12 no carga en 3.13. Si
   alguien actualiza el intérprete, el servicio deja de importar.

**Hace falta el `.py` original.** Debería estar en la máquina donde se
desarrolló. Los `.pyc` quedan versionados mientras tanto porque perderlos sería
peor, no porque sea la forma correcta de guardar esto.

---

## Estructura

| archivo | qué hace (deducido del bytecode) |
|---|---|
| `main.pyc` | App FastAPI. `GET /health` y monta los routers bajo `/monitor`. |
| `config.pyc` | `PUERTO=8001`, `MODELO_WHISPER='base'`, `DB_PATH='db/testigos.sqlite'`, `CHUNK_SEGUNDOS`, `MAX_SESIONES` |
| `api/monitor_routes.pyc` | `/start`, `/stop/{id}`, `/sessions`, `/testigos` |
| `api/websocket.pyc` | `/ws/{sesion_id}` y `notificar_alerta()` |
| `core/session_manager.pyc` | Loop: captura → transcribe → detecta → alerta |
| `core/stream_capture.pyc` | Baja el chunk de audio del stream |
| `core/transcriber.pyc` | Llama a Whisper |
| `core/keyword_detector.pyc` | Busca las palabras clave en el texto |
| `db/testigos_repo.pyc` | Guarda cada detección |
| `db/testigos.sqlite` | 437 registros reales de sesiones anteriores |

El venv (388 MB, con torch) está en `.gitignore`.

---

## API real, medida contra el servidor corriendo

| método | ruta | respuesta |
|---|---|---|
| `GET` | `/health` | `{"status":"ok","servicio":"monitorsol"}` |
| `POST` | `/monitor/start` | `{"sesion_id":"…","status":"iniciada"}` |
| `DELETE` | `/monitor/stop/{sesion_id}` | 404 si no existe |
| `GET` | `/monitor/sessions` | `{"sesiones":[…]}` |
| `GET` | `/monitor/testigos` | `{…}` con 437 registros |
| `WS` | `/ws/{sesion_id}` | sólo alertas, ver abajo |

Objeto de sesión que devuelve `/monitor/sessions`:

```json
{ "sesion_id": "…", "emisora_url": "…", "emisora_nombre": "…",
  "keywords": [...], "iniciada_en": "2026-08-13T03:43:08",
  "total_chunks": 23, "total_detecciones": 0 }
```

Mensaje que empuja el WebSocket:

```json
{ "sesion_id": "…", "emisora_nombre": "…", "keyword": "campeche",
  "transcripcion": "…", "timestamp": "2026-08-13T03:46:07" }
```

---

## Desajustes con el frontend

Cinco, medidos contra el servidor corriendo. **Ninguno está corregido**: el
frontend no se tocó a la espera de decidir de qué lado se arregla cada uno.

| # | qué | frontend espera | backend entrega | efecto |
|---|---|---|---|---|
| 1 | Detener sesión | `POST /monitor/stop/{id}` | sólo `DELETE` | **405.** La UI cree que detuvo; la sesión sigue viva consumiendo el stream |
| 2 | Estado de sesión | lee `s.status` | no existe el campo | La comparación con `'stopped'` nunca se cumple |
| 3 | Discriminador de mensaje | `data.tipo === 'alerta'` | no manda `tipo` | **Todo mensaje del WS se descarta en silencio** |
| 4 | Nombre de la keyword | `data.keyword_detectada` | `data.keyword` | Llegaría `undefined` |
| 5 | Transcripción en vivo | `{tipo:'transcripcion', texto}` | nunca se envía | El panel de transcripción queda vacío para siempre |

El 3 y el 5 son los graves: **con el backend funcionando perfectamente, la
pantalla no muestra nada.** El WebSocket conecta, los mensajes llegan, y el
`if (data.tipo === …)` los tira todos porque ese campo no existe.

El 5 además no es un desajuste de nombres sino de diseño: el backend sólo
notifica cuando hay coincidencia de palabra clave. La transcripción continua
existe —se ve en el log del servidor— pero no sale por el socket.

### Cómo se arreglaría

- **1, 2, 3 y 4** se arreglan en el frontend en unos minutos: cambiar el verbo
  a `DELETE`, dejar de depender de `status`, y leer los campos que sí llegan en
  vez de un `tipo` inexistente.
- **5** necesita tocar el backend: que `_loop_monitoreo` empuje también cada
  chunk transcrito, no sólo las alertas. Eso requiere el código fuente.

Alternativa sin backend: que el frontend consulte `/monitor/sessions` cada pocos
segundos y muestre el avance de `total_chunks`. Da actividad visible pero no el
texto, que es justo lo que hace valiosa la pantalla.
