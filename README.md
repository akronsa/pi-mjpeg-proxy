# pi-mjpeg-proxy

Dos servicios para Raspberry Pi que trabajan en conjunto con [Control Stock Tekron](https://github.com/akronsa):

- **`server.py`** — proxy RTSP → HTTP MJPEG para mostrar el stream en vivo en el browser
- **`recorder.py`** — grabador que se conecta al servidor por WebSocket y transmite el video de la cámara IP directamente al servidor cuando hay una sesión activa

## Requisitos

```bash
sudo apt update
sudo apt install ffmpeg python3-venv
```

## Instalación

```bash
git clone https://github.com/akronsa/pi-mjpeg-proxy.git
cd pi-mjpeg-proxy

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso manual

### Proxy MJPEG (preview en pantalla)

```bash
source venv/bin/activate
python server.py --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" --port 8080
```

El stream queda disponible en `http://localhost:8080/stream`.

### Grabador

```bash
source venv/bin/activate
python recorder.py \
  --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" \
  --server "wss://control.tekron.com.ar"
```

El grabador reconecta automáticamente si se cae la conexión al servidor.

### Tapo C100

Activar **cámara local** en la app Tapo antes de usar la URL RTSP.

### Chromium en modo kiosk (HTTPS + stream HTTP local)

El proxy MJPEG corre en HTTP (`localhost:8080`). Si el sitio principal usa HTTPS, Chromium bloquea el contenido mixto. Usar el flag `--unsafely-treat-insecure-origin-as-secure` apuntando al origen del proxy:

```bash
chromium-browser \
  --kiosk \
  --unsafely-treat-insecure-origin-as-secure=http://localhost:8080 \
  https://control.tekron.com.ar
```

---

## Inicio automático con systemd

### 1. Crear el servicio del proxy MJPEG

```bash
sudo nano /etc/systemd/system/mjpeg-proxy.service
```

Contenido (reemplazá `USUARIO`, `CLAVE` e `IP_CAMARA`):

```ini
[Unit]
Description=MJPEG Proxy para cámara IP
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/pi-mjpeg-proxy
ExecStart=/home/pi/pi-mjpeg-proxy/venv/bin/python server.py --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Crear el servicio del grabador

```bash
sudo nano /etc/systemd/system/mjpeg-recorder.service
```

Contenido:

```ini
[Unit]
Description=Grabador cámara IP para Control Stock Tekron
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/pi-mjpeg-proxy
ExecStart=/home/pi/pi-mjpeg-proxy/venv/bin/python recorder.py --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" --server "wss://control.tekron.com.ar"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Habilitar e iniciar los servicios

```bash
sudo systemctl daemon-reload

sudo systemctl enable mjpeg-proxy
sudo systemctl enable mjpeg-recorder

sudo systemctl start mjpeg-proxy
sudo systemctl start mjpeg-recorder
```

### Comandos útiles

```bash
# Ver estado
sudo systemctl status mjpeg-proxy
sudo systemctl status mjpeg-recorder

# Ver logs en vivo
journalctl -u mjpeg-proxy -f
journalctl -u mjpeg-recorder -f

# Reiniciar
sudo systemctl restart mjpeg-proxy
sudo systemctl restart mjpeg-recorder
```
