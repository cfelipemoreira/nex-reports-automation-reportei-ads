"""
Entry point — runs the scheduler and orchestrates all reports.

Usage:
    python main.py            # start scheduler (runs indefinitely)
    python main.py --now reportei-daily
    python main.py --now reportei-monthly
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
from src import google_ads_client as gads
from src import analyzer
from src.pdf_generator import generate_pdf, pdf_path
from src import email_sender
from src import git_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TZ = pytz.timezone(config.TIMEZONE)
reportei = reportei_module.ReporteiClient()


# ── Cached dashboard ID ─────────────────────────────────────────────────────

# ── Job: Reportei daily ─────────────────────────────────────────────────────

def job_reportei_daily(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[reportei-daily] Iniciando analise para %s", today)
    try:
        raw = reportei.fetch_daily_data(today)
        analysis = analyzer.analyze_reportei_daily(raw, today)

        path = pdf_path("reportei_daily", today.strftime("%Y-%m-%d"))
        generate_pdf(analysis, path)
        log.info("[reportei-daily] PDF gerado: %s", path)

        email_sender.send_reportei_daily(path, today)
        git_manager.commit_report("reportei-daily", today.strftime("%Y-%m-%d"))
        log.info("[reportei-daily] Concluido.")

    except Exception as e:
        log.exception("[reportei-daily] Erro: %s", e)


# ── Job: Reportei monthly (every Monday) ───────────────────────────────────

def job_reportei_monthly(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[reportei-monthly] Iniciando relatorio mensal para %s", today)
    try:
        raw = reportei.fetch_monthly_period_data(today)
        analysis = analyzer.analyze_reportei_monthly(raw)

        path = pdf_path("reportei_monthly", today.strftime("%Y-%m-%d"))
        generate_pdf(analysis, path)
        log.info("[reportei-monthly] PDF gerado: %s", path)

        period_start = today.replace(day=1)
        email_sender.send_reportei_monthly(path, period_start, today)
        git_manager.commit_report("reportei-monthly", today.strftime("%Y-%m-%d"))
        log.info("[reportei-monthly] Concluido.")

    except Exception as e:
        log.exception("[reportei-monthly] Erro: %s", e)


# ── Job: Google Ads daily ───────────────────────────────────────────────────

def job_gads_daily(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[gads-daily] Iniciando analise Google Ads para %s", today)
    try:
        raw = gads.fetch_daily_data(today)
        analysis = analyzer.analyze_google_ads_daily(raw)

        path = pdf_path("gads_daily", today.strftime("%Y-%m-%d"))
        generate_pdf(analysis, path)
        log.info("[gads-daily] PDF gerado: %s", path)

        email_sender.send_google_ads_daily(path, today)
        git_manager.commit_report("gads-daily", today.strftime("%Y-%m-%d"))
        log.info("[gads-daily] Concluido.")

    except Exception as e:
        log.exception("[gads-daily] Erro: %s", e)


# ── Job: Google Ads monthly (every Monday) ─────────────────────────────────

def job_gads_monthly(run_date: date | None = None):
    today = run_date or date.today()
    log.info("[gads-monthly] Iniciando relatorio mensal Google Ads para %s", today)
    try:
        raw = gads.fetch_monthly_period_data(today)
        analysis = analyzer.analyze_google_ads_monthly(raw)

        path = pdf_path("gads_monthly", today.strftime("%Y-%m-%d"))
        generate_pdf(analysis, path)
        log.info("[gads-monthly] PDF gerado: %s", path)

        period_start = today.replace(day=1)
        email_sender.send_google_ads_monthly(path, period_start, today)
        git_manager.commit_report("gads-monthly", today.strftime("%Y-%m-%d"))
        log.info("[gads-monthly] Concluido.")

    except Exception as e:
        log.exception("[gads-monthly] Erro: %s", e)


# ── Monday combined job ─────────────────────────────────────────────────────

def job_monday(run_date: date | None = None):
    """
    Every Monday: runs all four jobs (daily + monthly for both sources).
    The daily jobs still run at 12h daily; the monthly extras are Monday-only.
    """
    today = run_date or date.today()
    job_reportei_daily(today)
    job_reportei_monthly(today)
    job_gads_daily(today)
    job_gads_monthly(today)


# ── Weekday (non-Monday) combined job ───────────────────────────────────────

def job_weekday(run_date: date | None = None):
    today = run_date or date.today()
    job_reportei_daily(today)
    job_gads_daily(today)


# ── Scheduler setup ─────────────────────────────────────────────────────────

def start_scheduler():
    scheduler = BlockingScheduler(timezone=TZ)

    # Mon–Sun daily at 12:00 (non-Monday: only daily reports)
    scheduler.add_job(
        job_weekday,
        trigger=CronTrigger(day_of_week="tue,wed,thu,fri,sat,sun", hour=12, minute=0, timezone=TZ),
        id="weekday_daily",
        name="Relatorios diarios (ter-dom)",
        misfire_grace_time=3600,
    )

    # Every Monday at 12:00 (daily + monthly reports)
    scheduler.add_job(
        job_monday,
        trigger=CronTrigger(day_of_week="mon", hour=12, minute=0, timezone=TZ),
        id="monday_full",
        name="Segunda-feira: diario + mensal",
        misfire_grace_time=3600,
    )

    log.info("Scheduler iniciado. Proximos disparos:")
    for job in scheduler.get_jobs():
        log.info("  - %s: %s", job.name, job.next_run_time)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler encerrado.")


# ── CLI manual trigger ──────────────────────────────────────────────────────

_JOB_MAP = {
    "reportei-daily": job_reportei_daily,
    "reportei-monthly": job_reportei_monthly,
    "gads-daily": job_gads_daily,
    "gads-monthly": job_gads_monthly,
    "all": lambda: (
        job_reportei_daily(),
        job_reportei_monthly(),
        job_gads_daily(),
        job_gads_monthly(),
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
