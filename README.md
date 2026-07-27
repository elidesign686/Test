# 🤖 CyberPet

Una mascota virtual animada para tu escritorio: un robotito blanco y azul
que pasea por **toda** la pantalla, siempre visible encima de tus ventanas.
No hace acciones grandes — camina a puntos aleatorios, rebota al andar,
parpadea, se balancea y de vez en cuando te saluda con la mano. 👋

## Controles

| Acción | Resultado |
|---|---|
| Arrastrar con clic izquierdo | Mueves al robot a donde quieras |
| Doble clic | Te saluda |
| Clic derecho | Menú: **Saludar** / **Salir** |

## Cómo obtener el ejecutable (Windows)

### Opción 1 — Descarga directa (recomendada)
Descarga **CyberPet.exe** desde la sección
[**Releases**](../../releases) del repositorio (release *"CyberPet —
descarga directa"*) y haz doble clic. ¡Listo!

El ejecutable también está en la raíz del repositorio (`CyberPet.exe`),
subido automáticamente por GitHub Actions en cada compilación.

> Nota: Windows SmartScreen puede avisar porque el ejecutable no está
> firmado. Pulsa "Más información" → "Ejecutar de todas formas".

### Opción 2 — Compilarlo tú misma
Con [Python](https://www.python.org/downloads/) instalado, haz doble clic
en `build_windows.bat`. El ejecutable queda en `dist\CyberPet.exe`.

### Opción 3 — Sin compilar
Con Python instalado, doble clic en `cyber_pet.py` (o `py cyber_pet.py`).

## Para salir

Clic derecho sobre el robot → **Salir**.

## Detalles técnicos

- Hecho solo con Python + tkinter (sin dependencias externas): el robot se
  dibuja por código, no usa imágenes.
- La ventana es transparente y sin bordes en Windows, así que solo se ve
  el robot flotando sobre el escritorio.
- En Linux/macOS también funciona (`python3 cyber_pet.py`), aunque la
  transparencia por color solo existe en Windows.
