---
id: selecao-template-por-conteudo
nome: Seleção de Template por Conteúdo
descricao: Framework de decisão para escolher o template visual certo baseado no tipo de conteúdo e objetivo do post.
gatilhos: [template, selecao, conteudo, tipo-post, carrossel]
modelo_minimo: sonnet
tags: [design, template, decisao]
---

# Seleção de Template por Conteúdo

## Árvore de decisão

```
Qual é o conteúdo principal do post?
│
├── Dado numérico / estatística forte
│   └── → template: info-data (número grande em destaque)
│
├── Processo / passo-a-passo
│   └── → template: carrossel-lista (bullets numerados)
│
├── Citação ou insight forte (1 ideia)
│   └── → template: quote-hero (tipografia grande, espaço negativo)
│
├── Comparação (antes/depois, A vs B)
│   └── → template: split-comparison (2 colunas)
│
└── Texto com keyword principal por slide
    └── → template: carrossel-tipografico (1 keyword grande + contexto)
```

## Critérios secundários

- **≤ 3 slides:** quote-hero ou info-data. 4-7 slides: carrossel-tipografico ou lista. 8+: lista com agrupamento.
- **Pilar 1-2 (topo):** visual bold, impacto emocional. Pilar 3 (nicho): diagrama, lista técnica. Pilar 4 (prova): dado real, screenshot.

## Anti-padrões de seleção

- Usar quote-hero para conteúdo com 6+ slides — visual fica vazio.
- Usar carrossel-tipografico para dados numéricos — perde o impacto do número.
- Forçar split quando o conteúdo não é binário — confunde mais do que ajuda.
