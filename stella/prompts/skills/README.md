# Skills compartilhadas

Esta pasta é escaneada pelo `SkillsRegistry` (FB-M2) na startup da Stella.

Formato esperado: cada arquivo `.md` representa **uma skill** com frontmatter
contendo `id`, `nome`, `descricao`, `gatilhos`, `modelo_minimo` e `tags`.

Exemplo:

```yaml
---
id: marketing-copy-pt-br
nome: Copy de marketing PT-BR
descricao: Diretrizes para textos publicitários em português brasileiro
gatilhos: [copy, anuncio, landing-page]
modelo_minimo: sonnet
tags: [marketing, revisao]
---

# Conteúdo da skill em markdown...
```

Pasta vazia em FB-M2 (registry funciona sem skills cadastradas). Skills reais
entram quando Sub-projeto C (Time de Marketing) começar.
