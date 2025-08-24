import requests
import sys

def get_ngrok_url():
    try:
        # Hace una petición a la API local de ngrok
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        response.raise_for_status() # Lanza un error para códigos de respuesta HTTP incorrectos
        tunnels = response.json().get("tunnels", [])
        
        # Encuentra la URL que usa HTTPS
        for tunnel in tunnels:
            if tunnel.get("proto") == "https":
                return tunnel.get("public_url")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la URL de ngrok: {e}", file=sys.stderr)
    return None

if __name__ == "__main__":
    url = get_ngrok_url()
    if url:
        # Imprime la URL a la salida estándar para que el script de bash la pueda capturar
        print(url)
    else:
        sys.exit(1)