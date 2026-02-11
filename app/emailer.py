import os
import requests

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend").lower()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "Monitor de Processos <onboarding@resend.dev>")

def enviar_email(destino: str, assunto: str, corpo: str):
    if EMAIL_PROVIDER != "resend":
        raise RuntimeError(f"EMAIL_PROVIDER inválido: {EMAIL_PROVIDER}")

    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY não configurada no Environment")

    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": EMAIL_FROM,
            "to": [destino],
            "subject": assunto,
            "text": corpo,
        },
        timeout=20,
    )

    if r.status_code >= 400:
        raise RuntimeError(f"Resend error {r.status_code}: {r.text}")

    return r.json()
