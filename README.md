# Stella

Assistente pessoal local do Bruno. Fase 1 — MVP Supervisora.

Spec de design: `bssurf00/C04 Claude Obsidian/projetos e specs/Stella/2026-05-11 — Fase 1 — Design.md`

## Setup

```powershell
cd D:\VortexBrain00\stella
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# editar .env com as chaves reais
```

## Testes

```powershell
pytest
```
