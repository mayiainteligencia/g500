# db/models.py
CREATE_TABLE_TESTIGOS = """
CREATE TABLE IF NOT EXISTS testigos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id TEXT NOT NULL,
    emisora_url TEXT NOT NULL,
    emisora_nombre TEXT,
    keyword_detectada TEXT NOT NULL,
    transcripcion TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""