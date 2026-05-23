---
id: design-tipografico-dark
nome: Design tipográfico em fundo escuro
descricao: Padrões de tipografia e hierarquia visual para designs em dark mode ou fundo escuro
gatilhos: [design, tipografia, dark, hierarquia, visual]
modelo_minimo: sonnet
tags: [design, visual]
---

# Design tipográfico em fundo escuro

## Princípio central

**Hierarquia clara + Contraste extremo** — em fundo escuro, a tipografia é a principal arma de contraste. Sem hierarquia agressiva, tudo desaparece visualmente.

## Regra da palavra-chave

**UMA palavra-chave por slide deve estar destacada em cor de acento.**

A palavra-chave é aquela que carrega o "stake" emocional ou intelectual do slide. Exemplos:

- Slide sobre "Prompts não são conversa" → destacar **"conversa"** (o que leitor estava fazendo errado)
- Slide sobre "IA 10x mais produtiva" → destacar **"10x"** (o número/resultado)
- Slide sobre "Erro comum em agentes" → destacar **"erro"** ou o tipo do erro (visual cue)

## Contraste sobre fundo escuro

- **Peso mínimo: 600 (semi-bold) a 700 (bold)** — fonte 400-500 vira cinzenta e desaparece
- **Tamanho mínimo: equivalente a 40px** — se está destacada, precisa ser grande. Pequeno = ênfase falsa
- **Cor de acento:** branco puro (#ffffff) · amarelo quente (#ffd700) · verde neon (#00ff41) · rosa (#ff1493)
  - Evitar: cinzas (perdem contraste), cores muito dessaturadas

## Regra dos 5 segundos

Leitor em scroll vê o slide por ~5 segundos. Nesse tempo, precisa entender:
1. Qual é o tema (grande, bold, claro)
2. Qual é o insight (a palavra destacada + cor)
3. Por que importa (1 subtítulo em corpo menor)

Se depois de 5 segundos o leitor ainda está tentando decifrar o slide, perdeu.

## Estrutura visual típica (recomendada)

```
[Fundo escuro — #1a1a1a ou #0f0f0f]

[Titulo grande — 60-80px, weight 700, cor clara (#f5f5f5 ou branco)]
[Palavra-chave destacada em cor de acento — 70-90px, weight 700, cor neon/vibrante]

[Subtítulo/contexto — 18-24px, weight 400, cor cinza-claro (#b0b0b0)]

[Máximo ~20 palavras total no slide]
```

## Densidade máxima

- **~20 palavras por slide** — objetivo é visual + textual = não sobrecarga
- Se tem 40+ palavras, é layout de documento, não de slide
- Priorizar: 1 frase principal (a palavra-chave em destaque) + 1 contexto + (opcionalmente) 1 CTA/ação

## Tipografia prática

- **Font family:** Helvetica, Arial, Inter, Roboto, ou sans-serif moderna (evitar serifas em tela escura — ficam pesadas)
- **Line-height:** 1.2–1.4 (justo, sem breathing room excessivo que quebre ritmo)
- **Espaçamento de letra:** 0 (nenhum) é ok; letter-spacing +2px pode funcionar em títulos mega-grandes para agressividade

## Anti-padrões

- ❌ Texto em cinza claro sobre preto — desaparece. Se é importante, branco ou cor.
- ❌ 3+ cores diferentes (além de fundo) — caótico. Máximo: branco/claro + 1 cor de acento
- ❌ Múltiplas palavras destacadas — dilui o "stake". Destacar == dar poder. Distribuir poder mata hierarquia.
- ❌ Fonte muito elegante/script — on dark, fica ilegível. Prefira moderno e clean

## Exemplos quick

**✅ Bom:**
```
Fundo: #1a1a1a
Título: "Prompt perfeito" (branco, 70px, bold)
Destaque: "não existe" (neon-pink #ff1493, 80px, bold)
Subtítulo: "Iteração é o segredo" (cinza, 20px, regular)
```

**❌ Ruim:**
```
Fundo: #000000 (muito puro)
Corpo: "Prompts perfis em IA são importantes porque..." (cinza médio, 16px)
Palavra-destaque: nenhuma
```
