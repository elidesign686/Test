"""Vigilancia antirrobo para tiendas con alertas al celular.

Detecta con las cámaras de la tienda:
  - Personas dentro de la tienda fuera del horario (intrusión / posible robo)
  - Personas en zonas restringidas (mostrador, bodega, vitrinas)
  - Merodeo prolongado (comportamiento sospechoso)

Uso:
    python vigilancia_tienda.py                    # usa config_tienda.yaml
    python vigilancia_tienda.py -c mi_config.yaml
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
from fall_detector.tienda import VigilanciaTienda

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tienda")


def main():
    parser = argparse.ArgumentParser(description="Vigilancia antirrobo con alertas al celular")
    parser.add_argument("-c", "--config", default="config_tienda.yaml", help="Archivo de configuración")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    det_cfg = config.get("detection", {})
    store_cfg = config.get("store", {})
    show_video = config.get("display", {}).get("show_video", True)

    # Para la tienda basta el modelo de detección (no hace falta pose)
    model_name = det_cfg.get("model", "yolov8n.pt")
    logger.info("Cargando modelo %s (se descarga automáticamente la primera vez)...", model_name)
    model = YOLO(model_name)

    alert_manager = AlertManager(config.get("alerts", {}))

    settings = {**det_cfg, **store_cfg}
    cameras = []
    detectors = {}
    for cam_cfg in config.get("cameras", []):
        name = cam_cfg.get("name", f"Camara {len(cameras) + 1}")
        source = cam_cfg.get("source", 0)
        stream = CameraStream(name, source).start()
        cameras.append(stream)
        detectors[name] = VigilanciaTienda(name, model, settings, cam_cfg.get("zones"))
        logger.info("Cámara registrada: %s (%s, %d zonas restringidas)",
                    name, source, len(detectors[name].zones))

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

    logger.info("Vigilancia de tienda iniciada. Ctrl+C (o 'q' en la ventana) para salir.")

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
                    logger.warning("[%s] %s", event.camera_name, event.mensaje.splitlines()[0])
                    alert_manager.notify(
                        key=f"{event.camera_name}/{event.tipo}",
                        camera_name=event.camera_name,
                        frame=event.frame,
                        timestamp=event.timestamp,
                        body=event.mensaje,
                    )

                if show_video:
                    cv2.imshow(f"Vigilancia tienda - {stream.name}", annotated)

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
