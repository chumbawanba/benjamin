# BRAND.md — Identidade de marca do Benjamin

> Extraído de `Benjamin_Brand_Identity.docx` (partilhado em chat, 2026-07-21). Nota: o
> ficheiro .docx só tem texto — não contém o ficheiro real do logo (o owl 🦉 lá dentro é
> só um emoji placeholder). O logo em si (imagem PNG com a coruja + wordmark "Benjamin")
> foi mostrado em chat mas ainda não existe como ficheiro no repositório — ver HANDOFF.md,
> "Próximos passos".

## Marca
- Nome: Benjamin
- Tagline: "Investe com cabeça, não por impulso." (anteriormente "Think before you invest.")
- Domínio: appbenjamin.com

## Mission / Values / Personality
- Mission: Help investors make disciplined decisions with AI.
- Values: Wisdom, Discipline, Transparency, Simplicity.
- Personality: Calm, Premium, Intelligent, Minimal.

## Identidade visual
- Primary: `#0F172A` (navy escuro — é o mesmo tom do logo da coruja)
- Background: `#FAFAF8`
- Surface: `#FFFFFF`
- Success: `#10B981`
- Warning: `#F59E0B`
- Danger: `#EF4444`
- Typography: Inter / SF Pro / Geist
- Style: Minimal, cantos arredondados, whitespace generoso

## Logo
Coruja minimalista inspirada na Coruja de Atena (sabedoria, decisão disciplinada) —
simples, circular, reconhecível como ícone de app.

## ⚠️ Discrepância a decidir
O `frontend/tailwind.config.js` já tem uma cor de destaque chamada `petrol` (verde-petróleo,
`#0f8f84` a `#052b28`), usada em toda a UI (botões, links, badges). O novo Primary da
identidade de marca (`#0F172A`) é **navy**, não verde — cores diferentes. Por decidir:
1. Substituir `petrol` pelo novo navy `#0F172A` em toda a UI (rebrand visual real), ou
2. Manter o verde-petróleo como está e usar o navy só no logo/marketing (landing page,
   favicon), sem tocar na app em si.

Ver `ROADMAP.md` secção 5 — a `benjamin-landing.html` enviada antes desta sessão tinha uma
identidade "verde-tinta/âmbar" diferente desta também; os três documentos (landing antiga,
este brand doc, e o `tailwind.config.js` real) não estão alinhados entre si ainda.
