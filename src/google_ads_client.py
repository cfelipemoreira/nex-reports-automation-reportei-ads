"""
Google Ads API client — direct integration via google-ads Python library.
Credentials loaded from google-ads.yaml (not in version control).

Public API:
    GoogleAdsDirectClient.fetch_daily(target_date)   -> dict  (for analyze_google_ads_daily)
    GoogleAdsDirectClient.fetch_monthly(target_date) -> dict  (for analyze_google_ads_monthly)
"""
from __future__ import annotations
import os
from datetime import date, timedelta

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH   = os.path.join(BASE_DIR, "google-ads.yaml")
CUSTOMER_ID = "9772636001"


class GoogleAdsDirectClient:
    def __init__(self):
        from google.ads.googleads.client import GoogleAdsClient
        self._client  = GoogleAdsClient.load_from_storage(YAML_PATH)
        self._service = self._client.get_service("GoogleAdsService")

    # ── Core queries ──────────────────────────────────────────────────────────

    def _account_metrics(self, start: date, end: date) -> dict:
        """Aggregated account-level metrics for a date range."""
        query = f"""
            SELECT
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.conversions,
              metrics.conversions_value,
              metrics.ctr,
              metrics.average_cpc,
              metrics.cost_per_conversion
            FROM customer
            WHERE segments.date BETWEEN '{start}' AND '{end}'
        """
        rows = list(self._service.search(customer_id=CUSTOMER_ID, query=query))

        impressions = clicks = cost = conversions = conv_value = 0.0
        for row in rows:
            m = row.metrics
            impressions  += m.impressions
            clicks       += m.clicks
            cost         += m.cost_micros / 1_000_000
            conversions  += m.conversions
            conv_value   += m.conversions_value

        ctr     = (clicks / impressions * 100) if impressions else 0.0
        avg_cpc = (cost / clicks)              if clicks      else 0.0
        cpp     = (cost / conversions)         if conversions else 0.0
        roas    = (conv_value / cost)          if cost        else 0.0

        return {
            "impressions":         impressions,
            "clicks":              clicks,
            "cost":                cost,
            "conversions":         conversions,
            "ctr":                 ctr,
            "avg_cpc":             avg_cpc,
            "cost_per_conversion": cpp,
            "roas":                roas,
        }

    def _top_campaigns(self, start: date, end: date, limit: int = 5) -> list[dict]:
        """Top campaigns by cost for the date range."""
        query = f"""
            SELECT
              campaign.name,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.conversions,
              metrics.ctr
            FROM campaign
            WHERE segments.date BETWEEN '{start}' AND '{end}'
              AND campaign.status = 'ENABLED'
            ORDER BY metrics.cost_micros DESC
            LIMIT {limit}
        """
        rows = list(self._service.search(customer_id=CUSTOMER_ID, query=query))

        # Aggregate by campaign name (multiple date rows possible)
        by_name: dict[str, dict] = {}
        for row in rows:
            name = row.campaign.name
            if name not in by_name:
                by_name[name] = {"name": name, "impressions": 0, "clicks": 0,
                                 "cost": 0.0, "conversions": 0.0}
            m = row.metrics
            by_name[name]["impressions"] += m.impressions
            by_name[name]["clicks"]      += m.clicks
            by_name[name]["cost"]        += m.cost_micros / 1_000_000
            by_name[name]["conversions"] += m.conversions

        result = sorted(by_name.values(), key=lambda x: x["cost"], reverse=True)
        for c in result:
            c["ctr"] = (c["clicks"] / c["impressions"] * 100) if c["impressions"] else 0.0
        return result

    # ── Public API ─────────────────────────────────────────────────────────────

    def fetch_daily(self, target_date: date) -> dict:
        """
        Returns dict compatible with analyzer.analyze_google_ads_daily().
        Compares target_date vs previous day.
        """
        prev_day  = target_date - timedelta(days=1)
        current   = self._account_metrics(target_date, target_date)
        previous  = self._account_metrics(prev_day, prev_day)
        campaigns = self._top_campaigns(target_date, target_date)

        # _raw dict keyed by reference_key for analyzer._analyze_gads()
        raw = {
            "gads:impressions":         {"current": current["impressions"],         "comparison": previous["impressions"]},
            "gads:clicks":              {"current": current["clicks"],              "comparison": previous["clicks"]},
            "gads:cost_micros":         {"current": current["cost"],                "comparison": previous["cost"]},
            "gads:conversions":         {"current": current["conversions"],         "comparison": previous["conversions"]},
            "gads:ctr":                 {"current": current["ctr"],                 "comparison": previous["ctr"]},
            "gads:average_cpc":         {"current": current["avg_cpc"],             "comparison": previous["avg_cpc"]},
            "gads:roas":                {"current": current["roas"],                "comparison": previous["roas"]},
            "gads:cost_per_conversion": {"current": current["cost_per_conversion"], "comparison": previous["cost_per_conversion"]},
        }

        return {
            "date":      target_date,
            "prev_date": prev_day,
            "current":   current,
            "previous":  previous,
            "campaigns": campaigns,
            "_raw":      raw,
        }

    def fetch_monthly(self, target_date: date) -> dict:
        """
        Returns dict compatible with analyzer.analyze_google_ads_monthly().
        Compares 01/month → target_date vs same period last month.
        """
        current_start = target_date.replace(day=1)
        current_end   = target_date

        last_month      = target_date.month - 1 if target_date.month > 1 else 12
        last_month_year = target_date.year if target_date.month > 1 else target_date.year - 1
        comp_start = target_date.replace(year=last_month_year, month=last_month, day=1)
        comp_end   = target_date.replace(year=last_month_year, month=last_month)

        current    = self._account_metrics(current_start, current_end)
        comparison = self._account_metrics(comp_start, comp_end)
        campaigns  = self._top_campaigns(current_start, current_end)

        return {
            "current_period":    {"start": current_start, "end": current_end},
            "comparison_period": {"start": comp_start,    "end": comp_end},
            "current":           current,
            "comparison":        comparison,
            "campaigns":         campaigns,
        }
