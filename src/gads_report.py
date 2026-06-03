"""
Google Ads full report generator.

Produces a single self-contained HTML (print-optimised, A4)
combining daily + monthly data with critical analysis,
attention points, opportunities, and campaign breakdown.

Public API:
    build_gads_report(daily_data, monthly_data, report_date) -> str  (HTML string)
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Any


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pct(current: float, previous: float) -> float:
    if not previous:
        return 100.0 if current > 0 else 0.0
    return (current - previous) / abs(previous) * 100


def _arrow(pct: float) -> str:
    if pct > 1:  return "&#9650;"   # ▲
    if pct < -1: return "&#9660;"   # ▼
    return "&#8212;"                 # —


def _badge(pct: float, positive_dir: str = "up") -> str:
    """Returns CSS class for a change badge."""
    if abs(pct) <= 1:
        return "badge-flat"
    going_up = pct > 0
    good = (going_up and positive_dir == "up") or (not going_up and positive_dir == "down")
    return "badge-good" if good else "badge-bad"


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}"


def _fmt_num(v: float) -> str:
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if v >= 1_000:     return f"{v/1_000:.1f}K"
    return f"{v:,.0f}" if v == int(v) else f"{v:.1f}"


def _fmt_pct_val(v: float) -> str:
    return f"{v:.2f}%"


def _fmt_x(v: float) -> str:
    return f"{v:.2f}x"


def _signed(pct: float) -> str:
    s = "+" if pct >= 0 else ""
    return f"{s}{pct:.1f}%"


# ── Analysis engine ───────────────────────────────────────────────────────────

def _analyse(daily: dict, monthly: dict) -> dict:
    """Derive all insights, attention points and opportunities."""
    dc  = daily["current"]
    dp  = daily["previous"]
    mc  = monthly["current"]
    mp  = monthly["comparison"]

    # Daily deltas
    d_impr  = _pct(dc["impressions"],         dp["impressions"])
    d_click = _pct(dc["clicks"],              dp["clicks"])
    d_cost  = _pct(dc["cost"],                dp["cost"])
    d_conv  = _pct(dc["conversions"],         dp["conversions"])
    d_ctr   = _pct(dc["ctr"],                 dp["ctr"])
    d_cpc   = _pct(dc["avg_cpc"],             dp["avg_cpc"])
    d_roas  = _pct(dc["roas"],                dp["roas"])
    d_cpp   = _pct(dc["cost_per_conversion"], dp["cost_per_conversion"])

    # Monthly deltas
    m_impr  = _pct(mc["impressions"],         mp["impressions"])
    m_click = _pct(mc["clicks"],              mp["clicks"])
    m_cost  = _pct(mc["cost"],                mp["cost"])
    m_conv  = _pct(mc["conversions"],         mp["conversions"])
    m_ctr   = _pct(mc["ctr"],                 mp["ctr"])
    m_cpc   = _pct(mc["avg_cpc"],             mp["avg_cpc"])
    m_roas  = _pct(mc["roas"],                mp["roas"])
    m_cpp   = _pct(mc["cost_per_conversion"], mp["cost_per_conversion"])

    attention = []
    opportunities = []
    actions = []

    # ── Attention points ──────────────────────────────────────────────────────

    if dc["roas"] > 0 and dc["roas"] < 1:
        attention.append(
            f"ROAS diario abaixo de 1 ({_fmt_x(dc['roas'])}) — campanha gerando menos receita do que custa hoje."
        )
    if mc["roas"] > 0 and mc["roas"] < 1:
        attention.append(
            f"ROAS mensal abaixo de 1 ({_fmt_x(mc['roas'])}) — acumulado do mes com ROI negativo."
        )

    if d_conv < -20 and d_cost > 5:
        attention.append(
            f"Conversoes caindo {_signed(d_conv)} enquanto gasto subiu {_signed(d_cost)} — deterioracao de eficiencia no dia."
        )
    if m_conv < -20 and m_cost > 5:
        attention.append(
            f"Conversoes mensais caindo {_signed(m_conv)} com gasto +{_signed(m_cost)} — revisar estrategia de conversao."
        )

    if dc["ctr"] > 0 and dc["ctr"] < 2.0:
        attention.append(
            f"CTR diario abaixo de 2% ({_fmt_pct_val(dc['ctr'])}) — anuncios com baixa relevancia ou alta competicao."
        )

    if d_cpc > 25:
        attention.append(
            f"CPC subiu {_signed(d_cpc)} vs ontem ({_fmt_brl(dp['avg_cpc'])} → {_fmt_brl(dc['avg_cpc'])}) — lances mais caros."
        )
    if m_cpc > 20:
        attention.append(
            f"CPC medio mensal subiu {_signed(m_cpc)} — tendencia de custo por clique em alta no mes."
        )

    if mc["cost_per_conversion"] > 0 and mc["cost_per_conversion"] > 500:
        attention.append(
            f"Custo por conversao mensal elevado ({_fmt_brl(mc['cost_per_conversion'])}) — avaliar qualidade das conversoes rastreadas."
        )

    if d_impr > 30 and d_ctr < -15:
        attention.append(
            f"Impressoes +{_signed(d_impr)} mas CTR caiu {_signed(d_ctr)} — alcance maior porem menos relevante."
        )

    if not dc["conversions"] and dc["cost"] > 100:
        attention.append(
            f"Nenhuma conversao registrada hoje com {_fmt_brl(dc['cost'])} investidos — verificar rastreamento."
        )

    # ── Opportunities ─────────────────────────────────────────────────────────

    if dc["roas"] > 3:
        opportunities.append(
            f"ROAS diario excelente ({_fmt_x(dc['roas'])}) — bom momento para ampliar orcamento nas campanhas ativas."
        )
    elif mc["roas"] > 3:
        opportunities.append(
            f"ROAS mensal solido ({_fmt_x(mc['roas'])}) — considere escalar campanhas com melhor desempenho."
        )

    if d_conv > 20 and d_cost <= d_conv + 10:
        opportunities.append(
            f"Conversoes +{_signed(d_conv)} com custo proporcional — eficiencia melhorando, bom momento para escalar."
        )

    if m_cpc < -10:
        opportunities.append(
            f"CPC mensal caindo {_signed(m_cpc)} — oportunidade de aumentar volume de cliques mantendo eficiencia de custo."
        )

    if d_ctr > 20:
        opportunities.append(
            f"CTR subiu {_signed(d_ctr)} hoje — criativos com boa ressonancia, avaliar expansao de public-alvo."
        )

    if mc["ctr"] > 5:
        opportunities.append(
            f"CTR mensal de {_fmt_pct_val(mc['ctr'])} — acima da media do mercado (3-5%), campanhas muito relevantes."
        )

    if m_impr > 20 and m_click > 15:
        opportunities.append(
            f"Crescimento organico de alcance (+{_signed(m_impr)} impressoes, +{_signed(m_click)} cliques) — momentum positivo no mes."
        )

    if not opportunities:
        opportunities.append("Manter configuracoes atuais e acompanhar evolucao diaria para identificar momentos de escala.")

    # ── Recommended actions ───────────────────────────────────────────────────

    if dc["roas"] > 0 and dc["roas"] < 1:
        actions.append("Auditar campanhas com ROAS < 1: pausar grupos de anuncios ineficientes e redirecionar orcamento.")
    if dc["ctr"] < 2.0 and dc["impressions"] > 200:
        actions.append("Revisar textos de anuncio e extensoes para melhorar CTR — testar novas copias com CTA mais direto.")
    if d_cpc > 20:
        actions.append("Revisar estrategia de lances — considerar tCPA ou tROAS para controlar custo por clique.")
    if d_conv < -20:
        actions.append("Checar rastreamento de conversoes no Google Tag Manager e revisar landing pages.")
    if mc["cost"] > 0 and not mc["conversions"]:
        actions.append("Zero conversoes no mes: verificar integracao de rastreamento e validar eventos de conversao.")
    if not actions:
        actions.append("Manter mix de campanhas atual e ampliar orcamento nas campanhas com ROAS acima de 3x.")
        actions.append("Agendar revisao semanal de lances e negativar termos irrelevantes para manter CTR saudavel.")

    return {
        "daily_deltas":  dict(d_impr=d_impr, d_click=d_click, d_cost=d_cost,
                               d_conv=d_conv, d_ctr=d_ctr, d_cpc=d_cpc,
                               d_roas=d_roas, d_cpp=d_cpp),
        "monthly_deltas": dict(m_impr=m_impr, m_click=m_click, m_cost=m_cost,
                                m_conv=m_conv, m_ctr=m_ctr, m_cpc=m_cpc,
                                m_roas=m_roas, m_cpp=m_cpp),
        "attention":     attention,
        "opportunities": opportunities,
        "actions":       actions,
    }


# ── HTML builder ──────────────────────────────────────────────────────────────

def _metric_card(label: str, value: str, prev: str, pct: float, pos_dir: str = "up") -> str:
    bc   = _badge(pct, pos_dir)
    arr  = _arrow(pct)
    sign = "+" if pct >= 0 else ""
    return f"""
      <div class="mc">
        <div class="mc-label">{label}</div>
        <div class="mc-value">{value}</div>
        <div class="mc-footer">
          <span class="mc-prev">ant: {prev}</span>
          <span class="badge {bc}">{arr} {sign}{pct:.1f}%</span>
        </div>
      </div>"""


def _row_delta(label: str, cur: str, prev: str, pct: float, pos_dir: str = "up") -> str:
    bc  = _badge(pct, pos_dir)
    arr = _arrow(pct)
    sign = "+" if pct >= 0 else ""
    return f"""
        <tr>
          <td class="td-label">{label}</td>
          <td class="td-cur">{cur}</td>
          <td class="td-prev">{prev}</td>
          <td><span class="badge {bc}">{arr} {sign}{pct:.1f}%</span></td>
        </tr>"""


def _campaign_row(c: dict, i: int) -> str:
    shade = ' style="background:#f8f9fc"' if i % 2 == 0 else ""
    return f"""
        <tr{shade}>
          <td class="td-label">{c['name'][:52]}</td>
          <td class="td-num">{_fmt_num(c['impressions'])}</td>
          <td class="td-num">{_fmt_num(c['clicks'])}</td>
          <td class="td-num">{_fmt_pct_val(c['ctr'])}</td>
          <td class="td-num">{_fmt_brl(c['cost'])}</td>
          <td class="td-num">{c['conversions']:.0f}</td>
        </tr>"""


def build_gads_report(daily_data: dict, monthly_data: dict, report_date: date) -> str:
    dc  = daily_data["current"]
    dp  = daily_data["previous"]
    mc  = monthly_data["current"]
    mp  = monthly_data["comparison"]
    campaigns = daily_data.get("campaigns") or monthly_data.get("campaigns") or []

    prev_date  = daily_data.get("prev_date", report_date)
    cp = monthly_data.get("current_period",    {})
    pp = monthly_data.get("comparison_period", {})
    fmt = lambda d: d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)

    analysis = _analyse(daily_data, monthly_data)
    dd = analysis["daily_deltas"]
    md = analysis["monthly_deltas"]
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── KPI scorecards (daily) ─────────────────────────────────────────────────
    cards = (
        _metric_card("Impressoes",  _fmt_num(dc["impressions"]),  _fmt_num(dp["impressions"]),  dd["d_impr"])  +
        _metric_card("Cliques",     _fmt_num(dc["clicks"]),       _fmt_num(dp["clicks"]),       dd["d_click"]) +
        _metric_card("Investimento",_fmt_brl(dc["cost"]),         _fmt_brl(dp["cost"]),         dd["d_cost"],  "neutral") +
        _metric_card("Conversoes",  _fmt_num(dc["conversions"]),  _fmt_num(dp["conversions"]),  dd["d_conv"])  +
        _metric_card("CTR",         _fmt_pct_val(dc["ctr"]),      _fmt_pct_val(dp["ctr"]),      dd["d_ctr"])   +
        _metric_card("CPC Medio",   _fmt_brl(dc["avg_cpc"]),      _fmt_brl(dp["avg_cpc"]),      dd["d_cpc"],   "down") +
        _metric_card("ROAS",        _fmt_x(dc["roas"]),           _fmt_x(dp["roas"]),           dd["d_roas"])  +
        _metric_card("Custo/Conv",  _fmt_brl(dc["cost_per_conversion"]), _fmt_brl(dp["cost_per_conversion"]), dd["d_cpp"], "down")
    )

    # ── Daily comparison table ─────────────────────────────────────────────────
    daily_rows = (
        _row_delta("Impressoes",   _fmt_num(dc["impressions"]),  _fmt_num(dp["impressions"]),  dd["d_impr"])  +
        _row_delta("Cliques",      _fmt_num(dc["clicks"]),       _fmt_num(dp["clicks"]),       dd["d_click"]) +
        _row_delta("Investimento", _fmt_brl(dc["cost"]),         _fmt_brl(dp["cost"]),         dd["d_cost"],  "neutral") +
        _row_delta("Conversoes",   _fmt_num(dc["conversions"]),  _fmt_num(dp["conversions"]),  dd["d_conv"])  +
        _row_delta("CTR",          _fmt_pct_val(dc["ctr"]),      _fmt_pct_val(dp["ctr"]),      dd["d_ctr"])   +
        _row_delta("CPC Medio",    _fmt_brl(dc["avg_cpc"]),      _fmt_brl(dp["avg_cpc"]),      dd["d_cpc"],   "down") +
        _row_delta("ROAS",         _fmt_x(dc["roas"]),           _fmt_x(dp["roas"]),           dd["d_roas"])  +
        _row_delta("Custo/Conv",   _fmt_brl(dc["cost_per_conversion"]), _fmt_brl(dp["cost_per_conversion"]), dd["d_cpp"], "down")
    )

    # ── Monthly comparison table ───────────────────────────────────────────────
    monthly_rows = (
        _row_delta("Impressoes",   _fmt_num(mc["impressions"]),  _fmt_num(mp["impressions"]),  md["m_impr"])  +
        _row_delta("Cliques",      _fmt_num(mc["clicks"]),       _fmt_num(mp["clicks"]),       md["m_click"]) +
        _row_delta("Investimento", _fmt_brl(mc["cost"]),         _fmt_brl(mp["cost"]),         md["m_cost"],  "neutral") +
        _row_delta("Conversoes",   _fmt_num(mc["conversions"]),  _fmt_num(mp["conversions"]),  md["m_conv"])  +
        _row_delta("CTR",          _fmt_pct_val(mc["ctr"]),      _fmt_pct_val(mp["ctr"]),      md["m_ctr"])   +
        _row_delta("CPC Medio",    _fmt_brl(mc["avg_cpc"]),      _fmt_brl(mp["avg_cpc"]),      md["m_cpc"],   "down") +
        _row_delta("ROAS",         _fmt_x(mc["roas"]),           _fmt_x(mp["roas"]),           md["m_roas"])  +
        _row_delta("Custo/Conv",   _fmt_brl(mc["cost_per_conversion"]), _fmt_brl(mp["cost_per_conversion"]), md["m_cpp"], "down")
    )

    # ── Campaign table ─────────────────────────────────────────────────────────
    campaign_rows = "".join(_campaign_row(c, i) for i, c in enumerate(campaigns))
    campaign_section = f"""
    <div class="section">
      <div class="section-title">
        <span class="dot dot-ads"></span> Top Campanhas — {fmt(report_date)}
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th class="th-label">Campanha</th>
            <th class="th-num">Impressoes</th>
            <th class="th-num">Cliques</th>
            <th class="th-num">CTR</th>
            <th class="th-num">Investimento</th>
            <th class="th-num">Conversoes</th>
          </tr>
        </thead>
        <tbody>{campaign_rows}</tbody>
      </table>
    </div>""" if campaigns else ""

    # ── Attention / Opportunity / Actions lists ────────────────────────────────
    def _li_list(items: list[str], cls: str) -> str:
        return "".join(f'<li class="{cls}">{item}</li>' for item in items)

    attention_lis    = _li_list(analysis["attention"],     "li-att")    or '<li class="li-none">Nenhum ponto critico identificado.</li>'
    opportunity_lis  = _li_list(analysis["opportunities"], "li-opp")
    actions_lis      = _li_list(analysis["actions"],       "li-act")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Google Ads — Relatorio Completo {fmt(report_date)}</title>
  <style>
    /* ── Reset ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    @page {{ size: A4; margin: 14mm 14mm 16mm; }}
    html, body {{
      font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
      font-size: 11px;
      color: #1a1a2e;
      background: #fff;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    /* ── Header ── */
    .header {{
      background: #1a1a2e;
      color: #fff;
      padding: 18px 24px 14px;
      border-radius: 8px 8px 0 0;
      margin-bottom: 0;
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }}
    .header-brand {{
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: rgba(255,255,255,0.5);
      margin-bottom: 6px;
    }}
    .header-title {{
      font-size: 20px;
      font-weight: 800;
      line-height: 1.1;
    }}
    .header-subtitle {{
      font-size: 11px;
      color: rgba(255,255,255,0.65);
      margin-top: 4px;
    }}
    .header-meta {{
      text-align: right;
      font-size: 10px;
      color: rgba(255,255,255,0.5);
      line-height: 1.8;
    }}
    .header-meta strong {{ color: rgba(255,255,255,0.85); }}

    /* ── KPI strip ── */
    .kpi-strip {{
      background: #f0f4ff;
      border: 1px solid #d0d9f0;
      border-top: none;
      padding: 14px 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .mc {{
      flex: 1 1 140px;
      background: #fff;
      border: 1px solid #e0e4f0;
      border-radius: 6px;
      padding: 10px 12px;
    }}
    .mc-label {{
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #6b6b90;
      margin-bottom: 5px;
    }}
    .mc-value {{
      font-size: 18px;
      font-weight: 800;
      color: #1a1a2e;
      line-height: 1;
      margin-bottom: 6px;
    }}
    .mc-footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 4px;
    }}
    .mc-prev {{
      font-size: 9px;
      color: #a0a0b8;
    }}

    /* ── Badges ── */
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 2px;
      padding: 2px 6px;
      border-radius: 10px;
      font-size: 9.5px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .badge-good    {{ background: #e6f4ea; color: #1a7a3c; }}
    .badge-bad     {{ background: #fce8e6; color: #b71c1c; }}
    .badge-flat    {{ background: #f1f3f4; color: #6b6b80; }}
    .badge-neutral {{ background: #e8f0fe; color: #1967d2; }}

    /* ── Sections ── */
    .section {{
      border: 1px solid #e0e4f0;
      border-top: none;
      padding: 14px 16px;
      page-break-inside: avoid;
    }}
    .section:last-child {{ border-radius: 0 0 8px 8px; }}
    .section-title {{
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #1a1a2e;
      margin-bottom: 12px;
      padding-bottom: 7px;
      border-bottom: 1px solid #e8eaf0;
    }}
    .dot {{
      width: 9px; height: 9px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .dot-ads   {{ background: #34A853; }}
    .dot-warn  {{ background: #f59e0b; }}
    .dot-opp   {{ background: #3b82f6; }}
    .dot-act   {{ background: #7c3aed; }}

    /* ── Two-column layout ── */
    .two-col {{
      display: flex;
      gap: 16px;
    }}
    .col {{
      flex: 1;
    }}
    .col-title {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: #6b6b90;
      margin-bottom: 8px;
    }}

    /* ── Data table ── */
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 10px;
    }}
    .data-table thead tr {{
      background: #1a1a2e;
      color: #fff;
    }}
    .th-label {{
      text-align: left;
      padding: 6px 8px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .th-num {{
      text-align: right;
      padding: 6px 8px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}
    .td-label {{
      padding: 5px 8px;
      color: #2d3748;
      font-weight: 600;
    }}
    .td-cur {{
      padding: 5px 8px;
      text-align: right;
      font-weight: 700;
      color: #1a1a2e;
    }}
    .td-prev {{
      padding: 5px 8px;
      text-align: right;
      color: #9b9bae;
    }}
    .td-num {{
      padding: 5px 8px;
      text-align: right;
      color: #2d3748;
    }}
    .data-table td:last-child {{ text-align: right; padding: 5px 8px; }}
    .data-table tbody tr:nth-child(even) {{ background: #f8f9fc; }}

    /* ── Analysis lists ── */
    .analysis-list {{
      list-style: none;
      padding: 0;
    }}
    .analysis-list li {{
      padding: 7px 10px 7px 28px;
      position: relative;
      border-radius: 5px;
      margin-bottom: 5px;
      font-size: 10.5px;
      line-height: 1.45;
    }}
    .analysis-list li::before {{
      position: absolute;
      left: 10px;
      top: 8px;
      font-size: 9px;
      font-weight: 900;
    }}
    .li-att {{
      background: #fffbf0;
      border-left: 3px solid #f59e0b;
      color: #78350f;
    }}
    .li-att::before {{ content: "!"; color: #d97706; }}
    .li-opp {{
      background: #eff6ff;
      border-left: 3px solid #3b82f6;
      color: #1e3a8a;
    }}
    .li-opp::before {{ content: "+"; color: #2563eb; }}
    .li-act {{
      background: #f5f3ff;
      border-left: 3px solid #7c3aed;
      color: #4c1d95;
    }}
    .li-act::before {{ content: "&#9658;"; color: #7c3aed; }}
    .li-none {{
      background: #f0faf4;
      border-left: 3px solid #28a745;
      color: #155724;
    }}
    .li-none::before {{ content: "&#10003;"; color: #28a745; }}

    /* ── Period label ── */
    .period-label {{
      font-size: 9px;
      color: #9b9bae;
      font-style: italic;
      margin-bottom: 8px;
    }}

    /* ── Footer ── */
    .footer {{
      margin-top: 14px;
      text-align: center;
      font-size: 9px;
      color: #b0b0c8;
    }}

    /* ── Print breaks ── */
    .page-break {{ page-break-before: always; }}
  </style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="header-top">
      <div>
        <div class="header-brand">NEX Coworking &mdash; Google Ads</div>
        <div class="header-title">Relatorio Completo de Performance</div>
        <div class="header-subtitle">Analise critica diaria e mensal — conta NEX.WORK (977-263-6001)</div>
      </div>
      <div class="header-meta">
        <strong>{fmt(report_date)}</strong><br>
        Gerado: {generated}<br>
        ID: 977-263-6001
      </div>
    </div>
  </div>

  <!-- KPI Strip (daily) -->
  <div class="kpi-strip">
    {cards}
  </div>

  <!-- Daily vs Yesterday -->
  <div class="section">
    <div class="section-title">
      <span class="dot dot-ads"></span> Performance Diaria — {fmt(report_date)} vs {fmt(prev_date)}
    </div>
    <table class="data-table">
      <thead>
        <tr>
          <th class="th-label">Metrica</th>
          <th class="th-num">{fmt(report_date)}</th>
          <th class="th-num">{fmt(prev_date)}</th>
          <th class="th-num">Variacao</th>
        </tr>
      </thead>
      <tbody>{daily_rows}</tbody>
    </table>
  </div>

  <!-- Monthly MTD -->
  <div class="section">
    <div class="section-title">
      <span class="dot dot-ads"></span> Performance Mensal (MTD) — {fmt(cp.get('start',''))} a {fmt(cp.get('end',''))}
    </div>
    <div class="period-label">Comparado com: {fmt(pp.get('start',''))} a {fmt(pp.get('end',''))}</div>
    <table class="data-table">
      <thead>
        <tr>
          <th class="th-label">Metrica</th>
          <th class="th-num">Mes Atual</th>
          <th class="th-num">Mes Anterior</th>
          <th class="th-num">Variacao</th>
        </tr>
      </thead>
      <tbody>{monthly_rows}</tbody>
    </table>
  </div>

  <!-- Campaigns -->
  {campaign_section}

  <!-- Attention Points -->
  <div class="section">
    <div class="section-title">
      <span class="dot dot-warn"></span> Pontos de Atencao
    </div>
    <ul class="analysis-list">
      {attention_lis}
    </ul>
  </div>

  <!-- Opportunities -->
  <div class="section">
    <div class="section-title">
      <span class="dot dot-opp"></span> Oportunidades Identificadas
    </div>
    <ul class="analysis-list">
      {opportunity_lis}
    </ul>
  </div>

  <!-- Actions -->
  <div class="section">
    <div class="section-title">
      <span class="dot dot-act"></span> Acoes Recomendadas
    </div>
    <ul class="analysis-list">
      {actions_lis}
    </ul>
  </div>

  <div class="footer">
    NEX Coworking &bull; Relatorio automatico &bull; felipe@nexcoworking.com.br &bull; {generated}
  </div>

</body>
</html>"""
