#!/usr/bin/env python3
"""
LinkedIn Service Marketplace – Response Sender
Para cada JSON em requests/data/ que tenha "resposta" preenchida,
navega até a solicitação correspondente na página de provider,
clica em "Enviar proposta" e submete o texto da resposta.

Uso:
  python requests/send_responses.py             → envia todas as respostas pendentes
  python requests/send_responses.py --dry-run   → simula sem submeter nada
  python requests/send_responses.py --login     → força novo login
  python requests/send_responses.py --debug     → salva HTML/screenshot de cada modal

Pré-requisitos:
  pip install playwright
  playwright install chromium
"""

import json
import sys
from datetime import datetime
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

ROOT          = Path(__file__).parent
REPO          = ROOT.parent
DATA_DIR      = ROOT / "data"
SESSION_FILE  = REPO / ".linkedin_session.json"
DEBUG_DIR     = REPO / ".debug"
REQUESTS_URL  = "https://www.linkedin.com/service-marketplace/provider/requests/"

_ITEM_SEL   = (
    ".scaffold-finite-scroll__content "
    "li[data-test-service-marketplace-premium-service-requests__list-item]"
)
_ACCEPT_BTN = "[data-test-service-request-details__accept]"

# ── Auth ──────────────────────────────────────────────────────────────────────

def ensure_session(playwright, force_login: bool = False):
    browser = playwright.chromium.launch(headless=False, slow_mo=50)

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

# ── JSON Helpers ──────────────────────────────────────────────────────────────

def load_ready() -> dict[str, dict]:
    """
    Return {perfil_url: data} for all JSONs with 'resposta' filled
    and 'enviado' not True.
    """
    ready = {}
    if not DATA_DIR.exists():
        return ready
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("resposta") and not data.get("enviado"):
            url = (data.get("solicitante", {}).get("perfil_url") or "").rstrip("/")
            if url:
                ready[url] = {"data": data, "path": f}
    return ready


def mark_sent(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["enviado"] = True
    data["data_envio"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Page Helpers ──────────────────────────────────────────────────────────────

def _scroll_to_load_all(page) -> None:
    prev = 0
    stale = 0
    while stale < 3:
        page.evaluate("""
            const el = document.querySelector('.scaffold-finite-scroll__content');
            if (el) el.scrollTop = el.scrollHeight;
            else window.scrollTo(0, document.body.scrollHeight);
        """)
        page.wait_for_timeout(2_000)
        count = len(page.query_selector_all(_ITEM_SEL))
        if count > prev:
            prev  = count
            stale = 0
        else:
            stale += 1


def _get_detail_profile_url(page) -> str | None:
    """Extract the profile URL shown in the currently active detail panel."""
    return page.evaluate("""
        () => {
            const a = document.querySelector('[data-test-service-requests-detail__creator-title-link]');
            return a ? a.href : null;
        }
    """)

# ── Proposal Modal ────────────────────────────────────────────────────────────

def _save_debug_modal(page, slug: str) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    page.screenshot(path=str(DEBUG_DIR / f"modal_{slug}_{ts}.png"), full_page=False)
    (DEBUG_DIR / f"modal_{slug}_{ts}.htm").write_text(page.content(), encoding="utf-8")
    print(f"\n  > Debug modal salvo em {DEBUG_DIR}")


_TEXTAREA_SEL  = "textarea[aria-label='Sua proposta']"
_CONSULT_SEL   = "[data-test-text-selectable-option__input='Incluir consulta por telefone']"
_SUBMIT_SEL    = "[data-test-proposal-submission-modal__footer-cta-button]"
_CLOSE_SEL     = ".artdeco-modal__dismiss"


def _close_modal(page) -> None:
    close = page.query_selector(_CLOSE_SEL)
    if close:
        close.click()


def _open_modal(page, debug: bool, slug: str) -> bool:
    """Click 'Enviar proposta' and wait for the textarea. Returns False on failure."""
    try:
        page.wait_for_selector(_ACCEPT_BTN, timeout=5_000).click()
    except PWTimeout:
        print("  ! Botão 'Enviar proposta' não encontrado.")
        return False
    try:
        page.wait_for_selector(_TEXTAREA_SEL, timeout=8_000)
        page.wait_for_timeout(500)
    except PWTimeout:
        print("  ! Modal de proposta não abriu.")
        if debug:
            _save_debug_modal(page, slug)
        return False
    if debug:
        _save_debug_modal(page, slug)
    return True


def _check_consultation(page) -> None:
    consult = page.query_selector(_CONSULT_SEL)
    if not consult:
        print("  > Opção de consulta por telefone não disponível nesta proposta.")
        return
    if consult.is_checked():
        print("  > Consulta por telefone já estava marcada.")
    else:
        consult.check()
        print("  > Consulta por telefone marcada.")


def fill_and_submit(page, resposta: str, dry_run: bool, debug: bool, slug: str) -> bool:
    """Click 'Enviar proposta', fill the textarea and submit. Returns True on success."""
    if not _open_modal(page, debug, slug):
        return False

    page.query_selector(_TEXTAREA_SEL).fill(resposta)
    page.wait_for_timeout(500)

    _check_consultation(page)
    page.wait_for_timeout(500)

    if dry_run:
        print("  [DRY-RUN] Textarea preenchida e checkbox marcado. Submit NÃO executado.")
        _close_modal(page)
        return True

    # submit = page.query_selector(_SUBMIT_SEL)
    # if not submit:
    #     print("  ! Botão de envio não encontrado. Rode com --debug para inspecionar.")
    #     _close_modal(page)
    #     return False
    # submit.click()
    # page.wait_for_timeout(2_000)
    # print("  > Proposta enviada.")
    return True

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    force_login = "--login"   in sys.argv
    dry_run     = "--dry-run" in sys.argv
    debug_mode  = "--debug"   in sys.argv

    print("\n=== LinkedIn Service Marketplace – Response Sender ===")
    if dry_run:
        print("  [DRY-RUN] Nenhuma proposta será efetivamente enviada.")

    ready = load_ready()
    if not ready:
        print("\n  Nenhum JSON com resposta pronta e não enviado encontrado.")
        print("  Preencha o campo 'resposta' nos JSONs e rode novamente.")
        return

    print(f"\n  {len(ready)} proposta(s) para enviar:")
    for url, entry in ready.items():
        nome = entry["data"].get("solicitante", {}).get("nome") or "—"
        print(f"    {nome}  ({url})")

    with sync_playwright() as pw:
        browser, context = ensure_session(pw, force_login)
        page = context.new_page()

        print(f"\n  > Abrindo {REQUESTS_URL} ...")
        try:
            page.goto(REQUESTS_URL, wait_until="networkidle", timeout=60_000)
        except PWTimeout:
            page.goto(REQUESTS_URL, wait_until="domcontentloaded", timeout=30_000)

        page.wait_for_timeout(3_000)

        try:
            page.wait_for_selector(".scaffold-finite-scroll__content", timeout=15_000)
        except PWTimeout:
            print("  ! Lista de solicitações não encontrada.")
            browser.close()
            raise SystemExit(1)

        print("  > Scrollando para carregar todos os itens...")
        _scroll_to_load_all(page)

        # Back to top
        page.evaluate("""
            const el = document.querySelector('.scaffold-finite-scroll__content');
            if (el) el.scrollTop = 0;
        """)
        page.wait_for_timeout(500)

        items = page.query_selector_all(_ITEM_SEL)
        total = len(items)
        print(f"  > {total} solicitação(ões) na lista")

        sent    = 0
        skipped = 0

        for idx in range(total):
            items = page.query_selector_all(_ITEM_SEL)
            if idx >= len(items):
                break

            items[idx].scroll_into_view_if_needed()
            items[idx].click()

            try:
                page.wait_for_selector(
                    "#service-marketplace-provider-requests-detail", timeout=10_000
                )
                page.wait_for_timeout(800)
            except PWTimeout:
                continue

            detail_url = (_get_detail_profile_url(page) or "").rstrip("/")
            if not detail_url:
                continue

            entry = ready.get(detail_url)
            if not entry:
                continue

            nome     = entry["data"].get("solicitante", {}).get("nome") or detail_url
            resposta = entry["data"]["resposta"]
            slug     = detail_url.rstrip("/").split("/")[-1]

            print(f"\n  [{idx + 1}/{total}] {nome}")
            print(f"     Resposta: {resposta[:80].replace(chr(10), ' ')}{'...' if len(resposta) > 80 else ''}")

            ok = fill_and_submit(page, resposta, dry_run, debug_mode, slug)

            if ok and not dry_run:
                mark_sent(entry["path"])
                sent += 1
            elif ok and dry_run:
                sent += 1
            else:
                skipped += 1

            page.wait_for_timeout(2_000)

        page.close()
        context.storage_state(path=str(SESSION_FILE))
        browser.close()

    label = "simulada(s)" if dry_run else "enviada(s)"
    print(f"\n  Concluído: {sent} proposta(s) {label}, {skipped} falha(s).")


if __name__ == "__main__":
    main()
