import cv2
import numpy as np
import os

def processar_imagem_para_ocr(caminho_arquivo: str) -> bool:
    """
    Aplica técnicas suaves de pré-processamento para melhorar a leitura de OCR.
    Retorna True se o processamento for bem-sucedido.
    """
    if not os.path.exists(caminho_arquivo):
        return False

    # 1. Ler a imagem original
    img = cv2.imread(caminho_arquivo)
    if img is None:
        return False

    # 2. Conversão para Escala de Cinza
    # Remove as cores, focando apenas no contraste entre fundo e texto
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. Correção Suave de Rotação (Deskew)
    # Binariza a imagem invertida apenas para localizar os blocos de texto
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    # Encontra as coordenadas de todos os pixels de texto
    coords = np.column_stack(np.where(mask > 0))
    if len(coords) > 0:
        # Calcula o ângulo da caixa delimitadora que envolve o texto
        angle = cv2.minAreaRect(coords)[-1]
        
        # Ajuste de compensação do ângulo do OpenCV
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Só rotaciona se a inclinação for maior que 0.5 graus (evita distorcer imagens boas)
        if abs(angle) > 0.5:
            (h, w) = gray.shape[:2]
            centro = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(centro, angle, 1.0)
            # Aplica a rotação preenchendo as bordas vazias com a cor mais próxima
            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    # 4. Aumento de Contraste e Binarização Adaptativa
    # O desfoque suave (Blur) ajuda a remover pequenos ruídos pontuais antes do contraste
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Usamos o Adaptive Threshold porque ele lida incrivelmente bem com sombras
    # irregulares causadas por fotos tiradas de celular, calculando o contraste por regiões.
    processada = cv2.adaptiveThreshold(
        blur, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 
        21, # Tamanho do bloco (área de cálculo local)
        10  # Constante subtraída da média (ajuste de sensibilidade)
    )

    # 5. Sobrescrever o arquivo salvo com a versão limpa
    cv2.imwrite(caminho_arquivo, processada)
    
    return True