#!/usr/bin/env python3
# Proxy RTSP -> MJPEG HTTP/HTTPS para Raspberry Pi
# Requiere: pip install flask  y  ffmpeg instalado en el sistema
#
# Uso sin SSL:
#   python server.py --rtsp "rtsp://USUARIO:CLAVE@IP:554/stream1" --port 8080
#
# Uso con SSL (recomendado, ver README para setup con mkcert):
#   python server.py --rtsp "rtsp://USUARIO:CLAVE@IP:554/stream1" --port 8080 \
#     --cert /home/pi/certs/localhost.pem --key /home/pi/certs/localhost-key.pem

import subprocess
import threading
import argparse
from flask import Flask, Response

app = Flask(__name__)

frame_lock = threading.Lock()
current_frame = b''


def capture_frames(rtsp_url):
    global current_frame
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-f', 'image2pipe',
        '-vf', 'scale=640:360',
        '-r', '10',
        '-vcodec', 'mjpeg',
        '-q:v', '5',
        'pipe:1',
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    buf = b''
    while True:
        chunk = proc.stdout.read(4096)
        if not chunk:
            break
        buf += chunk
        while True:
            start = buf.find(b'\xff\xd8')
            end = buf.find(b'\xff\xd9')
            if start != -1 and end != -1 and end > start:
                with frame_lock:
                    current_frame = buf[start:end + 2]
                buf = buf[end + 2:]
            else:
                break


def generate_mjpeg():
    while True:
        with frame_lock:
            frame = current_frame
        if frame:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )


@app.route('/stream')
def stream():
    return Response(
        generate_mjpeg(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache, no-store',
        },
    )


@app.route('/')
def preview():
    return '<html><body style="margin:0;background:#000"><img src="/stream" style="width:100%"></body></html>'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rtsp', required=True, help='URL RTSP de la cámara')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--cert', default=None, help='Ruta al certificado SSL (.pem)')
    parser.add_argument('--key', default=None, help='Ruta a la clave privada SSL (.pem)')
    args = parser.parse_args()

    ssl_context = (args.cert, args.key) if args.cert and args.key else None
    proto = 'https' if ssl_context else 'http'

    t = threading.Thread(target=capture_frames, args=(args.rtsp,), daemon=True)
    t.start()

    print(f'Stream disponible en {proto}://localhost:{args.port}/stream')
    app.run(host='0.0.0.0', port=args.port, ssl_context=ssl_context)
