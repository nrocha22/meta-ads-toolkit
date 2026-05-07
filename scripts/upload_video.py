#!/usr/bin/env python3
"""Sube video a Meta, espera procesamiento, devuelve video_id."""

import json
import sys
import time
import os
import requests
from pathlib import Path
from helpers import get_account, get_access_token, strip_account_flag, PROJECT_DIR, API_BASE_URL

BASE_URL = API_BASE_URL


def upload_video(video_path, title, ad_account_id, access_token):
    """Sube video a la Media Library del ad account. Retorna video_id."""
    url = f"{BASE_URL}/{ad_account_id}/advideos"

    with open(video_path, "rb") as f:
        files = {"source": (os.path.basename(video_path), f, "video/mp4")}
        data = {
            "title": title,
            "access_token": access_token,
        }
        sys.stderr.write(f"  Subiendo {os.path.basename(video_path)} ({os.path.getsize(video_path) / 1024 / 1024:.1f} MB)...\n")
        response = requests.post(url, files=files, data=data)

    if response.status_code != 200:
        sys.stderr.write(f"  Error upload: {response.status_code}\n")
        sys.stderr.write(f"  {response.text}\n")
        sys.exit(1)

    result = response.json()
    video_id = result.get("id")
    if not video_id:
        sys.stderr.write(f"  Error: respuesta sin video ID: {result}\n")
        sys.exit(1)

    sys.stderr.write(f"  Upload OK. Video ID: {video_id}\n")
    return video_id


def check_video_status(video_id, access_token):
    """Consulta estado de procesamiento del video."""
    url = f"{BASE_URL}/{video_id}"
    params = {
        "fields": "status,title",
        "access_token": access_token,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return "error"

    data = response.json()
    status = data.get("status", {})
    if isinstance(status, dict):
        return status.get("video_status", "unknown")
    return str(status)


def wait_for_processing(video_id, access_token, interval=5, timeout=300):
    """Espera a que el video termine de procesarse. Retorna True si ready."""
    sys.stderr.write(f"  Esperando procesamiento")
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            sys.stderr.write(f"\n  Timeout ({timeout}s). Video aún procesando.\n")
            return False

        status = check_video_status(video_id, access_token)
        if status == "ready":
            sys.stderr.write(f"\n  Video listo ({elapsed:.0f}s)\n")
            return True
        elif status in ("error", "failed"):
            sys.stderr.write(f"\n  Error de procesamiento: {status}\n")
            return False

        sys.stderr.write(".")
        sys.stderr.flush()
        time.sleep(interval)


def main():
    args = strip_account_flag(sys.argv)
    acct = get_account()
    access_token = get_access_token()

    if not args:
        print("Uso: python upload_video.py --account <name> <video_path> [title]")
        print("")
        print("Sube video, espera procesamiento, devuelve video_id (JSON a stdout).")
        print("")
        print("Ejemplo:")
        print("  python upload_video.py --account mibrand ./videos/mi-video.mp4 'Mi Video'")
        sys.exit(1)

    video_path = args[0]
    title = args[1] if len(args) > 1 else Path(video_path).stem

    # Validar archivo
    if not os.path.isfile(video_path):
        sys.stderr.write(f"Error: archivo no encontrado: {video_path}\n")
        sys.exit(1)

    sys.stderr.write(f"\n  Upload Video — {acct['label']}\n")
    sys.stderr.write(f"  {'─'*40}\n")
    sys.stderr.write(f"  Archivo: {video_path}\n")
    sys.stderr.write(f"  Título:  {title}\n")
    sys.stderr.write(f"  Cuenta:  {acct['ad_account_id']}\n")
    sys.stderr.write(f"  {'─'*40}\n\n")

    # 1. Upload
    video_id = upload_video(video_path, title, acct["ad_account_id"], access_token)

    # 2. Esperar procesamiento
    success = wait_for_processing(video_id, access_token, interval=5, timeout=300)

    if not success:
        sys.stderr.write(f"\n  Video subido pero no procesado aún.\n")
        sys.stderr.write(f"  ID: {video_id} — puedes verificar más tarde.\n")

    # JSON a stdout
    output = {
        "video_id": video_id,
        "title": title,
        "status": "ready" if success else "processing",
        "account": acct["ad_account_id"],
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
