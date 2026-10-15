# db/testigos_repo.py
import aiosqlite
from db.models import CREATE_TABLE_TESTIGOS
from config import DB_PATH
import os

async def init_db():
    os.makedirs("db", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_TESTIGOS)
        await db.commit()

async def guardar_testigo(sesion_id: str, emisora_url: str, emisora_nombre: str,
                           keyword: str, transcripcion: str, timestamp: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO testigos 
            (sesion_id, emisora_url, emisora_nombre, keyword_detectada, transcripcion, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sesion_id, emisora_url, emisora_nombre, keyword, transcripcion, timestamp))
        await db.commit()

async def obtener_testigos(sesion_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if sesion_id:
            cursor = await db.execute(
                "SELECT * FROM testigos WHERE sesion_id = ? ORDER BY creado_en DESC",
                (sesion_id,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM testigos ORDER BY creado_en DESC"
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]