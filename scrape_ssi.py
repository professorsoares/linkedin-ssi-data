#!/usr/bin/env python3
"""
LinkedIn SSI Scraper
Coleta automaticamente os dados do SSI usando a sua sessão do LinkedIn.

Primeira execução:
  python scrape_ssi.py          → abre browser para login, salva sessão
Execuções seguintes:
  python scrape_ssi.py          → usa sessão salva, coleta e gera CSV
  python scrape_ssi.py --login  → força novo login (sessão expirada)
  python scrape_ssi.py --debug  → salva raw JSON e screenshot para inspeção

Pré-requisitos:
  pip install playwright
  playwright install chromium
"""

import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError as exc:
    raise SystemExit(
        "Playwright não instalado. Execute:\n"
        "  pip install playwright\n"
        "  playwright install chromium"
    ) from exc

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT         = Path(__file__).parent
DATA_DIR     = ROOT / "data"
SESSION_FILE = ROOT / ".linkedin_session.json"
DEBUG_DIR    = ROOT / ".debug"
SSI_URL      = "https://www.linkedin.com/sales/ssi"

CSV_HEADER = [
    "data_referencia", "hora_referencia", "secao", "campo",
    "valor_original", "unidade", "valor_numerico", "escala", "observacao", "fonte",
]
SOURCE = "LinkedIn SSI / scrape_ssi.py"

# ── Auth ──────────────────────────────────────────────────────────────────────

def ensure_session(playwright, force_login: bool = False):
    """Return an authenticated (browser, context) pair. Prompts login if needed."""
    browser = playwright.chromium.launch(headless=False, slow_mo=30)

    if not force_login and SESSION_FILE.exists():
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()
        try:
            page.goto("https://www.linkedin.com/feed",
                      wait_until="domcontentloaded", timeout=20_000)
            if any(p in page.url for p in ("/feed", "/mynetwork", "/sales")):
                print("  > Sessão válida carregada")
                page.close()
                return browser, context
        except PWTimeout:
            pass
        print("  ! Sessão expirada, solicitando novo login...")
        context.close()

    # Open login and wait for user
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.linkedin.com/login")
    print("\nFaça login no LinkedIn no browser que abriu.")

    print("Aguardando 10 segundos para o login...")
    page.wait_for_timeout(10_000)
    context.storage_state(path=str(SESSION_FILE))
    print(f"  > Sessão salva em {SESSION_FILE}")
    page.close()
    return browser, context

# ── Network Interception ──────────────────────────────────────────────────────

# Known LinkedIn SSI API patterns (may need extension based on observed traffic)
_API_PATTERNS = [
    "socialSellingIndex",
    "sales-api/salesApiSocialSelling",
    "voyager/api/sales/ssi",
    "ssiDashboard",
]

def _looks_like_ssi(url: str, body: dict) -> bool:
    if any(p in url for p in _API_PATTERNS):
        return True
    if isinstance(body, dict):
        text = json.dumps(body).lower()
        return "socialsellingindex" in text or "ssiscore" in text
    return False


def intercept_ssi_api(page) -> list[tuple[str, dict]]:
    """
    Navigate to the SSI page and return all captured API responses that look like SSI data.
    Useful for --debug mode; extraction itself uses DOM selectors.
    """
    captured: list[tuple[str, dict]] = []

    def on_response(response):
        url = response.url
        if not any(kw in url for kw in ("api", "graphql", "sales", "ssi")):
            return
        try:
            body = response.json()
            if _looks_like_ssi(url, body):
                captured.append((url, body))
                print(f"  > API capturada: {url}")
        except (ValueError, TypeError):
            pass

    page.on("response", on_response)
    try:
        page.goto(SSI_URL, wait_until="networkidle", timeout=60_000)
    except PWTimeout:
        page.goto(SSI_URL, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(4_000)

    return captured


# ── Data Extraction ────────────────────────────────────────────────────────────

def extract_from_dom(page) -> dict | None:
    """Extract SSI data via DOM selectors evaluated in the browser context."""
    print("  > Extraindo dados do DOM...")
    result = page.evaluate("""
    () => {
        const num = (el, attr) => {
            if (!el) return null;
            const raw = attr ? el.getAttribute(attr) : el.textContent.trim();
            const v = parseFloat(raw);
            return isNaN(v) ? null : v;
        };

        // SSI total — the span inside the donut caption (not the sub-score spans)
        const caption = document.querySelector(
            '.user-ssi-score__donut-chart-caption .ssi-score__value'
        );
        const ssi = num(caption);

        // Component scores — <progress> elements have the precise float in their value attr
        const comp = (id) => num(document.getElementById(id), 'value');

        // Rankings — two .ssi-rank blocks, each has a .t-40 span with the integer
        const rankEls = document.querySelectorAll('.ssi-rank__category-score .t-40');
        const rankSector = rankEls[0] ? parseInt(rankEls[0].textContent.trim(), 10) : null;
        const rankNet    = rankEls[1] ? parseInt(rankEls[1].textContent.trim(), 10) : null;

        // Averages — extracted from natural-language paragraphs: "SSI médio de 35"
        const allText = document.body.innerText;
        const avgMatches = [...allText.matchAll(/SSI médio de (\\d+)/g)];
        const avgSector = avgMatches[0] ? parseInt(avgMatches[0][1], 10) : null;
        const avgNet    = avgMatches[1] ? parseInt(avgMatches[1][1], 10) : null;

        // Per-component sector/network values — from Highcharts group charts
        // Charts inside .group-ssi-score__donut-chart: [0]=sector, [1]=network
        // Each pie has 5 slices: marca, pessoas, insights, relacao, remaining
        const hcAll = (window.Highcharts && window.Highcharts.charts || []).filter(Boolean);
        const groupCharts = hcAll.filter(
            c => c.container && c.container.closest('.group-ssi-score__donut-chart')
        );
        const slices = (chart) => {
            if (!chart) return [null, null, null, null];
            const pts = chart.series && chart.series[0] && chart.series[0].data || [];
            return pts.slice(0, 4).map(p => (p && p.y != null) ? p.y : null);
        };
        const [sm, sp, si, sr] = slices(groupCharts[0]);
        const [nm, np, ni, nr] = slices(groupCharts[1]);

        return {
            ssi,
            marca:       comp('establish-brand__sub-score-bar'),
            pessoas:     comp('find-people__sub-score-bar'),
            insights:    comp('engage-with-insights__sub-score-bar'),
            relacao:     comp('build-relationships__sub-score-bar'),
            rank_sector: rankSector,
            rank_net:    rankNet,
            avg_sector:  avgSector,
            avg_net:     avgNet,
            sector_marca: sm, sector_pessoas: sp, sector_insights: si, sector_relacao: sr,
            net_marca:    nm, net_pessoas:    np, net_insights:    ni, net_relacao:    nr,
        };
    }
    """)

    return result if result and result.get("ssi") is not None else None

# ── CSV Builder ────────────────────────────────────────────────────────────────

_COMP_LABELS = {
    "marca":    "Estabelecer sua marca profissional",
    "pessoas":  "Localizar as pessoas certas",
    "insights": "Interagir oferecendo insights",
    "relacao":  "Criar relacionamentos",
}


def _br(v: float) -> str:
    """Format float as Brazilian decimal string: comma separator, no trailing zeros."""
    return f"{round(v, 3):g}".replace(".", ",")


def build_rows(metrics: dict, ref_date: str, ref_time: str) -> list[list]:
    """Convert the extracted metrics dict into CSV rows matching the existing format."""
    rows = []

    def row(secao, campo, valor_original, unidade, valor_num, escala="", obs=""):
        return [
            ref_date, ref_time, secao, campo,
            valor_original, unidade, valor_num, escala, obs, SOURCE,
        ]

    if metrics.get("ssi") is not None:
        v = metrics["ssi"]
        rows.append(row("Social Selling Index atual", "Social Selling Index atual",
                        f"{int(v)} de 100", "pontos", round(v, 3), "0-100"))

    for key, label in _COMP_LABELS.items():
        if metrics.get(key) is not None:
            v = metrics[key]
            rows.append(row("Os quatro componentes da sua pontuação", label,
                            _br(v), "pontos", round(v, 3), "0-25"))

    for campo, key, obs in [
        ("Classificação SSI do setor", "rank_sector", "Ranking percentual no setor"),
        ("Classificação SSI da rede",  "rank_net",    "Ranking percentual na rede"),
    ]:
        if metrics.get(key) is not None:
            v = metrics[key]
            rows.append(row("Sua classificação", campo,
                            f"Primeiros {int(v)}%", "percentual", int(v), "percentual", obs))

    for campo, key in [
        ("SSI médio do setor", "avg_sector"),
        ("SSI médio da rede",  "avg_net"),
    ]:
        if metrics.get(key) is not None:
            v = metrics[key]
            rows.append(row("Benchmark", campo,
                            f"{int(v)} de 100", "pontos", int(v), "0-100"))

    for secao, prefix in [("Pessoas no seu setor", "sector_"), ("Pessoas na sua rede", "net_")]:
        for comp_key, label in _COMP_LABELS.items():
            v = metrics.get(f"{prefix}{comp_key}")
            if v is not None:
                rows.append(row(secao, label, _br(v), "pontos", round(v, 3), "0-25"))

    return rows


def save_csv(metrics: dict, force: bool = False) -> Path:
    """Write metrics to a dated CSV in data/. Skips if file exists (--force to overwrite)."""
    DATA_DIR.mkdir(exist_ok=True)
    today    = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M")
    output   = DATA_DIR / f"ssi_{today}.csv"

    if output.exists() and not force:
        print(f"  ! CSV para hoje já existe: {output.name} (use --force para sobrescrever)")
        return output

    rows = build_rows(metrics, today, now_time)
    with open(output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)

    print(f"  > CSV salvo: {output}")
    return output

# ── Debug Helpers ──────────────────────────────────────────────────────────────

def save_debug(page, all_captured: list) -> None:
    """Dump screenshot, captured API JSON, and page HTML to .debug/ for inspection."""
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    screenshot = DEBUG_DIR / f"ssi_{ts}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    print(f"  > Screenshot: {screenshot}")

    for i, (url, body) in enumerate(all_captured):
        out = DEBUG_DIR / f"api_{ts}_{i}.json"
        payload = json.dumps({"url": url, "body": body}, indent=2, ensure_ascii=False)
        out.write_text(payload, encoding="utf-8")
        print(f"  > JSON capturado: {out}")

    html_dump = DEBUG_DIR / f"html_{ts}.htm"
    html_dump.write_text(page.content(), encoding="utf-8")
    print(f"  > HTML salvo: {html_dump}")
    print(f"\n  Inspecione os arquivos em {DEBUG_DIR} para identificar os campos corretos.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    """Entry point: parse CLI flags, run scrape, save CSV."""
    force_login = "--login" in sys.argv
    debug_mode  = "--debug" in sys.argv
    force_csv   = "--force" in sys.argv

    print("\n=== LinkedIn SSI Scraper ===")

    with sync_playwright() as pw:
        browser, context = ensure_session(pw, force_login)
        page = context.new_page()

        print(f"  > Abrindo {SSI_URL} ...")
        all_captured = intercept_ssi_api(page)

        if debug_mode:
            save_debug(page, all_captured)

        metrics = extract_from_dom(page)

        page.close()
        context.storage_state(path=str(SESSION_FILE))  # refresh session TTL
        browser.close()

    if not metrics:
        print("\n  ! Não foi possível extrair os dados.")
        print("  Rode com --debug para inspecionar o tráfego e ajustar os seletores.")
        print("  Veja .debug/ após a execução.")
        raise SystemExit(1)

    print(f"\n  SSI: {metrics.get('ssi')}  |  "
          f"Marca: {metrics.get('marca')}  |  "
          f"Pessoas: {metrics.get('pessoas')}  |  "
          f"Insights: {metrics.get('insights')}  |  "
          f"Relações: {metrics.get('relacao')}")

    save_csv(metrics, force=force_csv)


if __name__ == "__main__":
    main()
