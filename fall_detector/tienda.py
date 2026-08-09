"""Vigilancia antirrobo para tiendas.

Con las mismas cámaras del sistema de caídas, este módulo detecta las
situaciones de riesgo de robo que sí son detectables de forma fiable:

1. **Intrusión fuera de horario**: cualquier persona dentro de la tienda
   cuando está cerrada dispara una alerta inmediata.
2. **Zonas restringidas**: alguien entra a una zona prohibida para clientes
   (detrás del mostrador, bodega, vitrina de valor) y permanece unos segundos.
3. **Merodeo**: una persona permanece demasiado tiempo casi sin moverse
   (comportamiento típico previo a un hurto o a la espera de descuido).

Nota honesta: ningún sistema de visión detecta con fiabilidad el momento en
que alguien esconde un producto; estas tres señales son las que usan los
sistemas comerciales de prevención de pérdidas.
"""

import datetime
import math
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

COLOR_OK = (0, 200, 0)
COLOR_WARN = (0, 165, 255)
COLOR_ALERT = (0, 0, 255)
COLOR_ZONE = (255, 120, 0)


@dataclass
class PersonaTienda:
    """Estado temporal de una persona rastreada en la tienda."""

    centroid: tuple
    last_seen: float
    first_seen: float
    positions: list = field(default_factory=list)  # (tiempo, x, y) para merodeo
    zone_since: dict = field(default_factory=dict)  # nombre de zona -> tiempo de entrada
    alerted_zones: set = field(default_factory=set)
    alerted_loiter: bool = False
    alerted_after_hours: bool = False


@dataclass
class EventoTienda:
    camera_name: str
    tipo: str        # "intrusion", "zona", "merodeo"
    mensaje: str
    frame: np.ndarray
    timestamp: float


def _parse_time(text: str) -> datetime.time:
    hours, minutes = str(text).split(":")
    return datetime.time(int(hours), int(minutes))


class VigilanciaTienda:
    """Detector antirrobo para una cámara. Mantiene el estado entre cuadros."""

    MAX_TRACK_DISTANCE = 150
    TRACK_TIMEOUT = 3.0

    def __init__(self, camera_name: str, model, settings: dict, zones: list | None = None):
        self.camera_name = camera_name
        self.model = model
        self.confidence = settings.get("confidence", 0.5)

        after = settings.get("after_hours", {})
        self.after_hours_enabled = after.get("enabled", False)
        self.open_time = _parse_time(after.get("open_time", "09:00"))
        self.close_time = _parse_time(after.get("close_time", "21:00"))

        loiter = settings.get("loitering", {})
        self.loiter_enabled = loiter.get("enabled", False)
        self.loiter_seconds = loiter.get("seconds", 120)
        self.loiter_radius = loiter.get("radius", 80)

        self.zones = []
        for zone in zones or []:
            points = np.array(zone.get("points", []), dtype=np.int32)
            if len(points) >= 3:
                self.zones.append(
                    {
                        "name": zone.get("name", "Zona restringida"),
                        "points": points,
                        "seconds": zone.get("seconds", 3),
                    }
                )

        self._people: dict[int, PersonaTienda] = {}
        self._next_id = 0

    # ------------------------------------------------------------------ #
    def _store_is_closed(self) -> bool:
        if not self.after_hours_enabled:
            return False
        now = datetime.datetime.now().time()
        if self.open_time <= self.close_time:
            # Horario normal, p. ej. 09:00 - 21:00
            return not (self.open_time <= now < self.close_time)
        # Horario que cruza medianoche, p. ej. abre 22:00 y cierra 06:00
        return self.close_time <= now < self.open_time

    def _match_person(self, centroid: tuple, now: float) -> int:
        best_id, best_dist = None, self.MAX_TRACK_DISTANCE
        for pid, state in self._people.items():
            dist = math.dist(centroid, state.centroid)
            if dist < best_dist:
                best_id, best_dist = pid, dist
        if best_id is None:
            best_id = self._next_id
            self._next_id += 1
            self._people[best_id] = PersonaTienda(
                centroid=centroid, last_seen=now, first_seen=now
            )
        state = self._people[best_id]
        state.centroid = centroid
        state.last_seen = now
        return best_id

    def _forget_stale(self, now: float):
        stale = [pid for pid, s in self._people.items() if now - s.last_seen > self.TRACK_TIMEOUT]
        for pid in stale:
            del self._people[pid]

    def _is_loitering(self, state: PersonaTienda, now: float) -> bool:
        """¿La persona lleva mucho tiempo casi sin moverse?"""
        if not self.loiter_enabled:
            return False
        state.positions = [
            p for p in state.positions if now - p[0] <= self.loiter_seconds
        ]
        if not state.positions:
            return False
        t_first = state.positions[0][0]
        if now - t_first < self.loiter_seconds:
            return False
        xs = [p[1] for p in state.positions]
        ys = [p[2] for p in state.positions]
        spread = math.dist((min(xs), min(ys)), (max(xs), max(ys)))
        return spread <= self.loiter_radius * 2

    # ------------------------------------------------------------------ #
    def process(self, frame: np.ndarray) -> tuple[np.ndarray, list[EventoTienda]]:
        """Analiza un cuadro. Devuelve el cuadro anotado y los eventos."""
        now = time.monotonic()
        events: list[EventoTienda] = []
        annotated = frame
        closed = self._store_is_closed()

        # Dibujar las zonas restringidas
        for zone in self.zones:
            cv2.polylines(annotated, [zone["points"]], True, COLOR_ZONE, 2)
            zx, zy = zone["points"][0]
            cv2.putText(annotated, zone["name"], (int(zx), int(zy) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_ZONE, 2)
        if closed:
            cv2.putText(annotated, "TIENDA CERRADA", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_ALERT, 2)

        results = self.model.predict(frame, conf=self.confidence, classes=[0], verbose=False)
        boxes = results[0].boxes.xyxy.cpu().numpy() if results[0].boxes is not None else []

        for box in boxes:
            x1, y1, x2, y2 = box[:4]
            centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
            # Punto de apoyo: donde la persona "pisa" (para las zonas del piso)
            foot_point = ((x1 + x2) / 2, y2)
            pid = self._match_person(centroid, now)
            state = self._people[pid]
            state.positions.append((now, centroid[0], centroid[1]))

            label, color = "OK", COLOR_OK

            # 1) Intrusión fuera de horario: alerta inmediata
            if closed and not state.alerted_after_hours:
                state.alerted_after_hours = True
                label, color = "INTRUSION", COLOR_ALERT
                events.append(EventoTienda(
                    camera_name=self.camera_name,
                    tipo="intrusion",
                    mensaje=("🚨 ¡POSIBLE ROBO / INTRUSIÓN!\n"
                             "Se detectó una persona dentro de la tienda "
                             "FUERA DEL HORARIO de apertura."),
                    frame=annotated.copy(),
                    timestamp=time.time(),
                ))
            elif closed:
                label, color = "INTRUSION", COLOR_ALERT

            # 2) Zonas restringidas
            for zone in self.zones:
                inside = cv2.pointPolygonTest(zone["points"], foot_point, False) >= 0
                zname = zone["name"]
                if inside:
                    state.zone_since.setdefault(zname, now)
                    in_zone_time = now - state.zone_since[zname]
                    if in_zone_time >= zone["seconds"]:
                        if zname not in state.alerted_zones:
                            state.alerted_zones.add(zname)
                            events.append(EventoTienda(
                                camera_name=self.camera_name,
                                tipo=f"zona/{zname}",
                                mensaje=("🚨 ¡ALERTA DE SEGURIDAD!\n"
                                         f"Una persona entró a la zona restringida: {zname}."),
                                frame=annotated.copy(),
                                timestamp=time.time(),
                            ))
                        label, color = f"EN ZONA: {zname}", COLOR_ALERT
                    elif color != COLOR_ALERT:
                        label, color = f"Entrando a {zname}", COLOR_WARN
                else:
                    state.zone_since.pop(zname, None)
                    state.alerted_zones.discard(zname)

            # 3) Merodeo prolongado
            if self._is_loitering(state, now):
                if not state.alerted_loiter:
                    state.alerted_loiter = True
                    events.append(EventoTienda(
                        camera_name=self.camera_name,
                        tipo="merodeo",
                        mensaje=("⚠️ COMPORTAMIENTO SOSPECHOSO\n"
                                 "Una persona lleva más de "
                                 f"{self.loiter_seconds // 60} min en la misma zona "
                                 "casi sin moverse. Conviene revisar la cámara."),
                        frame=annotated.copy(),
                        timestamp=time.time(),
                    ))
                if color == COLOR_OK:
                    label, color = "MERODEANDO", COLOR_WARN

            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(annotated, label, (int(x1), max(20, int(y1) - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        self._forget_stale(now)
        return annotated, events
