"""Prueba rápida de alertas: envía un mensaje de prueba a tu celular.

Úsalo para verificar que Telegram/Twilio están bien configurados en
config.yaml ANTES de poner el sistema a funcionar con las cámaras.

Uso:
    python probar_alerta.py
    python probar_alerta.py -c mi_config.yaml
"""

import argparse
import logging
import sys
import time

import numpy as np
import cv2
import yaml

from fall_detector.alerts import AlertManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Envía una alerta de prueba al celular")
    parser.add_argument("-c", "--config", default="config.yaml", help="Archivo de configuración")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    alerts_cfg = config.get("alerts", {})
    tg = alerts_cfg.get("telegram", {})
    tw = alerts_cfg.get("twilio", {})

    if not tg.get("enabled") and not tw.get("enabled"):
        print("❌ Ningún canal de alertas está activado en config.yaml.")
        print("   Activa telegram.enabled: true y configura bot_token y chat_ids.")
        sys.exit(1)

    if tg.get("enabled") and "PON_AQUI" in str(tg.get("bot_token", "")):
        print("❌ Telegram está activado pero falta el bot_token en config.yaml.")
        print("   1. Escribe a @BotFather en Telegram y crea un bot con /newbot")
        print("   2. Escribe a @userinfobot para obtener tu chat_id")
        print("   3. Pega ambos en config.yaml y vuelve a ejecutar este script")
        sys.exit(1)

    # Imagen de prueba que simula la captura de una caída
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(frame, "IMAGEN DE PRUEBA", (140, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.putText(frame, "Si ves esto en tu celular,", (140, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, "las alertas funcionan :)", (140, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    print("📤 Enviando alerta de prueba a tu celular...")
    manager = AlertManager(alerts_cfg)
    manager.notify_fall("PRUEBA (no es una caida real)", frame, time.time())

    # El envío corre en un hilo aparte; le damos tiempo a terminar
    time.sleep(10)
    print()
    print("✅ Listo. Revisa tu celular:")
    print("   - Telegram: debe llegarte un mensaje del bot con la imagen de prueba.")
    print("   - Si no llega, verifica que le enviaste /start a tu bot y que el")
    print("     chat_id es correcto. Revisa los mensajes de error de arriba.")


if __name__ == "__main__":
    main()
