import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings
import logging

logger = logging.getLogger(__name__)

def enviar_email_boas_vindas(email_destino: str, nome_candidato: str, senha_temporaria: str):
    """Envia um e-mail de boas-vindas com a senha provisória gerada."""
    
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("SMTP não configurado. O e-mail de boas-vindas não será enviado.")
        return

    assunto = "Sua inscrição foi recebida - Acesso ao Portal"
    
    corpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0056b3;">Olá, {nome_candidato}!</h2>
            <p>Seu pré-cadastro foi realizado com sucesso em nosso sistema.</p>
            <p>Para acompanhar o status da sua inscrição e enviar os documentos necessários, acesse o portal usando suas credenciais:</p>
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Usuário (E-mail ou CPF):</strong> {email_destino}</p>
                <p style="margin: 0;"><strong>Senha Provisória:</strong> {senha_temporaria}</p>
            </div>
            <p><em>Recomendamos que você altere esta senha no seu primeiro acesso.</em></p>
            <br>
            <p>Atenciosamente,<br>Equipe de Admissão</p>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = settings.smtp_from_email
    msg['To'] = email_destino
    msg['Subject'] = assunto
    
    msg.attach(MIMEText(corpo_html, 'html'))

    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
            logger.info(f"E-mail de boas-vindas enviado para {email_destino}")
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {email_destino}: {str(e)}")

