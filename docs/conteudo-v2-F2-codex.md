# F2 — Ferramentas da fábrica de carrossel (spec autocontida para Codex)

Contexto: skill de Conteúdo v2 (carrossel). A F1 (Claude) já entregou, na branch
`feat/conteudo-v2-f1`:
- `stella/domain/registro_keywords.py` — `RegistroKeywords` (keyword→slug→material→posts,
  matching acento/caixa-insensível, dedup, escrita atômica). Use como fonte da verdade.
- `stella/corpo/persona_carrossel.py` — `PERSONA_CARROSSEL` define o CONTRATO: o cérebro
  vai chamar exatamente os 4 comandos abaixo. Não mude os nomes/assinaturas.

Regras do projeto: TDD obrigatório (teste falha primeiro, depois código). Type hints
estritos. `uv run pytest`, `uv run ruff check`, `uv run ruff format`, `uv run mypy` limpos.
Clean Architecture (domínio não importa adapters). Codex NÃO commita; deixa a árvore pronta
para o Claude revisar e commitar. Sem travessão em qualquer texto público gerado.

Caminhos base:
- Fábrica (fonte): `<vault>/C04 Claude Obsidian/outputs/FABRICADECONTEUDO/`
- Fila (slides que vão pro ar): `<vault>/C04 Claude Obsidian/Stella-publicacao/fila/<id>/`
- Registro JSON: `FABRICADECONTEUDO/registro-keywords.json`
- CSS de material compartilhada: `FABRICADECONTEUDO/_material.css`
- Hub: `D:/VortexBrain00/brunoeduardosantos-site/public/materiais/<slug>.pdf`
- `<vault>` vem de `StellaConfig().vault_path`.

Motor a portar: `FABRICADECONTEUDO/motor/gerar_carrossel.py` (Chrome headless
`--screenshot`, layout Field Manual escuro, slides capa/conteudo/cta 1080x1350). Traga a
lógica para um módulo do repo; as funções que montam HTML (capa/conteudo/cta) viram funções
puras testáveis.

## Comando 1 — `stella carrossel <json> <outdir>`
Renderiza os slides de um post.
- Lê o JSON (schema: `categoria`, `slides[]` com `tipo` em {capa,conteudo,cta}).
- Para cada slide, monta o HTML (porte de `BUILDERS`) e renderiza PNG `slide-NN.png` em `<outdir>`.
- Chrome: use `StellaConfig().render_browser_path` se setado, senão auto-detecte (mesma
  estratégia do resolvedor de foto-hero já existente).
- Imprime, por slide, `slide N/M (tipo): OK|FALHOU`.
Módulo sugerido: `stella/adapters/render/carrossel.py`. CLI em `frontends/cli.py`:
`@app.command("carrossel")`.
Testes (puro, sem Chrome): `montar_html_capa/conteudo/cta` produzem o HTML esperado
(contém título, passos, sem `—`); validação de schema rejeita `tipo` inválido.

## Comando 2 — `stella material <KEYWORD> --html <file> --slug <slug>`
Renderiza o lead-magnet HTML→PDF e registra no registro.
- Renderiza `<file>` com Chrome `--print-to-pdf` (headers off) para
  `FABRICADECONTEUDO/<KEYWORD>/<slug>.pdf`.
- Valida: fontes embutidas no PDF (procurar `Grotesk`/`Fraunces` nos bytes) e a REGRA DE
  LAYOUT: nº de `<section class="page">` no HTML == nº de páginas do PDF (senão, erro claro
  "material estourou: N seções, M páginas, redivida"). Ver `motor/COMO-FUNCIONA.md`.
- Atualiza o registro: `RegistroKeywords.carregar(reg).registrar_post` não se aplica aqui;
  use um método de set de material (adicione `definir_material(keyword, slug, material)` ao
  domínio via TDD se faltar) e `salvar`.
CLI: `@app.command("material")`.
Testes: a função de validação layout (seções vs páginas) é pura sobre (html_str, n_paginas);
o set de material no registro persiste e é acento-insensível.

## Comando 3 — `stella manychat <KEYWORD>`
Gera/atualiza `FABRICADECONTEUDO/<KEYWORD>/manychat-<kw>.txt` a partir do registro.
- Lê a entrada da keyword (slug, posts). Monta o arquivo no formato padrão:
  cabeçalho (KEYWORD, posts, "Material entregue: https://brunoeduardosantos.com.br/materiais/
  <slug>.pdf"), GATILHO, DM1 (confirmação "responde EU QUERO"), DM2 (botão URL pro PDF).
  Ver os `manychat-*.txt` existentes como modelo exato.
- Idempotente: re-rodar atualiza a linha "Posts que usam" com a lista do registro.
CLI: `@app.command("manychat")`.
Testes (puro): `montar_manychat(entrada)` produz texto com a keyword, os posts e a URL do slug;
sem travessão.

## Comando 4 — `stella publicar-material <slug>` (gate 2, ação externa)
Hospeda o PDF no hub. Só é chamado pelo cérebro após o ok explícito do Bruno.
- Copia `FABRICADECONTEUDO/<KEYWORD>/<slug>.pdf` (resolva a keyword pelo registro via slug)
  para `brunoeduardosantos-site/public/materiais/<slug>.pdf`.
- `git add` do PDF + commit com autor `brunoeduardosantos1982@gmail.com` (PEGADINHA do
  deploy, ver `reference_vercel_deploy_hub`) + `vercel deploy --prod --yes`.
- Verifica 200 em `https://www.brunoeduardosantos.com.br/materiais/<slug>.pdf`.
- Guard: se o PDF de origem não existir, erro claro e exit 1, sem tocar no git.
CLI: `@app.command("publicar-material")`.
Testes: resolução de caminho/slug e o guard (PDF ausente → erro) com `tmp_path`; o
deploy/git ficam atrás de uma fronteira injetável (função `deploy_fn`/`commit_fn`) para o
teste mockar sem rede. Não teste a rede real.

## Definição de pronto (F2)
- 4 comandos no `stella --help`, cada um com teste.
- `uv run pytest` todo verde; ruff + format + mypy limpos.
- Nenhuma regressão na suíte existente.
- Árvore pronta (NÃO commitar); avisar o Claude para revisar e commitar na branch
  `feat/conteudo-v2-f1` (ou abrir `feat/conteudo-v2-f2`).
