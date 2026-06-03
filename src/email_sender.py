"""
Sends emails with HTML report attachments via Gmail SMTP.
"""
import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

from config import config


_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def _build_email_body(subject: str, period: str, comparison: str, report_type: str) -> str:
    is_periodic = "Mensal" in report_type or "Semanal" in report_type
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 0; }}
    .container {{ max-width: 560px; margin: 24px auto; background: #fff;
                  border-radius: 10px; border: 1px solid #e0e0e8; overflow: hidden; }}
    .header {{ background: #1a1a2e; padding: 26px 30px; }}
    .header h1 {{ color: #fff; margin: 0; font-size: 18px; font-weight: 700; }}
    .header p {{ color: rgba(255,255,255,0.6); margin: 6px 0 0; font-size: 12px; }}
    .body {{ padding: 24px 30px; }}
    .body p {{ color: #3c3c4e; font-size: 14px; line-height: 1.6; margin: 0 0 14px; }}
    .pills {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0; }}
    .pill {{ background: #f0f2f5; color: #1a1a2e; padding: 4px 12px;
             border-radius: 20px; font-size: 12px; font-weight: 600;
             border: 1px solid #e0e0e8; }}
    .note {{ color: #9b9bae; font-size: 12px; margin-top: 16px; }}
    .footer {{ background: #f8f9fa; padding: 14px 30px; text-align: center;
               color: #9b9bae; font-size: 11px; border-top: 1px solid #e0e0e8; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{subject}</h1>
      <p>Relatorio automatico gerado as 12h (horario de Brasilia)</p>
    </div>
    <div class="body">
      <p>Ola,</p>
      <p>
        Segue o relatorio {'mensal' if 'Mensal' in report_type else 'semanal' if 'Semanal' in report_type else 'diario'} em anexo.
        O HTML contem a analise completa com metricas, anomalias, insights e acoes propostas.
      </p>
      <div class="pills">
        <span class="pill">Periodo: {period}</span>
        <span class="pill">Comparacao: {comparison}</span>
      </div>
      <p class="note">
        Este relatorio e enviado automaticamente todos os dias as 12h
        {'e toda segunda-feira com analise mensal e semanal.' if is_periodic else '.'}
      </p>
    </div>
    <div class="footer">
      NEX Coworking &bull; felipe@nexcoworking.com.br &bull; Relatorio automatico
    </div>
  </div>
</body>
</html>"""


def send_report(
    to: str,
    subject: str,
    html_report_path: str,
    period: str,
    comparison: str,
    report_type: str,
):
    if not os.path.exists(html_report_path):
        raise FileNotFoundError(f"Relatorio HTML nao encontrado: {html_report_path}")

    # Outer MIME container
    msg = MIMEMultipart("mixed")
    msg["From"] = config.GMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject

    # Email body (short HTML)
    body_html = _build_email_body(subject, period, comparison, report_type)
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    # HTML report as attachment
    with open(html_report_path, "rb") as f:
        attachment = MIMEText(f.read().decode("utf-8"), "html", "utf-8")
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(html_report_path),
        )
        msg.attach(attachment)

    context = ssl.create_default_context()
    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_USER, to, msg.as_string())

    print(f"[email] Enviado para {to}: {subject}")


# ── Convenience wrappers ─────────────────────────────────────────────────────

def send_reportei_daily(html_path: str, analysis_date: date):
    send_report(
        to=config.EMAIL_DAILY_TO,
        subject=f"[Reportei] Analise Diaria — {analysis_date.strftime('%d/%m/%Y')}",
        html_report_path=html_path,
        period=analysis_date.strftime("%d/%m/%Y"),
        comparison="Dia anterior + mesmo dia mes passado",
        report_type="Reportei Diario",
    )


def send_reportei_monthly(html_path: str, period_start: date, period_end: date):
    prev_month = period_start.month - 1 if period_start.month > 1 else 12
    send_report(
        to=config.EMAIL_WEEKLY_TO,
        subject=(
            f"[Reportei] Relatorio Mensal — "
            f"{period_start.strftime('%d/%m')} a {period_end.strftime('%d/%m/%Y')}"
        ),
        html_report_path=html_path,
        period=f"{period_start.strftime('%d/%m')} - {period_end.strftime('%d/%m/%Y')}",
        comparison=f"Mesmo periodo de {period_start.replace(month=prev_month).strftime('%B')}",
        report_type="Reportei Mensal",
    )


def send_reportei_weekly(html_path: str, week_start: date, week_end: date):
    send_report(
        to=config.EMAIL_WEEKLY_TO,
        subject=(
            f"[Reportei] Relatorio Semanal — "
            f"Semana de {week_start.strftime('%d/%m')} a {week_end.strftime('%d/%m/%Y')}"
        ),
        html_report_path=html_path,
        period=f"{week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m/%Y')}",
        comparison="Mesma semana do mes anterior",
        report_type="Reportei Semanal",
    )


def send_google_ads_full(pdf_path: str, analysis_date: date):
    """Envia o relatorio completo Google Ads (diario + mensal) como PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nao encontrado: {pdf_path}")

    period_start = analysis_date.replace(day=1)
    subject = f"[Google Ads] Relatorio Completo — {analysis_date.strftime('%d/%m/%Y')}"

    msg = MIMEMultipart("mixed")
    msg["From"] = config.GMAIL_USER
    msg["To"]   = config.EMAIL_DAILY_TO
    msg["Subject"] = subject

    body_html = _build_email_body(
        subject=subject,
        period=f"{analysis_date.strftime('%d/%m/%Y')} + {period_start.strftime('%d/%m')} a {analysis_date.strftime('%d/%m/%Y')}",
        comparison="Dia anterior + mes anterior (MTD)",
        report_type="Google Ads Completo",
    )
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    from email.mime.application import MIMEApplication
    with open(pdf_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
        attachment.add_header(
            "Content-Disposition", "attachment",
            filename=os.path.basename(pdf_path),
        )
        msg.attach(attachment)

    context = ssl.create_default_context()
    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        server.sendmail(config.GMAIL_USER, config.EMAIL_DAILY_TO, msg.as_string())

    print(f"[email] PDF Google Ads enviado para {config.EMAIL_DAILY_TO}: {subject}")


# ── Legacy wrappers (mantidos para compatibilidade) ──────────────────────────

def send_google_ads_daily(html_path: str, analysis_date: date):
    send_report(
        to=config.EMAIL_DAILY_TO,
        subject=f"[Google Ads] Analise Diaria — {analysis_date.strftime('%d/%m/%Y')}",
        html_report_path=html_path,
        period=analysis_date.strftime("%d/%m/%Y"),
        comparison="Dia anterior",
        report_type="Google Ads Diario",
    )


def send_google_ads_monthly(html_path: str, period_start: date, period_end: date):
    send_report(
        to=config.EMAIL_WEEKLY_TO,
        subject=(
            f"[Google Ads] Relatorio Mensal — "
            f"{period_start.strftime('%d/%m')} a {period_end.strftime('%d/%m/%Y')}"
        ),
        html_report_path=html_path,
        period=f"{period_start.strftime('%d/%m')} - {period_end.strftime('%d/%m/%Y')}",
        comparison="Mesmo periodo mes anterior",
        report_type="Google Ads Mensal",
    )
