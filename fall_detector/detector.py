"""Lógica de detección de caídas basada en estimación de pose (YOLOv8-pose).

Una caída se confirma cuando se combinan estas señales:

1. Postura horizontal: el cuadro delimitador de la persona es más ancho que
   alto, o el torso (hombros→caderas) está muy inclinado respecto a la
   vertical.
2. Descenso brusco: el centro de las caderas baja rápidamente (opcional,
   acelera la confirmación).
3. Persistencia: la persona permanece en el suelo durante N segundos, para
   no alertar cuando alguien solo se agacha o se sienta.
"""

import math
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

# Índices de keypoints en formato COCO (el que usa YOLOv8-pose)
L_SHOULDER, R_SHOULDER = 5, 6
L_HIP, R_HIP = 11, 12

COLOR_OK = (0, 200, 0)
COLOR_WARN = (0, 165, 255)
COLOR_FALL = (0, 0, 255)


@dataclass
class PersonState:
    """Estado temporal de una persona rastreada en la escena."""

    centroid: tuple
    last_seen: float
    hip_history: list = field(default_factory=list)  # (tiempo, y_cadera, alto_cuerpo)
    lying_since: float | None = None
    fall_alerted: bool = False
    event_sent: bool = False


@dataclass
class FallEvent:
    camera_name: str
    frame: np.ndarray
    timestamp: float


class FallDetector:
    """Detector de caídas para una cámara. Mantiene el estado entre cuadros."""

    MAX_TRACK_DISTANCE = 150  # píxeles para asociar detecciones entre cuadros
    TRACK_TIMEOUT = 3.0       # segundos sin ver a la persona antes de olvidarla
    HISTORY_SECONDS = 1.5     # ventana para medir la velocidad de descenso

    def __init__(self, camera_name: str, model, settings: dict):
        self.camera_name = camera_name
        self.model = model
        self.confidence = settings.get("confidence", 0.5)
        self.fall_confirm_seconds = settings.get("fall_confirm_seconds", 2.0)
        self.lying_aspect_ratio = settings.get("lying_aspect_ratio", 1.0)
        self.torso_angle_threshold = settings.get("torso_angle_threshold", 60)
        self.drop_speed_threshold = settings.get("drop_speed_threshold", 1.0)
        self._people: dict[int, PersonState] = {}
        self._next_id = 0

    # ------------------------------------------------------------------ #
    # Rastreo sencillo por cercanía de centroides
    # ------------------------------------------------------------------ #
    def _match_person(self, centroid: tuple, now: float) -> int:
        best_id, best_dist = None, self.MAX_TRACK_DISTANCE
        for pid, state in self._people.items():
            dist = math.dist(centroid, state.centroid)
            if dist < best_dist:
                best_id, best_dist = pid, dist
        if best_id is None:
            best_id = self._next_id
            self._next_id += 1
            self._people[best_id] = PersonState(centroid=centroid, last_seen=now)
        state = self._people[best_id]
        state.centroid = centroid
        state.last_seen = now
        return best_id

    def _forget_stale(self, now: float):
        stale = [pid for pid, s in self._people.items() if now - s.last_seen > self.TRACK_TIMEOUT]
        for pid in stale:
            del self._people[pid]

    # ------------------------------------------------------------------ #
    # Señales de caída
    # ------------------------------------------------------------------ #
    @staticmethod
    def _torso_angle(keypoints: np.ndarray) -> float | None:
        """Ángulo del torso respecto a la vertical, en grados (0 = de pie)."""
        pts = {}
        for idx in (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP):
            x, y, conf = keypoints[idx]
            if conf < 0.3:
                return None
            pts[idx] = (x, y)
        shoulder = ((pts[L_SHOULDER][0] + pts[R_SHOULDER][0]) / 2,
                    (pts[L_SHOULDER][1] + pts[R_SHOULDER][1]) / 2)
        hip = ((pts[L_HIP][0] + pts[R_HIP][0]) / 2,
               (pts[L_HIP][1] + pts[R_HIP][1]) / 2)
        dx, dy = shoulder[0] - hip[0], shoulder[1] - hip[1]
        if dx == 0 and dy == 0:
            return None
        return math.degrees(math.atan2(abs(dx), abs(dy)))

    def _is_fast_drop(self, state: PersonState) -> bool:
        """¿El centro de cadera bajó bruscamente en la ventana reciente?"""
        if len(state.hip_history) < 2:
            return False
        t_old, y_old, h_old = state.hip_history[0]
        t_new, y_new, _ = state.hip_history[-1]
        dt = t_new - t_old
        if dt <= 0 or h_old <= 0:
            return False
        # Velocidad de descenso medida en "alturas de cuerpo por segundo"
        speed = (y_new - y_old) / h_old / dt
        return speed > self.drop_speed_threshold

    # ------------------------------------------------------------------ #
    # Procesamiento de un cuadro
    # ------------------------------------------------------------------ #
    def process(self, frame: np.ndarray) -> tuple[np.ndarray, list[FallEvent]]:
        """Analiza un cuadro. Devuelve el cuadro anotado y los eventos de caída."""
        now = time.monotonic()
        events: list[FallEvent] = []
        annotated = frame

        results = self.model.predict(frame, conf=self.confidence, classes=[0], verbose=False)
        result = results[0]

        boxes = result.boxes.xyxy.cpu().numpy() if result.boxes is not None else []
        all_kpts = (
            result.keypoints.data.cpu().numpy()
            if result.keypoints is not None and result.keypoints.data is not None
            else [None] * len(boxes)
        )

        for box, kpts in zip(boxes, all_kpts):
            x1, y1, x2, y2 = box[:4]
            w, h = x2 - x1, y2 - y1
            centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
            pid = self._match_person(centroid, now)
            state = self._people[pid]

            # Historial de la altura de cadera para medir descensos bruscos
            hip_y = (y1 + y2) / 2
            if kpts is not None and len(kpts) > R_HIP:
                lx, ly, lc = kpts[L_HIP]
                rx, ry, rc = kpts[R_HIP]
                if lc >= 0.3 and rc >= 0.3:
                    hip_y = (ly + ry) / 2
            body_height = max(h, w)
            state.hip_history.append((now, hip_y, body_height))
            state.hip_history = [
                e for e in state.hip_history if now - e[0] <= self.HISTORY_SECONDS
            ]

            # ¿La persona está en postura horizontal?
            horizontal_box = h > 0 and (w / h) >= self.lying_aspect_ratio
            angle = self._torso_angle(kpts) if kpts is not None and len(kpts) > R_HIP else None
            torso_down = angle is not None and angle >= self.torso_angle_threshold
            is_lying = horizontal_box or torso_down

            fast_drop = self._is_fast_drop(state)

            if is_lying:
                if state.lying_since is None:
                    state.lying_since = now
                # Una caída brusca confirma más rápido que alguien que se recuesta
                confirm_time = (
                    self.fall_confirm_seconds / 2 if fast_drop else self.fall_confirm_seconds
                )
                lying_time = now - state.lying_since
                if lying_time >= confirm_time:
                    state.fall_alerted = True
                    label, color = "CAIDA DETECTADA", COLOR_FALL
                else:
                    label, color = f"En el suelo {lying_time:.1f}s", COLOR_WARN
            else:
                # La persona se levantó: se rearma la alerta
                state.lying_since = None
                state.fall_alerted = False
                state.event_sent = False
                label, color = "OK", COLOR_OK

            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            cv2.putText(
                annotated,
                label,
                (int(x1), max(20, int(y1) - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

            if state.fall_alerted and not state.event_sent:
                state.event_sent = True
                events.append(
                    FallEvent(
                        camera_name=self.camera_name,
                        frame=annotated.copy(),
                        timestamp=time.time(),
                    )
                )

        self._forget_stale(now)
        return annotated, events
