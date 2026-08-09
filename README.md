# 🚨 Vigilancia Inteligente: Caídas y Antirrobo con Alertas al Celular

Dos sistemas que comparten las mismas cámaras y alertas:

- **Detección de caídas** (`main.py`): detecta cuando una persona se cae y
  permanece en el suelo.
- **Vigilancia antirrobo para tiendas** (`vigilancia_tienda.py`): detecta
  intrusiones fuera de horario, personas en zonas restringidas y merodeo.

---

# Parte 1: Detección de Caídas

Sistema de visión por computadora que analiza en tiempo real el video de una o
varias cámaras de vigilancia, detecta cuando una persona **se cae y permanece
en el suelo**, y envía inmediatamente una **alerta al celular** con la foto del
momento de la caída.

## ¿Cómo funciona?

1. **Detección de personas y pose**: usa el modelo [YOLOv8-pose](https://docs.ultralytics.com/tasks/pose/)
   para localizar a cada persona y sus articulaciones (hombros, caderas, etc.).
2. **Análisis de caída**: combina tres señales para evitar falsas alarmas:
   - La persona está en **postura horizontal** (cuerpo más ancho que alto o
     torso muy inclinado respecto a la vertical).
   - Hubo un **descenso brusco** del cuerpo (caída rápida, no alguien que se
     recuesta despacio).
   - La persona **permanece en el suelo** durante unos segundos (configurable).
3. **Alerta al celular**: cuando se confirma la caída, envía un mensaje con la
   foto por **Telegram** (gratis) y/o **SMS/WhatsApp con Twilio** (opcional).

```
Cámaras (RTSP/HTTP/webcam) ──► YOLOv8-pose ──► Lógica de caída ──► 📱 Alerta al celular
                                                     │
                                                     └──► 💾 Captura guardada
```

## Requisitos

- Python 3.10 o superior
- Una cámara: webcam, cámara IP con RTSP (Hikvision, Dahua, TP-Link, etc.) o
  un archivo de video para pruebas
- (Recomendado) Una cuenta de Telegram para recibir las alertas gratis

## Instalación

```bash
git clone <este-repositorio>
cd <carpeta-del-repositorio>
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

La primera vez que ejecutes el programa, el modelo `yolov8n-pose.pt` se
descarga automáticamente (~6 MB).

## Configuración

Todo se configura en [`config.yaml`](config.yaml).

### 1. Cámaras

```yaml
cameras:
  - name: "Camara Sala"
    source: 0                     # Webcam local (para pruebas)
  - name: "Camara Patio"
    source: "rtsp://admin:clave@192.168.1.50:554/Streaming/Channels/101"
  - name: "Video de prueba"
    source: "videos/prueba.mp4"   # Archivo de video (para pruebas)
```

URLs RTSP típicas según la marca de la cámara:

| Marca | URL típica |
|-------|-----------|
| Hikvision | `rtsp://usuario:clave@IP:554/Streaming/Channels/101` |
| Dahua | `rtsp://usuario:clave@IP:554/cam/realmonitor?channel=1&subtype=0` |
| TP-Link Tapo | `rtsp://usuario:clave@IP:554/stream1` |
| Genérica ONVIF | `rtsp://usuario:clave@IP:554/` |

### 2. Alertas por Telegram (gratis, recomendado)

1. En Telegram, escribe a [@BotFather](https://t.me/BotFather), envía `/newbot`
   y sigue los pasos. Te dará un **token** como `123456789:ABCdef...`.
2. Escribe a [@userinfobot](https://t.me/userinfobot) para obtener tu
   **chat_id** (un número como `987654321`).
3. Abre un chat con tu nuevo bot y envíale `/start` (necesario para que pueda
   escribirte).
4. Pon el token y el chat_id en `config.yaml`:

```yaml
alerts:
  telegram:
    enabled: true
    bot_token: "123456789:ABCdef..."
    chat_ids:
      - "987654321"
```

Puedes agregar varios `chat_ids` (familiares, cuidadores) o el id de un grupo.

### 3. Alertas por SMS/WhatsApp con Twilio (opcional)

```bash
pip install twilio
```

```yaml
alerts:
  twilio:
    enabled: true
    account_sid: "ACxxxxxxxx"
    auth_token: "xxxxxxxx"
    from_number: "+14155238886"
    to_numbers:
      - "+521234567890"              # SMS
      - "whatsapp:+521234567890"     # WhatsApp
```

## Uso

```bash
python main.py                  # usa config.yaml
python main.py -c otra_config.yaml
```

- Se abre una ventana por cámara con las detecciones en vivo:
  - 🟩 **OK**: persona de pie / actividad normal
  - 🟧 **En el suelo X.Xs**: posible caída, contando el tiempo en el suelo
  - 🟥 **CAIDA DETECTADA**: caída confirmada → se envía la alerta
- Presiona `q` en la ventana o `Ctrl+C` en la terminal para salir.
- En un servidor sin pantalla, pon `display.show_video: false` en la config.
- Las capturas de cada caída se guardan en la carpeta `capturas/`.

## Ajustes importantes (`config.yaml`)

| Parámetro | Qué hace | Valor por defecto |
|-----------|----------|-------------------|
| `fall_confirm_seconds` | Segundos en el suelo para confirmar la caída | `2.0` |
| `lying_aspect_ratio` | Qué tan "horizontal" debe verse el cuerpo | `1.0` |
| `torso_angle_threshold` | Inclinación del torso (grados) para considerarse caído | `60` |
| `frame_skip` | Analiza 1 de cada N cuadros (súbelo en equipos lentos) | `2` |
| `cooldown_seconds` | Tiempo mínimo entre alertas de la misma cámara | `60` |
| `model` | `yolov8n-pose.pt` (rápido) o `yolov8s-pose.pt` (más preciso) | `yolov8n-pose.pt` |

## Consejos para reducir falsas alarmas

- Ajusta `fall_confirm_seconds` a 3–5 s si hay mascotas o niños jugando.
- Coloca la cámara a 2–2.5 m de altura con vista amplia de la habitación.
- Si la cámara ve camas o sofás de frente, sube `torso_angle_threshold` a 70.
- Usa `yolov8s-pose.pt` si el equipo lo permite: mejora bastante la precisión.

---

# Parte 2: Vigilancia Antirrobo para Tiendas

Con las mismas cámaras, `vigilancia_tienda.py` detecta las situaciones de
riesgo de robo que la visión por computadora sí puede identificar de forma
fiable:

| Detección | Qué hace | Alerta |
|-----------|----------|--------|
| 🌙 **Intrusión fuera de horario** | Cualquier persona dentro de la tienda cuando está cerrada | Inmediata: "posible robo/intrusión" |
| 🚫 **Zonas restringidas** | Alguien entra detrás del mostrador, a la bodega o junto a una vitrina y permanece unos segundos | "Persona en zona restringida" |
| 🕵️ **Merodeo** | Una persona permanece varios minutos casi sin moverse en el mismo lugar | "Comportamiento sospechoso" |

> **Nota honesta**: ningún sistema de visión detecta con fiabilidad el momento
> exacto en que alguien esconde un producto — los que lo prometen generan
> muchísimas falsas acusaciones. Estas tres señales son las que usan los
> sistemas comerciales de prevención de pérdidas.

## Uso

```bash
# 1. Configura tus cámaras, horario y alertas
nano config_tienda.yaml

# 2. Dibuja las zonas restringidas con clics del mouse sobre el video
python definir_zonas.py                # webcam
python definir_zonas.py "rtsp://usuario:clave@IP:554/stream1"
#    (pega el YAML que imprime dentro de tu cámara en config_tienda.yaml)

# 3. Inicia la vigilancia
python vigilancia_tienda.py
```

## Configuración clave (`config_tienda.yaml`)

```yaml
store:
  after_hours:
    enabled: true
    open_time: "09:00"     # también soporta horarios que cruzan medianoche
    close_time: "21:00"
  loitering:
    enabled: true
    seconds: 120           # minutos quieto para considerarse merodeo
    radius: 80             # qué tanto puede moverse y seguir "quieto"

cameras:
  - name: "Camara Tienda"
    source: "rtsp://..."
    zones:
      - name: "Detras del mostrador"
        points: [[50, 300], [300, 300], [300, 470], [50, 470]]
        seconds: 3         # segundos dentro de la zona antes de alertar
```

Las alertas llegan al celular igual que las de caídas (Telegram/Twilio, con la
foto del momento), cada tipo de alerta con su propio enfriamiento.

## Cómo probarlo

1. Verifica primero las alertas con `python probar_alerta.py`.
2. **Zona restringida**: define una zona con `definir_zonas.py`, inicia el
   sistema y párate dentro de la zona 3 segundos → alerta en el celular.
3. **Intrusión**: pon `open_time`/`close_time` en un horario en el que la
   tienda esté "cerrada" ahora mismo y pasa frente a la cámara → alerta
   inmediata.
4. **Merodeo**: baja `loitering.seconds` a 15 para la prueba y quédate quieto
   frente a la cámara.

---

# Aviso importante

Estos sistemas son una **ayuda de monitoreo**, no un dispositivo médico
certificado ni una prueba de delito. La detección de caídas no sustituye la
supervisión humana ni los servicios de teleasistencia; una alerta de la
tienda indica una situación a **verificar por una persona**, nunca una
acusación automática. Si instalas cámaras en un negocio, cumple la normativa
local de videovigilancia (avisos visibles, protección de datos, etc.).
