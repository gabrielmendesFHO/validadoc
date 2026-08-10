"""Pré-processamento de imagem.

O pipeline prepara imagens para análise multimodal:

- preparar_para_ia_multimodal: correção geométrica leve (deskew) + realce de
  contraste, mantendo COR. É o que vai pro Gemini. Modelos multimodais leem
  layout, sombras, carimbos e marcas d'água — informação que se perde se a
  imagem virar preto-e-branco puro.

Nenhuma das duas sobrescreve o arquivo original — a cópia processada é gravada
ao lado do arquivo de entrada com o sufixo _prep.
"""
import os

import cv2
import numpy as np

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}


def _extensao(caminho: str) -> str:
    return os.path.splitext(caminho)[1].lower()


def _calcular_angulo_deskew(gray: np.ndarray) -> float:
    """Estima o ângulo de rotação do texto a partir de uma máscara binarizada.
    Usada só pra calcular o ângulo — não altera a imagem de origem."""
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


def preparar_para_ia_multimodal(caminho_arquivo: str) -> str:
    """Correção leve e não-destrutiva (deskew + contraste), mantendo cor.

    Retorna o caminho do arquivo que deve ser enviado ao Gemini. Se o arquivo
    não for uma imagem suportada pelo OpenCV (ex.: PDF), devolve o próprio
    caminho original sem tocar nele — o Gemini lê PDF nativamente.
    """
    if _extensao(caminho_arquivo) not in EXTENSOES_IMAGEM:
        return caminho_arquivo

    img = cv2.imread(caminho_arquivo)
    if img is None:
        return caminho_arquivo

    gray_para_angulo = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    angle = _calcular_angulo_deskew(gray_para_angulo)
    if abs(angle) > 0.5:
        img = _rotacionar(img, angle)

    # Realce de contraste em cor: CLAHE no canal de luminância (espaço LAB),
    # preservando os canais de cor a/b intactos.
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    img = cv2.cvtColor(cv2.merge((l_channel, a_channel, b_channel)), cv2.COLOR_LAB2BGR)

    base, ext = os.path.splitext(caminho_arquivo)
    caminho_saida = f"{base}_prep{ext}"
    cv2.imwrite(caminho_saida, img)
    return caminho_saida
