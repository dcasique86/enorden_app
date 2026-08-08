"""Genera el icono provisional de EnOrden (assets/en_orden.ico)."""
import os
from PIL import Image, ImageDraw

destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "en_orden.ico")
os.makedirs(os.path.dirname(destino), exist_ok=True)

TAM = 256
tamanos = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

img = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

fondo = (30, 90, 160, 255)
borde = (255, 255, 255, 255)
texto = (255, 255, 255, 255)

d.rounded_rectangle([16, 16, TAM - 16, TAM - 16], radius=56, fill=fondo)
d.rounded_rectangle([16, 16, TAM - 16, TAM - 16], radius=56, outline=borde, width=10)

from PIL import ImageFont

def _fuente(pct):
    for nombre in ("seguisym.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nombre, int(TAM * pct))
        except OSError:
            continue
    return ImageFont.load_default()

fuente = _fuente(0.42)
texto_medido = d.textbbox((0, 0), "E", font=fuente)
ancho = texto_medido[2] - texto_medido[0]
alto = texto_medido[3] - texto_medido[1]
d.text(
    ((TAM - ancho) / 2 - texto_medido[0], (TAM - alto) / 2 - texto_medido[1]),
    "E", font=fuente, fill=texto,
)

img.save(destino, sizes=tamanos)
print(f"OK: {destino} ({os.path.getsize(destino)} bytes)")