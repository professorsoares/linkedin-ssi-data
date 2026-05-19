#!/usr/bin/env python3
"""
Adiciona o campo "texto_convite" aos JSONs existentes em requests/data/
que ainda não possuem esse campo.

Uso:
  python requests/add_invite_text.py          → atualiza somente os sem o campo
  python requests/add_invite_text.py --force  → regenera em todos os JSONs
"""

import json
import sys
from pathlib import Path

# Importa a função geradora que já está em scrape_requests
sys.path.insert(0, str(Path(__file__).parent))
from scrape_requests import build_invite_text  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"


def update_file(path: Path, force: bool) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))

    if "texto_convite" in data and not force:
        return False

    nome   = data.get("solicitante", {}).get("nome")
    titulo = data.get("titulo_projeto")
    data["texto_convite"] = build_invite_text(nome, titulo)

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def main():
    force = "--force" in sys.argv

    if not DATA_DIR.exists():
        raise SystemExit(f"Pasta não encontrada: {DATA_DIR}")

    files   = sorted(DATA_DIR.glob("*.json"))
    updated = 0
    skipped = 0

    for f in files:
        try:
            if update_file(f, force):
                nome = json.loads(f.read_text(encoding="utf-8")) \
                           .get("solicitante", {}).get("nome", "—")
                print(f"  OK {f.name}  ({nome})")
                updated += 1
            else:
                skipped += 1
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! Erro em {f.name}: {e}")

    print(f"\n  {updated} atualizado(s), {skipped} já possuíam o campo.")


if __name__ == "__main__":
    main()
