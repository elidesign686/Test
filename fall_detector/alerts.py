"""Envío de alertas al celular cuando se detecta una caída.

Canales soportados:

- Telegram (recomendado, gratuito): envía un mensaje con la foto del momento
  de la caída a uno o varios chats. Solo necesitas crear un bot con @BotFather.
- Twilio (opcional, de pago): envía SMS o mensajes de WhatsApp.

Los envíos se hacen en un hilo aparte para no congelar el análisis de video.
"""

import datetime
import logging
import os
import threading
import time

import cv2
import requests

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, settings: dict):
        self.settings = settings or {}
        self.cooldown = self.settings.get("cooldown_seconds", 60)
        self.save_snapshots = self.settings.get("save_snapshots", True)
        self.snapshot_dir = self.settings.get("snapshot_dir", "capturas")
        self._last_alert: dict[str, float] = {}  # por cámara
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    def notify_fall(self, camera_name: str, frame, timestamp: float):
        """Envía la alerta si la cámara no está en periodo de enfriamiento."""
        with self._lock:
            last = self._last_alert.get(camera_name, 0)
            if time.time() - last < self.cooldown:
                logger.info(
                    "[%s] Caída detectada pero la alerta está en enfriamiento.", camera_name
                )
                return
            self._last_alert[camera_name] = time.time()

        when = datetime.datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y %H:%M:%S")
        message = (
            "🚨 ¡ALERTA DE CAÍDA!\n"
            f"Cámara: {camera_name}\n"
            f"Hora: {when}\n"
            "Se detectó que una persona cayó y permanece en el suelo. "
            "Verifica la situación de inmediato."
        )

        snapshot_path = self._save_snapshot(camera_name, frame, timestamp)
        threading.Thread(
            target=self._send_all, args=(message, snapshot_path), daemon=True
        ).start()

    # ------------------------------------------------------------------ #
    def _save_snapshot(self, camera_name: str, frame, timestamp: float) -> str | None:
        if not self.save_snapshots or frame is None:
            return None
        os.makedirs(self.snapshot_dir, exist_ok=True)
        stamp = datetime.datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in camera_name)
        path = os.path.join(self.snapshot_dir, f"caida_{safe_name}_{stamp}.jpg")
        cv2.imwrite(path, frame)
        logger.info("Captura guardada en %s", path)
        return path

    def _send_all(self, message: str, snapshot_path: str | None):
        tg = self.settings.get("telegram", {})
        if tg.get("enabled"):
            self._send_telegram(tg, message, snapshot_path)
        tw = self.settings.get("twilio", {})
        if tw.get("enabled"):
            self._send_twilio(tw, message)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _send_telegram(cfg: dict, message: str, snapshot_path: str | None):
        token = cfg.get("bot_token", "")
        chat_ids = cfg.get("chat_ids", [])
        if not token or "PON_AQUI" in token:
            logger.error("Telegram activado pero falta configurar bot_token.")
            return
        base = f"https://api.telegram.org/bot{token}"
        for chat_id in chat_ids:
            try:
                if snapshot_path and os.path.exists(snapshot_path):
                    with open(snapshot_path, "rb") as photo:
                        resp = requests.post(
                            f"{base}/sendPhoto",
                            data={"chat_id": chat_id, "caption": message},
                            files={"photo": photo},
                            timeout=20,
                        )
                else:
                    resp = requests.post(
                        f"{base}/sendMessage",
                        data={"chat_id": chat_id, "text": message},
                        timeout=20,
                    )
                if resp.ok:
                    logger.info("Alerta enviada por Telegram a %s", chat_id)
                else:
                    logger.error("Telegram respondió %s: %s", resp.status_code, resp.text)
            except requests.RequestException as exc:
                logger.error("Error enviando alerta por Telegram: %s", exc)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _send_twilio(cfg: dict, message: str):
        try:
            from twilio.rest import Client
        except ImportError:
            logger.error(
                "Twilio activado pero la librería no está instalada. "
                "Ejecuta: pip install twilio"
            )
            return
        try:
            client = Client(cfg.get("account_sid"), cfg.get("auth_token"))
            for number in cfg.get("to_numbers", []):
                client.messages.create(
                    body=message, from_=cfg.get("from_number"), to=number
                )
                logger.info("Alerta enviada por Twilio a %s", number)
        except Exception as exc:  # la API de Twilio lanza varios tipos de error
            logger.error("Error enviando alerta por Twilio: %s", exc)
