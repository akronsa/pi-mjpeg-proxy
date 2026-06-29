# pi-mjpeg-proxy

Dos servicios para Raspberry Pi que trabajan en conjunto con [Control Stock Tekron](https://github.com/akronsa):

- **`server.py`** — proxy RTSP → HTTPS MJPEG para mostrar el stream en vivo en el browser
- **`recorder.py`** — grabador que se conecta al servidor por WebSocket y transmite el video de la cámara IP directamente al servidor cuando hay una sesión activa

## Requisitos

```bash
sudo apt update
sudo apt install ffmpeg python3-venv mkcert
```

## Instalación

```bash
git clone https://github.com/akronsa/pi-mjpeg-proxy.git
cd pi-mjpeg-proxy

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Certificado SSL para localhost (mkcert)

El proxy corre en `localhost` y el sitio principal usa HTTPS. Para evitar que Chromium bloquee el stream por contenido mixto, generamos un certificado local confiable con mkcert.

```bash
# Instalar la CA local de mkcert en el sistema y en Chromium
mkcert -install

# Crear los certificados para localhost
mkdir -p /home/pi/certs
mkcert -cert-file /home/pi/certs/localhost.pem \
       -key-file  /home/pi/certs/localhost-key.pem \
       localhost 127.0.0.1
```

Esto crea dos archivos:
- `/home/pi/certs/localhost.pem` — certificado
- `/home/pi/certs/localhost-key.pem` — clave privada

El certificado es reconocido automáticamente por Chromium sin flags adicionales.

## Uso manual

### Proxy MJPEG con HTTPS

```bash
source venv/bin/activate
python server.py \
  --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" \
  --port 8080 \
  --cert /home/pi/certs/localhost.pem \
  --key  /home/pi/certs/localhost-key.pem
```

El stream queda disponible en `https://localhost:8080/stream`.

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

### Chromium en modo kiosk

Con el certificado de mkcert instalado no se necesita ningún flag adicional:

```bash
chromium \
  --kiosk \
  https://control.tekron.com.ar
```

> Si no usás mkcert y querés correr el proxy en HTTP, agregar:
> `--unsafely-treat-insecure-origin-as-secure=http://localhost:8080`

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
ExecStart=/home/pi/pi-mjpeg-proxy/venv/bin/python server.py \
  --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" \
  --port 8080 \
  --cert /home/pi/certs/localhost.pem \
  --key  /home/pi/certs/localhost-key.pem
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
ExecStart=/home/pi/pi-mjpeg-proxy/venv/bin/python recorder.py \
  --rtsp "rtsp://USUARIO:CLAVE@IP_CAMARA:554/stream1" \
  --server "wss://control.tekron.com.ar"
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
