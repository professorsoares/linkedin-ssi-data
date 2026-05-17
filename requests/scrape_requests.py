#!/usr/bin/env python3
"""
LinkedIn Service Marketplace – Requests Scraper
Captura todas as solicitações de serviço disponíveis na página de provider,
busca as informações de contato de cada solicitante e salva um JSON completo
por solicitação em requests/data/.

Primeira execução:
  python requests/scrape_requests.py          → abre browser para login, salva sessão
Execuções seguintes:
  python requests/scrape_requests.py          → usa sessão salva, coleta e gera JSONs
  python requests/scrape_requests.py --login  → força novo login (sessão expirada)
  python requests/scrape_requests.py --debug  → salva screenshot e HTML para inspeção
  python requests/scrape_requests.py --force  → sobrescreve JSONs do dia se já existirem

Pré-requisitos:
  pip install playwright
  playwright install chromium
"""

import json
import re
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

ROOT          = Path(__file__).parent          # requests/
REPO          = ROOT.parent                    # repo root
DATA_DIR      = ROOT / "data"                  # requests/data/
SESSION_FILE  = REPO / ".linkedin_session.json"
DEBUG_DIR     = REPO / ".debug"
REQUESTS_URL  = "https://www.linkedin.com/service-marketplace/provider/requests/"
SOURCE        = "LinkedIn Service Marketplace / scrape_requests.py"

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
            if any(p in page.url for p in ("/feed", "/mynetwork", "/sales", "/service-marketplace")):
                print("  > Sessão válida carregada")
                page.close()
                return browser, context
        except PWTimeout:
            pass
        print("  ! Sessão expirada, solicitando novo login...")
        context.close()

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

# ── Request Extraction ─────────────────────────────────────────────────────────

def extract_detail(page) -> dict:
    """Extract all fields from the currently visible request detail panel."""
    return page.evaluate("""
    () => {
        // Returns trimmed text or null when element is absent
        const txt = (sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const v = el.innerText.trim();
            return v !== "" ? v : null;
        };

        const title    = txt('[data-test-service-requests-detail__project-title]');
        const location = txt('[data-test-service-requests-detail__location]');
        const posted   = txt('[data-test-service-requests-detail__project-status]');

        const creatorLink = document.querySelector('[data-test-service-requests-detail__creator-title-link]');
        const creatorName = creatorLink
            ? (creatorLink.querySelector('[data-test-service-requests-detail__creator-title] span') || creatorLink).innerText.trim() || null
            : null;
        const profileUrl = creatorLink ? creatorLink.href : null;

        const degreeEl = document.querySelector(
            '[data-test-service-requests-detail__creator-badge] .artdeco-entity-lockup__degree'
        );
        const degree = degreeEl
            ? degreeEl.innerText.replace(/[·\\s]/g, "").trim() || null
            : null;

        const subtitle = txt('[data-test-service-requests-detail__creator-subtitle]');

        // Mutual connections section is optional — null when absent
        const mutualEl = document.querySelector('[data-test-service-requests-detail__mutual-connections-text]');
        const mutual   = mutualEl ? mutualEl.innerText.trim() || null : null;

        // Q&A pairs: captured dynamically; number and content vary by request type
        const questions = Array.from(document.querySelectorAll('[data-test-service-requests-detail__description-question]'));
        const answers   = Array.from(document.querySelectorAll('[data-test-service-requests-detail__description-answer]'));
        const detalhes_projeto = questions.map((q, i) => ({
            pergunta: q.innerText.trim(),
            resposta: answers[i] ? answers[i].innerText.trim() : null
        }));

        return { title, location, posted, creatorName, profileUrl, degree, subtitle, mutual, detalhes_projeto };
    }
    """)


def scrape_all_requests(page) -> list[dict]:
    """Navigate to the requests page, click each item, and collect details."""
    print(f"\n  > Abrindo {REQUESTS_URL} ...")
    try:
        page.goto(REQUESTS_URL, wait_until="networkidle", timeout=60_000)
    except PWTimeout:
        page.goto(REQUESTS_URL, wait_until="domcontentloaded", timeout=30_000)

    page.wait_for_timeout(3_000)

    try:
        page.wait_for_selector(".scaffold-finite-scroll__content", timeout=15_000)
    except PWTimeout:
        print("  ! Lista de solicitações não encontrada. Verifique se a URL está correta.")
        return []

    items = page.query_selector_all(
        ".scaffold-finite-scroll__content li[data-test-service-marketplace-premium-service-requests__list-item]"
    )
    total = len(items)
    print(f"  > {total} solicitação(ões) encontrada(s)")

    if total == 0:
        return []

    results = []
    for idx in range(total):
        items = page.query_selector_all(
            ".scaffold-finite-scroll__content li[data-test-service-marketplace-premium-service-requests__list-item]"
        )
        if idx >= len(items):
            break

        items[idx].click()
        print(f"  > [{idx + 1}/{total}] Solicitação ...", end=" ")

        try:
            page.wait_for_selector(
                "#service-marketplace-provider-requests-detail",
                timeout=10_000
            )
            page.wait_for_timeout(1_000)
        except PWTimeout:
            print("timeout no painel de detalhe, pulando.")
            continue

        detail = extract_detail(page)
        print(f'"{detail.get("title") or "(sem título)"}"')
        results.append(detail)

    return results

# ── Contact Extraction ─────────────────────────────────────────────────────────

def extract_contact_info(page) -> list[dict]:
    """
    Extract all sections from the contact-info overlay.
    Returns whatever fields are present — list length varies by profile.
    """
    return page.evaluate("""
    () => {
        const sections = Array.from(
            document.querySelectorAll('.pv-contact-info__contact-type')
        );

        return sections.map(sec => {
            const tipo = (sec.querySelector('.pv-contact-info__header') || {}).innerText || "";

            // Prefer anchor text/href; fall back to span text
            const anchor = sec.querySelector('a');
            const span   = sec.querySelector('span');

            const valor = anchor
                ? anchor.innerText.trim()
                : (span ? span.innerText.trim() : "");

            const url = anchor ? anchor.href : "";

            return {
                tipo:  tipo.trim(),
                valor: valor || null,
                url:   url   || null,
            };
        }).filter(c => c.valor !== null);
    }
    """)


def scrape_contact(page, profile_url: str, debug: bool = False) -> list[dict] | None:
    """
    Open the contact-info overlay for a profile and return contact data.
    Returns None on failure; returns [] if overlay loads but has no data.
    """
    contact_url = profile_url.rstrip("/") + "/overlay/contact-info/"
    print(f"     contato: {contact_url} ...", end=" ")

    try:
        page.goto(contact_url, wait_until="domcontentloaded", timeout=30_000)
    except PWTimeout:
        print("timeout ao carregar.")
        return None

    try:
        page.wait_for_selector(".pv-contact-info__contact-type", timeout=10_000)
        page.wait_for_timeout(500)
    except PWTimeout:
        print("overlay não encontrado.")
        if debug:
            _save_debug_contact(page, profile_url)
        return None

    contacts = extract_contact_info(page)

    if debug:
        _save_debug_contact(page, profile_url)

    tipos = ", ".join(c["tipo"] for c in contacts) if contacts else "nenhum"
    print(f"OK ({len(contacts)} campo(s): {tipos})")
    return contacts


def _save_debug_contact(page, profile_url: str) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = profile_url.rstrip("/").split("/")[-1]
    page.screenshot(path=str(DEBUG_DIR / f"contact_{slug}_{ts}.png"), full_page=True)
    (DEBUG_DIR / f"contact_{slug}_{ts}.htm").write_text(page.content(), encoding="utf-8")
    print(f"\n  > Debug salvo em {DEBUG_DIR}")

# ── JSON Persistence ───────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[àáâãä]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = text.replace("ç", "c")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:40]


def _profile_id(url: str) -> str:
    m = re.search(r"/in/([^/?#]+)", url or "")
    return m.group(1) if m else ""


def _val(v) -> str | None:
    """Return stripped string or None for falsy/None values."""
    return v.strip() if isinstance(v, str) and v.strip() else None


def build_json(raw: dict, contacts: list[dict] | None, ref_date: str, ref_time: str) -> dict:
    return {
        "data_referencia": ref_date,
        "hora_referencia": ref_time,
        "titulo_projeto": _val(raw.get("title")),
        "localizacao": _val(raw.get("location")),
        "tempo_publicado": _val(raw.get("posted")),
        "solicitante": {
            "nome": _val(raw.get("creatorName")),
            "perfil_url": raw.get("profileUrl"),
            "grau_conexao": raw.get("degree"),
            "subtitulo": _val(raw.get("subtitle")),
            "conexoes_compartilhadas": raw.get("mutual"),
        },
        "detalhes_projeto": raw.get("detalhes_projeto", []),
        "contato": contacts,
        "resposta": None,
        "fonte": SOURCE,
    }


def save_request(raw: dict, contacts: list[dict] | None, idx: int,
                 ref_date: str, ref_time: str, force: bool) -> Path | None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    profile_id = _profile_id(raw.get("profileUrl") or "")
    name_slug  = _slug(raw.get("creatorName") or f"item{idx}")
    identifier = profile_id or name_slug
    filename   = f"{ref_date}_{idx:02d}_{identifier}.json"
    output     = DATA_DIR / filename

    if output.exists() and not force:
        print(f"  ! Já existe: {filename} (use --force para sobrescrever)")
        return None

    payload = build_json(raw, contacts, ref_date, ref_time)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  > Salvo: {filename}")
    return output

# ── Debug Helpers ──────────────────────────────────────────────────────────────

def save_debug_requests(page) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    page.screenshot(path=str(DEBUG_DIR / f"requests_{ts}.png"), full_page=True)
    (DEBUG_DIR / f"requests_html_{ts}.htm").write_text(page.content(), encoding="utf-8")
    print(f"  > Debug salvo em {DEBUG_DIR}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    force_login = "--login" in sys.argv
    debug_mode  = "--debug" in sys.argv
    force_save  = "--force" in sys.argv

    print("\n=== LinkedIn Service Marketplace – Requests Scraper ===")

    today    = date.today().isoformat()
    now_time = datetime.now().strftime("%H:%M")

    with sync_playwright() as pw:
        browser, context = ensure_session(pw, force_login)
        page = context.new_page()

        # ── 1. Collect all request details ────────────────────────────────────
        print("\n--- Etapa 1: Coletando solicitações ---")
        all_requests = scrape_all_requests(page)

        if debug_mode:
            save_debug_requests(page)

        if not all_requests:
            page.close()
            context.storage_state(path=str(SESSION_FILE))
            browser.close()
            print("\n  ! Nenhuma solicitação capturada.")
            print("  Rode com --debug para inspecionar o HTML e ajustar os seletores.")
            raise SystemExit(1)

        # ── 2. Fetch contact info for each profile ─────────────────────────────
        print(f"\n--- Etapa 2: Buscando contatos ({len(all_requests)} perfil(is)) ---")
        saved = 0
        for idx, raw in enumerate(all_requests, start=1):
            nome        = raw.get("creatorName") or f"item {idx}"
            profile_url = raw.get("profileUrl")

            print(f"\n  [{idx}/{len(all_requests)}] {nome}")

            contacts = None
            if profile_url:
                contacts = scrape_contact(page, profile_url, debug=debug_mode)
                page.wait_for_timeout(2_000)
            else:
                print("     contato: perfil_url ausente, pulando.")

            result = save_request(raw, contacts, idx, today, now_time, force_save)
            if result:
                saved += 1

        page.close()
        context.storage_state(path=str(SESSION_FILE))
        browser.close()

    print(f"\n  Concluído: {saved} de {len(all_requests)} JSON(s) salvo(s) em {DATA_DIR}")


if __name__ == "__main__":
    main()
