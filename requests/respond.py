#!/usr/bin/env python3
"""
LinkedIn Service Marketplace – Response Writer
Lista as solicitações pendentes e permite inserir a resposta/proposta
diretamente no campo "resposta" do JSON.

Uso:
  python requests/respond.py                      → menu interativo
  python requests/respond.py <arquivo.json>       → vai direto ao arquivo
  python requests/respond.py --list               → lista pendentes e sai
"""

import json
import sys
from pathlib import Path

ROOT     = Path(__file__).parent
DATA_DIR = ROOT / "data"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _pending() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    files = sorted(DATA_DIR.glob("*.json"))
    return [f for f in files if _load(f).get("resposta") is None]


def _all_files() -> list[Path]:
    if not DATA_DIR.exists():
        return []
    return sorted(DATA_DIR.glob("*.json"))

# ── Display ───────────────────────────────────────────────────────────────────

def _print_summary(data: dict, path: Path) -> None:
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  Arquivo : {path.name}")
    print(f"  Projeto : {data.get('titulo_projeto') or '—'}")
    print(f"  Local   : {data.get('localizacao') or '—'}")
    print(f"  Data    : {data.get('data_referencia')}  {data.get('tempo_publicado') or ''}")

    sol = data.get("solicitante", {})
    print(f"\n  Solicitante : {sol.get('nome') or '—'}  ({sol.get('grau_conexao') or '—'})")
    print(f"  Cargo       : {sol.get('subtitulo') or '—'}")

    contatos = data.get("contato") or []
    for c in contatos:
        label = c.get("tipo", "")
        valor = c.get("valor", "")
        if label and valor:
            print(f"  {label:<20}: {valor}")

    detalhes = data.get("detalhes_projeto") or []
    if detalhes:
        print(f"\n  Detalhes do projeto:")
        for qa in detalhes:
            print(f"    P: {qa.get('pergunta', '')}")
            print(f"    R: {qa.get('resposta', '')}")

    resposta_atual = data.get("resposta")
    if resposta_atual:
        print(f"\n  Resposta atual:\n{_indent(resposta_atual)}")

    print(sep)


def _indent(text: str, prefix: str = "    ") -> str:
    return "\n".join(prefix + line for line in text.splitlines())

# ── Input ─────────────────────────────────────────────────────────────────────

def _read_multiline(prompt: str) -> str:
    """Read multiline text. Finish with a blank line or Ctrl+Z/Ctrl+D."""
    print(prompt)
    print("  (linha em branco para finalizar | Ctrl+Z/Ctrl+D para cancelar)\n")
    lines = []
    try:
        while True:
            line = input()
            if line == "":
                if lines:
                    break
            else:
                lines.append(line)
    except EOFError:
        return ""
    return "\n".join(lines)


def _confirm(question: str) -> bool:
    try:
        return input(f"\n  {question} [s/N] ").strip().lower() in ("s", "sim", "y", "yes")
    except EOFError:
        return False

# ── Core ──────────────────────────────────────────────────────────────────────

def respond_to(path: Path) -> None:
    data = _load(path)
    _print_summary(data, path)

    has_response = bool(data.get("resposta"))
    if has_response:
        if not _confirm("Já existe uma resposta. Deseja substituir?"):
            print("  Cancelado.")
            return

    resposta = _read_multiline("  Digite a proposta/resposta:")
    if not resposta.strip():
        print("  Nenhum texto informado. Cancelado.")
        return

    print(f"\n  Prévia:\n{_indent(resposta)}")
    if not _confirm("Salvar esta resposta?"):
        print("  Cancelado.")
        return

    data["resposta"] = resposta.strip()
    _save(path, data)
    print(f"  ✓ Salvo em {path.name}")


def interactive_menu(files: list[Path]) -> None:
    if not files:
        print("  Nenhuma solicitação pendente encontrada.")
        return

    print(f"\n  {'#':<4} {'Arquivo':<45} {'Solicitante'}")
    print("  " + "─" * 75)
    for i, f in enumerate(files, start=1):
        try:
            data  = _load(f)
            nome  = data.get("solicitante", {}).get("nome") or "—"
            print(f"  {i:<4} {f.name:<45} {nome}")
        except Exception:
            print(f"  {i:<4} {f.name:<45} (erro ao ler)")

    print()
    try:
        raw = input("  Número da solicitação (ou Enter para sair): ").strip()
    except EOFError:
        return

    if not raw:
        return

    if not raw.isdigit() or not (1 <= int(raw) <= len(files)):
        print("  Número inválido.")
        return

    respond_to(files[int(raw) - 1])

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if "--list" in args:
        pending = _pending()
        if not pending:
            print("Nenhuma solicitação pendente.")
        else:
            print(f"\n  {len(pending)} pendente(s):\n")
            for f in pending:
                data = _load(f)
                nome = data.get("solicitante", {}).get("nome") or "—"
                print(f"  {f.name}  —  {nome}")
        return

    # Direct file argument
    direct = [a for a in args if not a.startswith("--")]
    if direct:
        candidate = Path(direct[0])
        if not candidate.is_absolute():
            candidate = DATA_DIR / candidate.name if candidate.parent == Path(".") else candidate
        if not candidate.exists():
            raise SystemExit(f"Arquivo não encontrado: {candidate}")
        respond_to(candidate)
        return

    # Interactive menu — show only pending by default, all with --all
    print("\n=== LinkedIn Service Marketplace – Response Writer ===")
    if "--all" in args:
        files = _all_files()
        print(f"  Mostrando todas as solicitações ({len(files)})")
    else:
        files = _pending()
        print(f"  Mostrando somente pendentes ({len(files)})  |  use --all para ver todas")

    interactive_menu(files)


if __name__ == "__main__":
    main()
