#!/usr/bin/env python3
"""
LinkedIn Contact Info Scraper
Para cada JSON em requests/data/ que ainda não tenha contato preenchido,
abre a overlay de informações de contato do perfil e extrai os dados disponíveis.

Uso:
  python requests/scrape_contact_info.py          → processa JSONs sem contato
  python requests/scrape_contact_info.py --login  → força novo login
  python requests/scrape_contact_info.py --force  → reprocessa todos (sobrescreve)
  python requests/scrape_contact_info.py --debug  → salva screenshot e HTML

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

ROOT         = Path(__file__).parent          # requests/
REPO         = ROOT.parent                    # repo root
DATA_DIR     = ROOT / "data"                  # requests/data/
SESSION_FILE = REPO / ".linkedin_session.json"
DEBUG_DIR    = REPO / ".debug"

# ── Auth ──────────────────────────────────────────────────────────────────────

def ensure_session(playwright, force_login: bool = False):
    browser = playwright.chromium.launch(headless=False, slow_mo=30)

    if not force_login and SESSION_FILE.exists():
        context = browser.new_context(storage_state=str(SESSION_FILE))
        page = context.new_page()
        try:
            page.goto("https://www.linkedin.com/feed",
                      wait_until="domcontentloaded", timeout=20_000)
            if any(p in page.url for p in ("/feed", "/mynetwork", "/sales", "/in/")):
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

# ── Contact Extraction ─────────────────────────────────────────────────────────

def extract_contact_info(page) -> list[dict]:
    """
    Extract all contact sections from the overlay.
    Returns a list of dicts: [{tipo, valor, url}]
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
                valor: valor,
                url:   url,
            };
        }).filter(c => c.valor !== "");
    }
    """)


def scrape_contact(page, profile_url: str, debug: bool = False) -> list[dict] | None:
    """
    Navigate to the contact-info overlay for a profile and return contact data.
    Returns None on failure.
    """
    contact_url = profile_url.rstrip("/") + "/overlay/contact-info/"
    print(f"  > {contact_url} ...", end=" ")

    try:
        page.goto(contact_url, wait_until="domcontentloaded", timeout=30_000)
    except PWTimeout:
        print("timeout ao carregar a página.")
        return None

    # Wait for the contact section to appear
    try:
        page.wait_for_selector(".pv-contact-info__contact-type", timeout=10_000)
        page.wait_for_timeout(500)
    except PWTimeout:
        print("overlay de contato não encontrado.")
        if debug:
            _save_debug_page(page, profile_url)
        return None

    contacts = extract_contact_info(page)

    if debug:
        _save_debug_page(page, profile_url)

    tipos = ", ".join(c["tipo"] for c in contacts) if contacts else "nenhum"
    print(f"OK ({len(contacts)} campo(s): {tipos})")
    return contacts


def _save_debug_page(page, profile_url: str) -> None:
    DEBUG_DIR.mkdir(exist_ok=True)
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug  = profile_url.rstrip("/").split("/")[-1]

    screenshot = DEBUG_DIR / f"contact_{slug}_{ts}.png"
    page.screenshot(path=str(screenshot), full_page=True)
    print(f"\n  > Screenshot: {screenshot}")

    html_dump = DEBUG_DIR / f"contact_{slug}_{ts}.htm"
    html_dump.write_text(page.content(), encoding="utf-8")
    print(f"  > HTML: {html_dump}")

# ── JSON Update ────────────────────────────────────────────────────────────────

def load_pending(force: bool) -> list[Path]:
    """Return JSON files that still need contact info scraped."""
    all_files = sorted(DATA_DIR.glob("*.json"))
    if force:
        return all_files

    pending = []
    for f in all_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("contato") is None:
                pending.append(f)
        except (json.JSONDecodeError, OSError):
            pending.append(f)

    return pending


def update_json(path: Path, contacts: list[dict]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["contato"] = contacts
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    force_login = "--login" in sys.argv
    debug_mode  = "--debug" in sys.argv
    force_all   = "--force" in sys.argv

    print("\n=== LinkedIn Contact Info Scraper ===")

    if not DATA_DIR.exists():
        raise SystemExit(f"Pasta de dados não encontrada: {DATA_DIR}\n"
                         "Execute scrape_requests.py primeiro.")

    pending = load_pending(force_all)
    if not pending:
        print("  Todos os JSONs já possuem informações de contato. "
              "Use --force para reprocessar.")
        return

    print(f"  > {len(pending)} arquivo(s) para processar")

    with sync_playwright() as pw:
        browser, context = ensure_session(pw, force_login)
        page = context.new_page()

        updated  = 0
        failed   = 0

        for json_path in pending:
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                print(f"  ! Erro ao ler {json_path.name}: {e}")
                failed += 1
                continue

            profile_url = data.get("solicitante", {}).get("perfil_url", "")
            nome        = data.get("solicitante", {}).get("nome", json_path.stem)

            print(f"\n  [{nome}]")

            if not profile_url:
                print("  ! perfil_url ausente, pulando.")
                failed += 1
                continue

            contacts = scrape_contact(page, profile_url, debug=debug_mode)

            if contacts is None:
                failed += 1
                continue

            update_json(json_path, contacts)
            print(f"  > {json_path.name} atualizado.")
            updated += 1

            # Small pause to avoid rate-limiting
            page.wait_for_timeout(2_000)

        page.close()
        context.storage_state(path=str(SESSION_FILE))
        browser.close()

    print(f"\n  Concluído: {updated} atualizado(s), {failed} falha(s).")


if __name__ == "__main__":
    main()
