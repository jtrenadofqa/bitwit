#!/bin/bash

# Este script inicia la API y ngrok, obtiene la URL y configura el webhook de Telegram automáticamente.

# --- Cargar las variables de entorno del archivo .env ---
source .env
# --------------------------------------------------------


function cleanup {
  echo "Terminando procesos..."
  kill $API_PID
  kill $NGROK_PID
}

trap cleanup EXIT

echo "Iniciando el servidor de la API en una nueva pestaña..."
konsole --new-tab --title="BitWit API" --hold -e "python api_server.py" &
API_PID=$!

echo "Iniciando ngrok en una nueva pestaña..."
konsole --new-tab --title="ngrok Tunnel" --hold -e "ngrok http 5000" &
NGROK_PID=$!

# Esperar unos segundos para que ngrok inicie y el túnel se establezca
echo "Esperando a que ngrok se inicie..."
sleep 10

# Obtener la URL de ngrok de forma programática
NGROK_URL=$(python ./get_ngrok_url.py)

if [ -z "$NGROK_URL" ]; then
    echo "Error: No se pudo obtener la URL de ngrok. Asegúrate de que ngrok está funcionando." >&2
    exit 1
fi

# Configurar el webhook de Telegram usando la URL obtenida y la variable de entorno
echo "Configurando el webhook de Telegram con la URL: ${NGROK_URL}/telegram-webhook"
curl "https://api.telegram.org/bot${TELEGRAM_BITWIT_TOKEN}/setWebhook?url=${NGROK_URL}/telegram-webhook"

echo "Todos los servicios se han iniciado y configurado."
echo "Presiona Ctrl+C para detenerlos."

wait