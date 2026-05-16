# Stella

Assistente pessoal local do Bruno. Fase 1, MVP Supervisora.

## Setup rápido

```powershell
cd D:\VortexBrain00\stella
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# editar .env com STELLA_NVIDIA_API_KEY e STELLA_ANTHROPIC_API_KEY
```

## Comandos disponíveis (M2)

```powershell
stella anota "ideia que acabou de surgir"
stella pergunta "Centro Viagens" "o que esta aberto?"
stella --help
```

## Testes

```powershell
pytest             # rapidos, sem chamar APIs (default — exclui 'live')
pytest -m live     # E2E com APIs reais (exige .env configurado, faz skip se faltar)
```

## Qualidade de código

Pre-commit hooks rodam em cada commit:

```powershell
pre-commit install   # primeira vez
pre-commit run --all-files   # rodar manualmente
```

Hooks ativos: `ruff` (lint + format), `mypy --strict`, `pytest`.

## Documentação

- **Spec:** `bssurf00/C04 Claude Obsidian/projetos e specs/Stella/2026-05-11 — Fase 1 — Design.md`
- **Como usar:** [docs/COMO_USAR.md](docs/COMO_USAR.md)
- **Planos por milestone:** `bssurf00/C04 Claude Obsidian/projetos e specs/Stella/`

## Estado

- M1 (Esqueleto + Fundação) — ✅ completo (merge em master)
- M2 (Captura + Q&A + CLI + qualidade) — ✅ completo
- M3 (Delegação + Tracking) — próximo
