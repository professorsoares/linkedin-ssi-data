#!/usr/bin/env python3
"""
Orquestrador diário do LinkedIn SSI.
Executa em sequência: coleta → dashboard → commit git.

Uso:
  python run_daily.py           # fluxo completo
  python run_daily.py --login   # força novo login antes de coletar
  python run_daily.py --force   # sobrescreve CSV do dia se já existir
  python run_daily.py --debug   # passa --debug para o scraper
"""

import subprocess
import sys
import webbrowser
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable


def step(label: str, cmd: list[str]) -> bool:
    """Run a command, stream output, return True on success."""
    print(f"\n{'─'*50}")
    print(f"  {label}")
    print(f"{'─'*50}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\n  [ERRO] '{' '.join(cmd)}' terminou com código {result.returncode}.")
    return result.returncode == 0


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def commit_today() -> bool:
    """Stage new/modified files in data/ and dashboard.html, then commit."""
    today_fmt = date.today().strftime("%d/%m/%Y")
    message   = f"Adicionando os dados do dia {today_fmt} ."

    # Stage only the files this pipeline produces
    git("add", "data/", "dashboard.html")

    status = git("status", "--porcelain")
    if not status.stdout.strip():
        print("  Nada para commitar — arquivos sem alterações.")
        return True

    result = git("commit", "-m", message)
    if result.returncode == 0:
        print(f"  Commit criado: \"{message}\"")
        # Show short hash
        ref = git("rev-parse", "--short", "HEAD")
        print(f"  Ref: {ref.stdout.strip()}")
        return True

    print(f"  [ERRO] git commit falhou:\n{result.stderr}")
    return False


def main():
    args = sys.argv[1:]

    # ── 1. Scrape ──────────────────────────────────────────────────────────────
    scrape_cmd = [PYTHON, str(ROOT / "scrape_ssi.py")]
    for flag in ("--login", "--force", "--debug"):
        if flag in args:
            scrape_cmd.append(flag)

    if not step("1/3  Coletando dados do LinkedIn SSI", scrape_cmd):
        raise SystemExit("Pipeline interrompido na etapa de coleta.")

    # ── 2. Dashboard ───────────────────────────────────────────────────────────
    if not step("2/3  Gerando dashboard.html", [PYTHON, str(ROOT / "generate_dashboard.py")]):
        raise SystemExit("Pipeline interrompido na geração do dashboard.")

    # ── 3. Commit ──────────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print("  3/3  Commitando no repositório")
    print(f"{'─'*50}")
    if not commit_today():
        raise SystemExit("Pipeline interrompido no commit.")

    print(f"\n{'─'*50}")
    print("  Concluído.")
    print(f"{'─'*50}\n")

    webbrowser.open((ROOT / "dashboard.html").as_uri())


if __name__ == "__main__":
    main()
