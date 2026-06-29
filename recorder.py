#!/usr/bin/env python3
"""
Grabador de cámara IP para Control Stock Tekron.

Se conecta al servidor por WebSocket y espera comandos start/stop.
Al recibir "start", lanza FFmpeg apuntando al RTSP de la cámara y
transmite el video directamente al servidor (sin guardar en el Pi).

Uso:
  python recorder.py \
    --rtsp "rtsp://usuario:clave@192.168.x.x:554/stream1" \
    --server "wss://control.tekron.com.ar"

Para desarrollo local:
  python recorder.py --rtsp "rtsp://..." --server "ws://localhost:8090"
"""

import asyncio
import subprocess
import argparse
import json
import sys
import websockets


async def stream_to_server(session_id: int, rtsp_url: str, server_base: str):
    """Lanza FFmpeg y envía el output al WebSocket del servidor."""
    ws_url = f"{server_base}/ws/sessions/{session_id}/video2"
    cmd = [
        'ffmpeg',
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,
        '-f', 'webm',
        '-vcodec', 'libvpx',
        '-b:v', '500k',
        '-r', '10',
        '-an',
        'pipe:1',
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        async with websockets.connect(ws_url) as ws:
            print(f"  Transmitiendo sesión {session_id} → {ws_url}")
            loop = asyncio.get_event_loop()
            while True:
                chunk = await loop.run_in_executor(None, proc.stdout.read, 65536)
                if not chunk:
                    break
                await ws.send(chunk)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"  Error transmitiendo: {e}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"  Grabación sesión {session_id} detenida")


async def control_loop(rtsp_url: str, server_base: str):
    """Mantiene la conexión de control con el servidor y ejecuta comandos."""
    ws_url = f"{server_base}/ws/recorder"
    video_task = None

    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20) as ws:
                print(f"Conectado al servidor: {server_base}")
                async for message in ws:
                    try:
                        cmd = json.loads(message)
                    except json.JSONDecodeError:
                        continue

                    action = cmd.get("action")
                    session_id = cmd.get("session_id")

                    if action == "start" and session_id:
                        if video_task and not video_task.done():
                            video_task.cancel()
                            try:
                                await video_task
                            except asyncio.CancelledError:
                                pass
                        print(f"Iniciando grabación sesión {session_id}")
                        video_task = asyncio.create_task(
                            stream_to_server(session_id, rtsp_url, server_base)
                        )

                    elif action == "stop":
                        if video_task and not video_task.done():
                            video_task.cancel()
                            try:
                                await video_task
                            except asyncio.CancelledError:
                                pass
                        print("Grabación detenida por el servidor")

        except (websockets.ConnectionClosed, OSError) as e:
            print(f"Desconectado ({e}), reintentando en 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Error inesperado: {e}, reintentando en 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grabador cámara IP para Control Stock Tekron")
    parser.add_argument('--rtsp', required=True, help='URL RTSP de la cámara (rtsp://user:pass@IP:554/stream1)')
    parser.add_argument('--server', required=True, help='URL base del servidor (wss://control.tekron.com.ar)')
    args = parser.parse_args()

    print(f"Grabador iniciado")
    print(f"  RTSP: {args.rtsp}")
    print(f"  Servidor: {args.server}")

    try:
        asyncio.run(control_loop(args.rtsp, args.server))
    except KeyboardInterrupt:
        print("Grabador detenido")
        sys.exit(0)
