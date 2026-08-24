"""Pré-processamento de imagem — versão em memória (bytes in, bytes out).

Os arquivos não tocam mais o disco: chegam do upload como bytes, são
processados em memória e vão criptografados direto pro banco. Duas funções:

- preparar_para_ia_multimodal: correção geométrica leve (deskew) + realce de
  contraste, mantendo COR. É o que vai pro Gemini.
- binarizar_para_ocr_tradicional: pipeline agressivo (grayscale + threshold
  adaptativo), só pro comparativo com Tesseract (seção 4.4 do TCC). Não é
  usada no pipeline principal.
"""
from typing import Optional, Tuple

import cv2
import numpy as np

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def _extensao_suportada(nome_arquivo: str) -> bool:
    nome = nome_arquivo.lower()
    return any(nome.endswith(ext) for ext in EXTENSOES_IMAGEM)


def _calcular_angulo_deskew(gray: np.ndarray) -> float:
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(mask > 0))
    if len(coords) == 0:
        return 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    return angle


def _rotacionar(img: np.ndarray, angle: float) -> np.ndarray:
    (h, w) = img.shape[:2]
    centro = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(centro, angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preparar_para_ia_multimodal(conteudo: bytes, nome_arquivo: str, mime_original: str) -> Tuple[bytes, str]:
    """Correção leve e não-destrutiva (deskew + contraste), mantendo cor.

    Devolve (bytes, mime_type) do arquivo pronto pra IA. Se não for uma
    imagem suportada (ex.: PDF) ou o OpenCV não conseguir decodificar,
    devolve o conteúdo original sem alteração — o Gemini lê PDF nativamente.
    """
    if not _extensao_suportada(nome_arquivo):
        return conteudo, mime_original

    array = np.frombuffer(conteudo, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if img is None:
        return conteudo, mime_original

    gray_para_angulo = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    angle = _calcular_angulo_deskew(gray_para_angulo)
    if abs(angle) > 0.5:
        img = _rotacionar(img, angle)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    img = cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    sucesso, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not sucesso:
        return conteudo, mime_original
    return buffer.tobytes(), "image/jpeg"


def binarizar_para_ocr_tradicional(conteudo: bytes, nome_arquivo: str) -> Optional[bytes]:
    """Pipeline agressivo (grayscale + threshold adaptativo). Uso exclusivo
    pro comparativo com OCR tradicional (Tesseract) — não usar no pipeline
    principal com Gemini."""
    if not _extensao_suportada(nome_arquivo):
        return None

    array = np.frombuffer(conteudo, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    angle = _calcular_angulo_deskew(gray)
    if abs(angle) > 0.5:
        gray = _rotacionar(gray, angle)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    processada = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10
    )

    sucesso, buffer = cv2.imencode(".png", processada)
    if not sucesso:
        return None
    return buffer.tobytes()