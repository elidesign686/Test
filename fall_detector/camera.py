"""Lectura de cámaras en hilos independientes.

Cada cámara (RTSP, HTTP, webcam o archivo) se lee en su propio hilo y siempre
se conserva únicamente el cuadro más reciente, para que el análisis nunca se
quede atrás respecto al video en vivo.
"""

import logging
import threading
import time

import cv2

logger = logging.getLogger(__name__)


class CameraStream:
    """Lector de video con reconexión automática (importante para RTSP)."""

    RECONNECT_DELAY = 5  # segundos entre intentos de reconexión

    def __init__(self, name: str, source):
        self.name = name
        self.source = source
        self._frame = None
        self._lock = threading.Lock()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.connected = False

    def start(self):
        self._thread.start()
        return self

    def _open(self):
        cap = cv2.VideoCapture(self.source)
        # Buffer mínimo: queremos el cuadro más reciente, no video atrasado
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _run(self):
        # Los archivos de video se reproducen una sola vez, sin reconexión
        is_file = isinstance(self.source, str) and not self.source.lower().startswith(
            ("rtsp://", "http://", "https://")
        )
        while not self._stopped.is_set():
            cap = self._open()
            if not cap.isOpened():
                cap.release()
                self.connected = False
                logger.warning(
                    "[%s] No se pudo conectar a la cámara. Reintentando en %ss...",
                    self.name,
                    self.RECONNECT_DELAY,
                )
                if is_file:
                    break
                time.sleep(self.RECONNECT_DELAY)
                continue

            self.connected = True
            logger.info("[%s] Cámara conectada.", self.name)

            while not self._stopped.is_set():
                ok, frame = cap.read()
                if not ok:
                    break
                with self._lock:
                    self._frame = frame

            cap.release()
            self.connected = False
            if is_file:
                logger.info("[%s] Fin del archivo de video.", self.name)
                break
            logger.warning("[%s] Se perdió la conexión. Reconectando...", self.name)
            time.sleep(self.RECONNECT_DELAY)

    def read(self):
        """Devuelve el cuadro más reciente (o None si aún no hay)."""
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def stop(self):
        self._stopped.set()
        self._thread.join(timeout=3)
