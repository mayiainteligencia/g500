import asyncio
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from db.testigos_repo import init_db
from api.monitor_routes import router as monitor_router
from api.websocket import router as ws_router

# Configuración necesaria para procesos secundarios en Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("[main] Base de datos inicializada.")
    yield
    print("[main] Apagando servicio.")

app = FastAPI(title="MonitorSol", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(monitor_router, prefix="/monitor")
app.include_router(ws_router)

@app.get("/health")
async def health():
    return {"status": "ok", "servicio": "monitorsol"}