---
id: cores-contraste-acessibilidade
nome: Cores, Contraste e Acessibilidade
descricao: Padrões WCAG AA aplicados a social media design dark-mode, com paletas práticas para Instagram.
gatilhos: [cores, contraste, acessibilidade, wcag, paleta]
modelo_minimo: gemma
tags: [design, acessibilidade, cores]
---

# Cores, Contraste e Acessibilidade

## Padrão mínimo: WCAG AA

- **Texto normal (< 18pt):** ratio mínimo 4.5:1 entre texto e fundo.
- **Texto grande (≥ 18pt bold ou ≥ 24pt regular):** ratio mínimo 3:1.
- **Componentes de UI e gráficos:** ratio mínimo 3:1 com contexto adjacente.

## Calculadora rápida (dark background #0D0D0F)

| Cor do texto | Ratio aproximado | Adequado para |
|---|---|---|
| Branco puro #FFFFFF | 20.9:1 | qualquer texto |
| Ciano #22D3EE | 12.3:1 | headlines, destaque |
| Oliva #AEBD63 | 7.4:1 | subheads, bullets |
| Branco 70% #B3B3B3 | 10.8:1 | body text |
| Cinza médio #6B7280 | 4.7:1 | captions (AA border) |

## Paleta mktmagneto.ia

```
dark:   #0D0D0F  (fundo)
accent: #22D3EE  (ciano — destaques, CTAs)
apoio:  #AEBD63  (oliva — pontos de suporte)
text:   #FFFFFF  (100% — headlines)
text2:  #B3B3B3  (70% — body)
text3:  #6B7280  (40% — captions)
```

## Regras práticas

- Nunca colocar texto de acento sobre fundo de acento — sempre sobre dark.
- Gradientes: verificar contraste no ponto mais claro.
- Imagens de fundo: overlay dark 60-80% antes de colocar texto.
- Status/badges: usar cor + ícone (não depender só de cor para daltonismo).
