import cv2
import numpy as np
from PIL import Image
import os

# ===============================
# CONFIGURAÇÕES
# ===============================
INPUT_TEXTURE = r"D:\Codigos\ExtraiTexturas_GLB\Saida\Soldado_armadura01_texture.png"
OUTPUT_TEXTURE = r"D:\Codigos\ExtraiTexturas_GLB\Saida\Soldado_armadura01_texture_inpaint.png"

# Limite para considerar pixel "preto"
BLACK_THRESHOLD = 15  # 0–255
INPAINT_RADIUS = 3   # quanto maior, mais agressivo

# ===============================
# CARREGAR IMAGEM
# ===============================
if not os.path.exists(INPUT_TEXTURE):
    raise FileNotFoundError(f"Arquivo não encontrado: {INPUT_TEXTURE}")

img = Image.open(INPUT_TEXTURE).convert("RGB")
img_np = np.array(img)

# ===============================
# CRIAR MÁSCARA (PIXELS PRETOS)
# ===============================
# Converte para escala de cinza
gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

# Cria máscara onde o pixel é quase preto
mask = gray < BLACK_THRESHOLD
mask = mask.astype(np.uint8) * 255

# ===============================
# INPAINTING
# ===============================
print("▶ Executando inpainting automático...")

inpainted = cv2.inpaint(
    img_np,
    mask,
    INPAINT_RADIUS,
    cv2.INPAINT_TELEA
)

# ===============================
# SALVAR RESULTADO
# ===============================
Image.fromarray(inpainted).save(OUTPUT_TEXTURE)

print("✔ Textura corrigida salva como:", OUTPUT_TEXTURE)
