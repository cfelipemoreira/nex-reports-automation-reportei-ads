"""
Reportei API v2 client.

Metric definitions use real UUIDs discovered from
GET /v2/metrics?integration_slug=<slug>.
Each call to metrics/get-data returns current + comparison data in one request.
"""
import requests
from datetime import date, timedelta
from config import config


# ── Integration IDs (Nex Coworking, project 458229) ─────────────────────────
INTEGRATION_RDSTATION     = 1351098
INTEGRATION_GA4           = 1421205
INTEGRATION_FACEBOOK_ADS  = 1421204
INTEGRATION_INSTAGRAM     = 1421200
INTEGRATION_GADS          = 1979996   # Google Ads — NEX.WORK
INTEGRATION_SEARCH_CONSOLE = 2002611
INTEGRATION_LINKEDIN      = 3042799

DASHBOARD_WEEKLY_TT_ID    = 2874248

# ── Metric definitions per integration ──────────────────────────────────────
# Format: list of dicts ready for the metrics[] array in the API payload.

METRICS_GA4 = [
    {"id": "4a9cc55e-27e8-41db-b173-f8e2c71f29aa",
     "reference_key": "google_analytics_4:all_sessions",
     "component": "number_v1", "metrics": ["sessions"], "type": []},
    {"id": "ca8b874f-deed-442b-9082-bd3bbe3fe346",
     "reference_key": "google_analytics_4:total_users",
     "component": "number_v1", "metrics": ["totalUsers"], "type": []},
    {"id": "20b0fecb-24b6-4b13-aedc-8ad625614ca1",
     "reference_key": "google_analytics_4:new_users",
     "component": "number_v1", "metrics": ["newUsers"], "type": []},
    {"id": "31431e55-0ea3-438f-ae2b-314acd45c52c",
     "reference_key": "google_analytics_4:all_pageviews",
     "component": "number_v1", "metrics": ["screenPageViews"], "type": []},
]

METRICS_FACEBOOK_ADS = [
    {"id": "bec746ab-834b-4dc6-8d90-bd0882101a64",
     "reference_key": "fb_ads:spend",
     "component": "number_v1", "metrics": ["spend"], "type": ["spend"]},
    {"id": "dda3ace2-c5f7-4929-bfc6-28b9dc87267e",
     "reference_key": "fb_ads:impressions",
     "component": "number_v1", "metrics": ["impressions"], "type": "impressions"},
    {"id": "582e012d-e776-4adc-8ea7-e87fda4f85fe",
     "reference_key": "fb_ads:clicks",
     "component": "number_v1", "metrics": ["clicks"], "type": "clicks"},
    {"id": "8368e2b8-9647-4114-ac40-e13a3548cdd4",
     "reference_key": "fb_ads:reach",
     "component": "number_v1", "metrics": ["reach"], "type": "reach"},
    {"id": "2c6fc3f6-5ad9-4124-82f9-ea9b295ca5a2",
     "reference_key": "fb_ads:ctr",
     "component": "number_v1", "metrics": ["ctr"], "type": []},
    {"id": "8f673ff2-8827-4537-b58a-0ad142670219",
     "reference_key": "fb_ads:cpm",
     "component": "number_v1", "metrics": ["cpm"], "type": []},
    {"id": "d5c6247f-7871-4a56-90db-36f8cd269e90",
     "reference_key": "fb_ads:cpc",
     "component": "number_v1", "metrics": ["cpc"], "type": []},
]

METRICS_GADS = [
    {"id": "d5934cb7-a5b7-4c30-bda8-c9558db88b0d",
     "reference_key": "gads:impressions",
     "component": "number_v1", "metrics": ["metrics.impressions"], "type": "impressions"},
    {"id": "e9a2bc46-6bce-45ba-80dc-a90375a61b43",
     "reference_key": "gads:clicks",
     "component": "number_v1", "metrics": ["metrics.clicks"], "type": "clicks"},
    {"id": "2ec9f1a8-ec88-4d4d-8fc2-f1e8626525b8",
     "reference_key": "gads:cost_micros",
     "component": "number_v1", "metrics": ["metrics.cost_micros"], "type": ["spend"]},
    {"id": "67eebf45-4317-4047-bd2b-e797f588f5a0",
     "reference_key": "gads:conversions",
     "component": "number_v1", "metrics": ["metrics.conversions"], "type": "conversion"},
    {"id": "088d2f9c-02b6-40e7-a861-d496a8c4f051",
     "reference_key": "gads:ctr",
     "component": "number_v1", "metrics": ["metrics.ctr"], "type": []},
    {"id": "3961804b-1d07-40f5-b5bf-4a7c6791649a",
     "reference_key": "gads:average_cpc",
     "component": "number_v1", "metrics": ["metrics.average_cpc"], "type": []},
    {"id": "4299471c-80a1-4fda-9a2a-57ac924ad8b1",
     "reference_key": "gads:roas",
     "component": "number_v1", "metrics": ["metrics.roas"], "type": []},
    {"id": "9eab9377-d277-4ac0-819a-cebb4599bb09",
     "reference_key": "gads:cost_per_conversion",
     "component": "number_v1", "metrics": ["metrics.cost_per_conversion"], "type": []},
]

METRICS_SEARCH_CONSOLE = [
    {"id": "sc-clicks-001", "reference_key": "search_console:clicks",
     "component": "number_v1", "metrics": ["clicks"], "type": ["clicks"]},
    {"id": "sc-impr-002", "reference_key": "search_console:impressions",
     "component": "number_v1", "metrics": ["impressions"], "type": ["impressions"]},
    {"id": "sc-ctr-003", "reference_key": "search_console:ctr",
     "component": "number_v1", "metrics": ["ctr"], "type": ["ctr"]},
]

# All integrations that make up [WEEKLY] TT, with their metric definitions
DASHBOARD_INTEGRATIONS = [
    {"id": INTEGRATION_GA4,            "name": "GA4 — Sessoes e Trafego",   "metrics": METRICS_GA4},
    {"id": INTEGRATION_FACEBOOK_ADS,   "name": "Facebook Ads — NEX Curitiba","metrics": METRICS_FACEBOOK_ADS},
    {"id": INTEGRATION_GADS,           "name": "Google Ads — NEX.WORK",      "metrics": METRICS_GADS},
    {"id": INTEGRATION_SEARCH_CONSOLE, "name": "Search Console — nex.work",  "metrics": METRICS_SEARCH_CONSOLE},
]


class ReporteiClient:
    def __init__(self):
        self.base_url = config.REPORTEI_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {config.REPORTEI_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        resp = requests.post(
            f"{self.base_url}{path}",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Core fetch ──────────────────────────────────────────────────────────

    def get_metrics(
        self,
        integration_id: int,
        start: date,
        end: date,
        metrics: list[dict],
        comparison_start: date | None = None,
        comparison_end: date | None = None,
    ) -> dict:
        """
        Calls POST /v2/metrics/get-data and returns a flat dict:
          { reference_key: {"current": float, "comparison": float | None, "pct": float | None} }
        """
        payload = {
            "integration_id": integration_id,
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "metrics": metrics,
        }
        if comparison_start and comparison_end:
            payload["comparison_start"] = comparison_start.strftime("%Y-%m-%d")
            payload["comparison_end"] = comparison_end.strftime("%Y-%m-%d")

        raw = self._post("/metrics/get-data", payload)
        return self._parse_response(raw.get("data", {}), metrics)

    @staticmethod
    def _parse_response(data: dict, metrics: list[dict]) -> dict:
        """Maps UUID keys back to reference_keys, extracting current + comparison values."""
        id_to_ref = {m["id"]: m["reference_key"] for m in metrics}
        result = {}
        for uuid, payload in data.items():
            ref = id_to_ref.get(uuid, uuid)
            if isinstance(payload, dict) and "message" not in payload:
                current = _to_float(payload.get("values"))
                comp_data = payload.get("comparison") or {}
                comparison = _to_float(comp_data.get("values")) if comp_data else None
                pct = comp_data.get("difference") if comp_data else None
                result[ref] = {
                    "current": current,
                    "comparison": comparison,
                    "pct_change": pct,
                }
        return result

    # ── High-level helpers ──────────────────────────────────────────────────

    def fetch_daily_data(self, target_date: date) -> dict:
        """
        Fetches all [WEEKLY] TT integrations for target_date,
        comparing with previous day AND same day last month (two comparison calls).
        Returns: { integration_name: { "vs_prev_day": {...}, "vs_last_month": {...} } }
        """
        prev_day = target_date - timedelta(days=1)

        last_month = target_date.month - 1 if target_date.month > 1 else 12
        last_month_year = target_date.year if target_date.month > 1 else target_date.year - 1
        same_day_last_month = target_date.replace(year=last_month_year, month=last_month)

        results = {}
        for integration in DASHBOARD_INTEGRATIONS:
            int_id = integration["id"]
            name = integration["name"]
            metrics = integration["metrics"]

            vs_prev = self.get_metrics(int_id, target_date, target_date, metrics,
                                       comparison_start=prev_day, comparison_end=prev_day)
            vs_lm = self.get_metrics(int_id, target_date, target_date, metrics,
                                     comparison_start=same_day_last_month,
                                     comparison_end=same_day_last_month)

            results[name] = {
                "integration_id": int_id,
                "vs_prev_day": vs_prev,
                "vs_last_month": vs_lm,
                "prev_day": prev_day,
                "same_day_last_month": same_day_last_month,
            }

        return results

    def fetch_monthly_period_data(self, target_date: date) -> dict:
        """
        Fetches 01/month → target_date, compared with same period last month.
        Returns: { integration_name: { "current": {...}, "comparison": {...} } }
        """
        current_start = target_date.replace(day=1)
        current_end = target_date

        last_month = target_date.month - 1 if target_date.month > 1 else 12
        last_month_year = target_date.year if target_date.month > 1 else target_date.year - 1
        comparison_start = target_date.replace(year=last_month_year, month=last_month, day=1)
        comparison_end = target_date.replace(year=last_month_year, month=last_month)

        results = {}
        for integration in DASHBOARD_INTEGRATIONS:
            int_id = integration["id"]
            name = integration["name"]
            metrics = integration["metrics"]

            data = self.get_metrics(int_id, current_start, current_end, metrics,
                                    comparison_start=comparison_start,
                                    comparison_end=comparison_end)

            results[name] = {
                "integration_id": int_id,
                "data": data,
                "current_period": {"start": current_start, "end": current_end},
                "comparison_period": {"start": comparison_start, "end": comparison_end},
            }

        return results


def _to_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
