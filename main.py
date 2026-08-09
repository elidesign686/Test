"""Sistema de detección de caídas para cámaras de vigilancia.

Detecta personas con YOLOv8-pose en una o varias cámaras (RTSP/HTTP/webcam),
identifica caídas (persona horizontal que permanece en el suelo) y envía
alertas al celular por Telegram y/o Twilio con la foto del momento.

Uso:
    python main.py                 # usa config.yaml
    python main.py -c mi_config.yaml
"""

import argparse
import logging
import signal
import sys
import time

import cv2
import yaml
from ultralytics import YOLO

from fall_detector.alerts import AlertManager
from fall_detector.camera import CameraStream
from fall_detector.detector import FallDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Detección de caídas con alertas al celular")
    parser.add_argument("-c", "--config", default="config.yaml", help="Archivo de configuración")
    args = parser.parse_args()

    config = load_config(args.config)
    det_cfg = config.get("detection", {})
    display_cfg = config.get("display", {})
    show_video = display_cfg.get("show_video", True)

    model_name = det_cfg.get("model", "yolov8n-pose.pt")
    logger.info("Cargando modelo %s (se descarga automáticamente la primera vez)...", model_name)
    model = YOLO(model_name)

    alert_manager = AlertManager(config.get("alerts", {}))

    cameras = []
    detectors = {}
    for cam_cfg in config.get("cameras", []):
        name = cam_cfg.get("name", f"Camara {len(cameras) + 1}")
        source = cam_cfg.get("source", 0)
        stream = CameraStream(name, source).start()
        cameras.append(stream)
        detectors[name] = FallDetector(name, model, det_cfg)
        logger.info("Cámara registrada: %s (%s)", name, source)

    if not cameras:
        logger.error("No hay cámaras configuradas en %s", args.config)
        sys.exit(1)

    frame_skip = max(1, int(det_cfg.get("frame_skip", 1)))
    counter = 0
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    logger.info("Sistema iniciado. Presiona Ctrl+C (o 'q' en la ventana) para salir.")

    try:
        while running:
            counter += 1
            processed_any = False
            for stream in cameras:
                frame = stream.read()
                if frame is None:
                    continue
                processed_any = True
                if counter % frame_skip != 0:
                    continue

                annotated, events = detectors[stream.name].process(frame)
                for event in events:
                    logger.warning("[%s] ¡CAÍDA DETECTADA! Enviando alerta...", event.camera_name)
                    alert_manager.notify_fall(event.camera_name, event.frame, event.timestamp)

                if show_video:
                    cv2.imshow(f"Deteccion de caidas - {stream.name}", annotated)

            if show_video:
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            elif not processed_any:
                time.sleep(0.05)
    finally:
        logger.info("Deteniendo cámaras...")
        for stream in cameras:
            stream.stop()
        cv2.destroyAllWindows()
        logger.info("Sistema detenido.")


if __name__ == "__main__":
    main()
