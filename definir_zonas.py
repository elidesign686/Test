"""Herramienta para dibujar zonas restringidas con el mouse.

Muestra el video de la cámara; haz clic en las esquinas de la zona que quieres
proteger (mostrador, bodega, vitrina...) y al terminar te imprime el bloque
YAML listo para pegar en config_tienda.yaml.

Controles:
    Clic izquierdo  -> agregar un punto a la zona actual
    n               -> terminar la zona actual y empezar otra
    z               -> borrar el último punto
    q               -> salir e imprimir el YAML de todas las zonas

Uso:
    python definir_zonas.py                # webcam
    python definir_zonas.py "rtsp://usuario:clave@IP:554/stream1"
"""

import sys

import cv2
import numpy as np

COLOR = (255, 120, 0)


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else 0
    try:
        source = int(source)
    except (TypeError, ValueError):
        pass

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"No se pudo abrir la cámara: {source}")
        sys.exit(1)

    zones: list[list[tuple]] = []
    current: list[tuple] = []

    def on_mouse(event, x, y, *_):
        if event == cv2.EVENT_LBUTTONDOWN:
            current.append((x, y))
            print(f"  Punto agregado: [{x}, {y}]")

    window = "Definir zonas (clic=punto, n=nueva zona, z=deshacer, q=salir)"
    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)

    print("Haz clic en las esquinas de la zona a proteger. 'q' para terminar.")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Se perdió el video de la cámara.")
            break

        for zone in zones:
            pts = np.array(zone, dtype=np.int32)
            cv2.polylines(frame, [pts], True, COLOR, 2)
        if len(current) > 1:
            cv2.polylines(frame, [np.array(current, dtype=np.int32)], False, COLOR, 2)
        for x, y in current:
            cv2.circle(frame, (x, y), 4, COLOR, -1)

        cv2.imshow(window, frame)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("n") and len(current) >= 3:
            zones.append(current.copy())
            current.clear()
            print("Zona guardada. Empieza la siguiente o presiona 'q'.")
        elif key == ord("z") and current:
            removed = current.pop()
            print(f"  Punto eliminado: {list(removed)}")

    if len(current) >= 3:
        zones.append(current)

    cap.release()
    cv2.destroyAllWindows()

    if not zones:
        print("No se definió ninguna zona.")
        return

    print("\nPega esto dentro de tu cámara en config_tienda.yaml:\n")
    print("    zones:")
    for i, zone in enumerate(zones, start=1):
        points = ", ".join(f"[{x}, {y}]" for x, y in zone)
        print(f'      - name: "Zona {i}"')
        print(f"        points: [{points}]")
        print("        seconds: 3")


if __name__ == "__main__":
    main()
