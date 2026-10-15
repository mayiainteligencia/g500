#!/bin/bash
# ============================================
# CEREBRO ELECTORAL — Servidor Local
# ============================================
# Haz doble clic en este archivo para arrancar
# el servidor y abrir la plataforma en el navegador.
# ============================================

cd "$(dirname "$0")/frontend"

# Verificar que Python 3 esté disponible
if ! command -v python3 &> /dev/null; then
  osascript -e 'display alert "Cerebro Electoral" message "Necesitas Python 3 instalado para correr el servidor local. Descárgalo desde python.org"'
  exit 1
fi

# Matar cualquier servidor previo en el mismo puerto
lsof -ti :8080 | xargs kill -9 2>/dev/null

# Arrancar servidor en background
python3 -m http.server 8080 &
SERVER_PID=$!

# Esperar un momento para que arranque
sleep 1

# Abrir el navegador
open "http://localhost:8080/index.html"

echo "============================================"
echo "  Cerebro Electoral — Servidor activo"
echo "  URL: http://localhost:8080"
echo "  PID: $SERVER_PID"
echo "  Cierra esta ventana para detener el servidor."
echo "============================================"

# Mantener el servidor vivo hasta que se cierre la terminal
wait $SERVER_PID
