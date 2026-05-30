# Handoff

## State
- Sub-projeto C completo (438 testes passando). Bugs corrigidos: AutoQA usa briefing da CarregadorMarca, Designer usa PlaywrightRender (PNG real), templates HTML dinâmicos com placeholders.
- Designer redesenhado para suportar 4 templates (capa-carrossel, foto-bg, foto-split, foto-topo) + injeção de fotos como base64 via `A03 Banco de Imagens/FotosBruno/` e `referencias para criativos/`.
- MCPs configurados em `C:\Users\Santos\.claude\mcp.json`: Paper.design (localhost:29979) + Higgsfield (token `hf_w2JbtOCKKZzVv-...` já configurado). Paper plugin instalado via `/plugin install paper-desktop@paper`.
- Higgsfield CLI instalado em `/usr/local/bin/hf`, autenticado.

## Next
1. **Construir designer Stella com Higgsfield + Paper**: substituir HTML/Playwright pelo pipeline Higgsfield (Soul ID para posts com Bruno) + Paper.design MCP (posts conceituais). Fazer brainstorm da arquitetura antes de codar.
2. **Treinar Soul ID no Higgsfield** com fotos de `A03 Banco de Imagens/FotosBruno/`.
3. **Testar MCPs**: verificar Paper MCP (precisa do app desktop aberto com arquivo) e Higgsfield MCP nas tools desta sessão.

## Context
- Paper MCP só funciona com o app desktop aberto e um arquivo aberto — lembrar de pedir ao Bruno antes de usar.
- `stella conteudo mktmagneto` gera copy OK mas visuais ainda usam HTML/Playwright. Fila tem 3 posts em rascunho aguardando visuais bons.
- Próxima sessão: usuário vai dizer "continuar stella".
