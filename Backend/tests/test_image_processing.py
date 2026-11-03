import cv2
import numpy as np

from app.services.image_processing import preparar_para_ia_multimodal


def test_foto_alta_resolucao_limita_imagem_de_trabalho_sem_perder_conteudo():
    imagem = np.full((4032, 3024, 3), 255, dtype=np.uint8)
    cv2.putText(imagem, "DOCUMENTO TESTE 123456", (200, 2000), cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 0, 0), 10)
    _, original = cv2.imencode(".jpg", imagem)
    preparado, mime = preparar_para_ia_multimodal(original.tobytes(), "foto.jpg", "image/jpeg")
    resultado = cv2.imdecode(np.frombuffer(preparado, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert mime == "image/jpeg"
    assert max(resultado.shape[:2]) <= 2000
    assert np.count_nonzero(cv2.cvtColor(resultado, cv2.COLOR_BGR2GRAY) < 100) > 500


def test_pdf_permanece_original():
    original = b"%PDF-1.7 arquivo de teste"
    assert preparar_para_ia_multimodal(original, "doc.pdf", "application/pdf") == (original, "application/pdf")
