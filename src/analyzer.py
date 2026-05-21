"""
Turns raw API data into structured analysis: % changes, insights, anomalies.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


ANOMALY_THRESHOLD = 0.20  # 20% change triggers an anomaly flag


@dataclass
class MetricChange:
    name: str
    current: float
    previous: float
    pct_change: float
    is_anomaly: bool
    direction: str  # "up" | "down" | "flat"
    unit: str = ""

    @property
    def formatted_current(self) -> str:
        return _fmt(self.current, self.unit)

    @property
    def formatted_previous(self) -> str:
        return _fmt(self.previous, self.unit)

    @property
    def formatted_pct(self) -> str:
        sign = "+" if self.pct_change >= 0 else ""
        return f"{sign}{self.pct_change:.1f}%"


@dataclass
class AnalysisResult:
    title: str
    period_label: str
    comparison_label: str
    metrics: list[MetricChange] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    top_campaigns: list[dict] = field(default_factory=list)


# ── Core helpers ────────────────────────────────────────────────────────────

def _pct(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return (current - previous) / abs(previous) * 100


def _direction(pct: float) -> str:
    if pct > 1:
        return "up"
    if pct < -1:
        return "down"
    return "flat"


def _fmt(value: float, unit: str) -> str:
    if unit == "R$":
        return f"R$ {value:,.2f}"
    if unit == "%":
        return f"{value:.2f}%"
    if unit == "x":
        return f"{value:.2f}x"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value/1_000:.1f}K"
    return f"{value:,.0f}" if value == int(value) else f"{value:.2f}"


def _make_metric(name: str, current: float, previous: float, unit: str = "") -> MetricChange:
    pct = _pct(current, previous)
    return MetricChange(
        name=name,
        current=current,
        previous=previous,
        pct_change=pct,
        is_anomaly=abs(pct) >= ANOMALY_THRESHOLD * 100,
        direction=_direction(pct),
        unit=unit,
    )


# ── Google Ads analysis ─────────────────────────────────────────────────────

def analyze_google_ads_daily(data: dict) -> AnalysisResult:
    cur = data["current"]
    prev = data["previous"]
    target_date = data["date"]
    prev_date = data["prev_date"]

    metrics = [
        _make_metric("Impressoes", cur["impressions"], prev["impressions"]),
        _make_metric("Cliques", cur["clicks"], prev["clicks"]),
        _make_metric("CTR", cur["ctr"], prev["ctr"], "%"),
        _make_metric("CPC Medio", cur["avg_cpc"], prev["avg_cpc"], "R$"),
        _make_metric("Gasto Total", cur["cost"], prev["cost"], "R$"),
        _make_metric("Conversoes", cur["conversions"], prev["conversions"]),
        _make_metric("Custo/Conversao", cur["cost_per_conversion"], prev["cost_per_conversion"], "R$"),
        _make_metric("ROAS", cur["roas"], prev["roas"], "x"),
    ]

    result = AnalysisResult(
        title="Google Ads — Analise Diaria",
        period_label=target_date.strftime("%d/%m/%Y"),
        comparison_label=prev_date.strftime("%d/%m/%Y"),
        metrics=metrics,
        top_campaigns=data.get("campaigns", [])[:5],
    )

    _generate_google_ads_insights(result, cur, prev)
    return result


def analyze_google_ads_monthly(data: dict) -> AnalysisResult:
    cur = data["current"]
    comp = data["comparison"]
    cp = data["current_period"]
    pp = data["comparison_period"]

    metrics = [
        _make_metric("Impressoes", cur["impressions"], comp["impressions"]),
        _make_metric("Cliques", cur["clicks"], comp["clicks"]),
        _make_metric("CTR", cur["ctr"], comp["ctr"], "%"),
        _make_metric("CPC Medio", cur["avg_cpc"], comp["avg_cpc"], "R$"),
        _make_metric("Gasto Total", cur["cost"], comp["cost"], "R$"),
        _make_metric("Conversoes", cur["conversions"], comp["conversions"]),
        _make_metric("Custo/Conversao", cur["cost_per_conversion"], comp["cost_per_conversion"], "R$"),
        _make_metric("ROAS", cur["roas"], comp["roas"], "x"),
    ]

    result = AnalysisResult(
        title="Google Ads — Relatorio Mensal",
        period_label=f"{cp['start'].strftime('%d/%m')} - {cp['end'].strftime('%d/%m/%Y')}",
        comparison_label=f"{pp['start'].strftime('%d/%m')} - {pp['end'].strftime('%d/%m/%Y')}",
        metrics=metrics,
        top_campaigns=data.get("campaigns", [])[:10],
    )

    _generate_google_ads_insights(result, cur, comp)
    return result


def _generate_google_ads_insights(result: AnalysisResult, cur: dict, prev: dict):
    for m in result.metrics:
        if m.is_anomaly:
            direction_word = "aumentou" if m.direction == "up" else "caiu"
            result.anomalies.append(
                f"ANOMALIA: {m.name} {direction_word} {m.formatted_pct} "
                f"({m.formatted_previous} -> {m.formatted_current})"
            )

    # Positive signals
    if cur["roas"] > 3:
        result.insights.append(f"ROAS excelente: {cur['roas']:.2f}x — campanha gerando bom retorno.")
    elif cur["roas"] > 1:
        result.insights.append(f"ROAS positivo: {cur['roas']:.2f}x — receita acima do gasto.")
    elif cur["roas"] > 0:
        result.insights.append(f"ATENCAO: ROAS baixo ({cur['roas']:.2f}x) — revise a estrategia de conversao.")

    ctr_change = _pct(cur["ctr"], prev["ctr"])
    if ctr_change > 10:
        result.insights.append(f"CTR subiu {ctr_change:.1f}% — criativos mais relevantes ou segmentacao melhorada.")
    elif ctr_change < -10:
        result.insights.append(f"CTR caiu {abs(ctr_change):.1f}% — considere renovar criativos ou revisar segmentacao.")

    cost_change = _pct(cur["cost"], prev["cost"])
    conv_change = _pct(cur["conversions"], prev["conversions"])
    if cost_change > 5 and conv_change < cost_change - 10:
        result.insights.append(
            f"Gasto cresceu {cost_change:.1f}% mas conversoes cresceram apenas {conv_change:.1f}% — "
            "eficiencia caindo."
        )
    elif conv_change > cost_change + 10:
        result.insights.append(
            f"Conversoes cresceram {conv_change:.1f}% com gasto subindo {cost_change:.1f}% — "
            "eficiencia melhorou."
        )


# ── Reportei analysis ───────────────────────────────────────────────────────

# ── Metric label + unit map (reference_key → display name, unit) ─────────────

_METRIC_LABELS = {
    # GA4
    "google_analytics_4:all_sessions":  ("Sessoes", ""),
    "google_analytics_4:total_users":   ("Usuarios Totais", ""),
    "google_analytics_4:new_users":     ("Novos Usuarios", ""),
    "google_analytics_4:all_pageviews": ("Pageviews", ""),
    # Facebook Ads
    "fb_ads:spend":       ("Investimento FB", "R$"),
    "fb_ads:impressions": ("Impressoes FB", ""),
    "fb_ads:clicks":      ("Cliques FB", ""),
    "fb_ads:reach":       ("Alcance FB", ""),
    "fb_ads:ctr":         ("CTR FB", "%"),
    "fb_ads:cpm":         ("CPM FB", "R$"),
    "fb_ads:cpc":         ("CPC FB", "R$"),
    # Google Ads via Reportei
    "gads:impressions":       ("Impressoes GAds", ""),
    "gads:clicks":            ("Cliques GAds", ""),
    "gads:cost_micros":       ("Gasto GAds", "R$"),
    "gads:conversions":       ("Conversoes GAds", ""),
    "gads:ctr":               ("CTR GAds", "%"),
    "gads:average_cpc":       ("CPC Medio GAds", "R$"),
    "gads:roas":              ("ROAS GAds", "x"),
    "gads:cost_per_conversion": ("Custo/Conv GAds", "R$"),
    # Search Console
    "search_console:clicks":      ("Cliques Organicos", ""),
    "search_console:impressions": ("Impressoes Organicas", ""),
    "search_console:ctr":         ("CTR Organico", "%"),
}


def analyze_reportei_daily(data: dict, target_date: Any) -> AnalysisResult:
    """
    data: { integration_name: { "vs_prev_day": {ref_key: {current, comparison, pct_change}},
                                 "vs_last_month": {ref_key: {...}}, ... } }
    """
    date_str = target_date.strftime("%d/%m/%Y") if hasattr(target_date, "strftime") else str(target_date)
    result = AnalysisResult(
        title="Reportei — Analise Diaria",
        period_label=date_str,
        comparison_label="Dia anterior e mesmo dia do mes passado",
    )

    for source_name, int_data in data.items():
        vs_prev = int_data.get("vs_prev_day", {})
        vs_lm   = int_data.get("vs_last_month", {})

        for ref_key, metric_data in vs_prev.items():
            label, unit = _METRIC_LABELS.get(ref_key, (ref_key.split(":")[-1], ""))
            cur  = metric_data.get("current", 0) or 0
            prev = metric_data.get("comparison", 0) or 0

            m = _make_metric(f"{source_name} — {label}", cur, prev, unit)
            result.metrics.append(m)

            if m.is_anomaly:
                direction_word = "subiu" if m.direction == "up" else "caiu"
                result.anomalies.append(
                    f"ANOMALIA [{source_name}]: {label} {direction_word} {m.formatted_pct} vs ontem "
                    f"({m.formatted_previous} → {m.formatted_current})"
                )

            # Also compare vs same day last month
            lm_data = vs_lm.get(ref_key, {})
            lm_prev = lm_data.get("comparison", 0) or 0
            if lm_prev and cur:
                lm_pct = _pct(cur, lm_prev)
                if abs(lm_pct) >= ANOMALY_THRESHOLD * 100:
                    direction_word = "acima" if lm_pct > 0 else "abaixo"
                    result.insights.append(
                        f"{source_name} — {label}: {abs(lm_pct):.1f}% {direction_word} "
                        f"do mesmo dia no mes passado ({_fmt(lm_prev, unit)} → {_fmt(cur, unit)})."
                    )

    _generate_reportei_daily_insights(result, data)
    return result


def analyze_reportei_monthly(data: dict) -> AnalysisResult:
    """
    data: { integration_name: { "data": {ref_key: {current, comparison, pct_change}},
                                  "current_period": {start, end},
                                  "comparison_period": {start, end} } }
    """
    result = AnalysisResult(
        title="Reportei — Relatorio Mensal",
        period_label="",
        comparison_label="",
    )

    for source_name, int_data in data.items():
        cp = int_data.get("current_period", {})
        pp = int_data.get("comparison_period", {})

        if cp and not result.period_label:
            fmt_date = lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)
            result.period_label = f"{fmt_date(cp.get('start'))} - {fmt_date(cp.get('end'))}"
            result.comparison_label = f"{fmt_date(pp.get('start'))} - {fmt_date(pp.get('end'))}"

        metrics_data = int_data.get("data", {})
        for ref_key, metric_data in metrics_data.items():
            label, unit = _METRIC_LABELS.get(ref_key, (ref_key.split(":")[-1], ""))
            cur  = metric_data.get("current", 0) or 0
            comp = metric_data.get("comparison", 0) or 0

            m = _make_metric(f"{source_name} — {label}", cur, comp, unit)
            result.metrics.append(m)

            if m.is_anomaly:
                direction_word = "cresceu" if m.direction == "up" else "caiu"
                result.anomalies.append(
                    f"{source_name}: {label} {direction_word} {m.formatted_pct} vs periodo anterior "
                    f"({m.formatted_previous} → {m.formatted_current})"
                )

    _generate_reportei_monthly_insights(result, data)
    return result


def _generate_reportei_daily_insights(result: AnalysisResult, data: dict):
    """Add high-level narrative insights for daily report."""
    for source_name, int_data in data.items():
        vs_prev = int_data.get("vs_prev_day", {})

        # GA4: sessions trend
        sess = vs_prev.get("google_analytics_4:all_sessions", {})
        if sess:
            cur, prev = sess.get("current", 0), sess.get("comparison", 0)
            if prev and cur:
                chg = _pct(cur, prev)
                if chg > 20:
                    result.insights.append(
                        f"Trafego: sessoes cresceram {chg:.1f}% vs ontem — dia com bom desempenho organico/pago."
                    )
                elif chg < -20:
                    result.insights.append(
                        f"Atencao: sessoes cairam {abs(chg):.1f}% vs ontem — verifique campanhas e status do site."
                    )

        # Google Ads: ROAS check
        roas = vs_prev.get("gads:roas", {})
        if roas:
            cur_roas = roas.get("current", 0)
            if cur_roas and cur_roas < 1:
                result.insights.append("Google Ads: ROAS abaixo de 1 — campanhas gastando mais do que gerando receita.")
            elif cur_roas and cur_roas > 3:
                result.insights.append(f"Google Ads: ROAS excelente ({cur_roas:.2f}x) — retorno muito positivo.")

        # Facebook: CPM spike
        cpm = vs_prev.get("fb_ads:cpm", {})
        if cpm:
            cur_cpm, prev_cpm = cpm.get("current", 0), cpm.get("comparison", 0)
            if prev_cpm and cur_cpm and _pct(cur_cpm, prev_cpm) > 50:
                result.insights.append(
                    f"Facebook Ads: CPM subiu {_pct(cur_cpm, prev_cpm):.1f}% vs ontem "
                    f"(R$ {prev_cpm:.2f} → R$ {cur_cpm:.2f}) — mercado mais disputado hoje."
                )


def _generate_reportei_monthly_insights(result: AnalysisResult, data: dict):
    """Add high-level narrative insights for monthly report."""
    for source_name, int_data in data.items():
        metrics_data = int_data.get("data", {})

        # Compare total ad spend FB + GAds
        fb_spend = (metrics_data.get("fb_ads:spend", {}).get("current") or 0)
        gads_spend = (metrics_data.get("gads:cost_micros", {}).get("current") or 0)
        fb_spend_prev = (metrics_data.get("fb_ads:spend", {}).get("comparison") or 0)
        gads_spend_prev = (metrics_data.get("gads:cost_micros", {}).get("comparison") or 0)

        total_cur = fb_spend + gads_spend
        total_prev = fb_spend_prev + gads_spend_prev
        if total_prev and total_cur:
            chg = _pct(total_cur, total_prev)
            result.insights.append(
                f"Investimento total em ads (FB + GAds): R$ {total_cur:.2f} vs R$ {total_prev:.2f} "
                f"({'+' if chg >= 0 else ''}{chg:.1f}%) no periodo comparado."
            )

        # Organic clicks trend
        sc_clicks = metrics_data.get("search_console:clicks", {})
        if sc_clicks:
            cur, comp = sc_clicks.get("current", 0), sc_clicks.get("comparison", 0)
            if comp and cur:
                chg = _pct(cur, comp)
                if abs(chg) > 10:
                    direction = "crescimento" if chg > 0 else "queda"
                    result.insights.append(
                        f"SEO: {direction} de {abs(chg):.1f}% em cliques organicos no periodo "
                        f"({int(comp)} → {int(cur)} cliques)."
                    )
