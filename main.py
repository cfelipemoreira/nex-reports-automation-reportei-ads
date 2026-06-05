"""
Entry point — runs the scheduler and orchestrates all reports.

Usage:
    python main.py                   # start scheduler (runs indefinitely)
    python main.py --now reportei-daily
    python main.py --now reportei-monthly
    python main.py --now reportei-weekly
    python main.py --now gads-daily
    python main.py --now gads-monthly
    python main.py --now all
"""
import sys
import logging
from datetime import date, datetime

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import config
from src import reportei_client as reportei_module
from src.google_ads_client import GoogleAdsDirectClient
from src import analyzer
from src.html_generator import generate_html, html_path
from src.gads_report import build_gads_report
from src.pdf_generator import html_to_pdf, pdf_path
from src import email_sender
from src import git_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TZ       = pytz.timezone(config.TIMEZONE)
reportei = reportei_module.ReporteiClient()

# GoogleAdsDirectClient é inicializado de forma lazy dentro de cada job
# para que erros de credencial não derrubem o scheduler inteiro.
_gads_client: GoogleAdsDirectClient | None = None

def _get_gads() -> GoogleAdsDirectClient:
    global _gads_client
    if _gads_client is None:
        _gads_client = GoogleAdsDirectClient()
    return _gads_client


# ── Job: Reportei daily ──────────────────────────────────────────────────────

def job_reportei_daily(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[reportei-daily] Iniciando analise para %s", today)
    try:
        raw      = reportei.fetch_daily_data(today)
        analysis = analyzer.analyze_reportei_daily(raw, today)

        path = html_path("reportei_daily", today.strftime("%Y-%m-%d"))
        generate_html(analysis, path)
        log.info("[reportei-daily] HTML gerado: %s", path)

        email_sender.send_reportei_daily(path, today)
        git_manager.commit_report("reportei-daily", today.strftime("%Y-%m-%d"))
        log.info("[reportei-daily] Concluido.")

    except Exception as e:
        log.exception("[reportei-daily] Erro: %s", e)


# ── Job: Reportei monthly (every Monday) ────────────────────────────────────

def job_reportei_monthly(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[reportei-monthly] Iniciando relatorio mensal para %s", today)
    try:
        raw      = reportei.fetch_monthly_period_data(today)
        analysis = analyzer.analyze_reportei_monthly(raw)

        path = html_path("reportei_monthly", today.strftime("%Y-%m-%d"))
        generate_html(analysis, path)
        log.info("[reportei-monthly] HTML gerado: %s", path)

        period_start = today.replace(day=1)
        email_sender.send_reportei_monthly(path, period_start, today)
        git_manager.commit_report("reportei-monthly", today.strftime("%Y-%m-%d"))
        log.info("[reportei-monthly] Concluido.")

    except Exception as e:
        log.exception("[reportei-monthly] Erro: %s", e)


# ── Job: Reportei weekly (every Monday) ─────────────────────────────────────

def job_reportei_weekly(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[reportei-weekly] Iniciando relatorio semanal para %s", today)
    try:
        raw      = reportei.fetch_weekly_data(today)
        analysis = analyzer.analyze_weekly(raw)

        path = html_path("reportei_weekly", today.strftime("%Y-%m-%d"))
        generate_html(analysis, path)
        log.info("[reportei-weekly] HTML gerado: %s", path)

        # Derive week_start and week_end from the analysis period label
        # Fall back to fetching directly from raw data
        first_int = next(iter(raw.values()), {})
        week_start = first_int.get("current_period", {}).get("start", today)
        week_end   = first_int.get("current_period", {}).get("end",   today)

        email_sender.send_reportei_weekly(path, week_start, week_end)
        git_manager.commit_report("reportei-weekly", today.strftime("%Y-%m-%d"))
        log.info("[reportei-weekly] Concluido.")

    except Exception as e:
        log.exception("[reportei-weekly] Erro: %s", e)


# ── Job: Google Ads completo (diario + mensal em um PDF) ─────────────────────

def job_gads(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[gads] Iniciando relatorio completo Google Ads para %s", today)
    try:
        gads = _get_gads()
        daily_raw   = gads.fetch_daily(today)
        monthly_raw = gads.fetch_monthly(today)

        html_str  = build_gads_report(daily_raw, monthly_raw, today)
        out_pdf   = pdf_path("gads_full", today.strftime("%Y-%m-%d"))
        html_to_pdf(html_str, out_pdf)
        log.info("[gads] PDF gerado: %s", out_pdf)

        email_sender.send_google_ads_full(out_pdf, today)
        git_manager.commit_report("gads-full", today.strftime("%Y-%m-%d"))
        log.info("[gads] Concluido.")

    except Exception as e:
        log.exception("[gads] Erro: %s", e)


# ── Monday combined job ──────────────────────────────────────────────────────

def job_monday(run_date: date | None = None):
    """Every Monday: Reportei (daily + monthly + weekly) + Google Ads completo."""
    today = run_date or date.today()
    job_reportei_daily(today)
    job_reportei_monthly(today)
    job_reportei_weekly(today)
    job_gads(today)


# ── Weekday (non-Monday) combined job ───────────────────────────────────────

def job_weekday(run_date: date | None = None):
    today = run_date or date.today()
    job_reportei_daily(today)
    job_gads(today)


# ── Scheduler setup ──────────────────────────────────────────────────────────

def start_scheduler():
    scheduler = BlockingScheduler(timezone=TZ)

    # Tue–Sun at 11:50 — daily reports only
    # misfire_grace_time=28800 (8h): se o Mac estiver dormindo ao meio-dia e
    # acordar até as 19h50, o job ainda roda no mesmo dia.
    scheduler.add_job(
        job_weekday,
        trigger=CronTrigger(day_of_week="tue,wed,thu,fri,sat,sun", hour=11, minute=50, timezone=TZ),
        id="weekday_daily",
        name="Relatorios diarios (ter-dom) — 11h50",
        misfire_grace_time=28800,
        coalesce=True,
    )

    # Every Monday at 11:50 — daily + monthly + weekly reports
    scheduler.add_job(
        job_monday,
        trigger=CronTrigger(day_of_week="mon", hour=11, minute=50, timezone=TZ),
        id="monday_full",
        name="Segunda-feira: diario + mensal + semanal — 11h50",
        misfire_grace_time=28800,
        coalesce=True,
    )

    log.info("Scheduler configurado — aguardando inicio...")
    log.info("Jobs agendados:")
    for job in scheduler.get_jobs():
        log.info("  - %s", job.name)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler encerrado.")


# ── CLI manual trigger ───────────────────────────────────────────────────────

_JOB_MAP = {
    "reportei-daily":   job_reportei_daily,
    "reportei-monthly": job_reportei_monthly,
    "reportei-weekly":  job_reportei_weekly,
    "gads":             job_gads,
    "all": lambda: (
        job_reportei_daily(),
        job_reportei_monthly(),
        job_reportei_weekly(),
        job_gads(),
    ),
}

if __name__ == "__main__":
    if "--now" in sys.argv:
        idx = sys.argv.index("--now")
        job_name = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "all"
        fn = _JOB_MAP.get(job_name)
        if fn:
            log.info("Executando manualmente: %s", job_name)
            fn()
        else:
            print(f"Job desconhecido: {job_name}")
            print(f"Opcoes: {', '.join(_JOB_MAP.keys())}")
            sys.exit(1)
    else:
        start_scheduler()
