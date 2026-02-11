import os
import smtplib
import socket
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Monitor de Processos")


def _resolve_ipv4(host: str, port: int):
    """
    Força IPv4 para evitar 'Network is unreachable' em ambientes sem rota IPv6.
    """
    infos = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_STREAM)
    # retorna (ip, port)
    return infos[0][4]


def enviar_email(destino: str, assunto: str, corpo: str):
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER/SMTP_PASS não configurados no Environment")

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
    msg["To"] = destino
    msg.set_content(corpo)

    ip, prt = _resolve_ipv4(SMTP_HOST, SMTP_PORT)

    # Usa timeout para não travar
    server = smtplib.SMTP(timeout=20)
    try:
        server.connect(ip, prt)
        server.ehlo()
        # STARTTLS na porta 587
        server.starttls()
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
