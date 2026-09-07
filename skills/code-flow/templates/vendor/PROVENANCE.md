# Embedded dependencies

- **Dagre 3.1.1:** `@dagrejs/dagre`, pinned by the root package lock. [Upstream](https://github.com/dagrejs/dagre). Regenerate with `npm run vendor`. The browser bundle has its source-map directive removed; license and bundled notices are preserved and embedded in generated pages. No CDN request occurs.
- **Noto Sans KR:** [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/notosanskr). Source TTF SHA-256: `194018e6b2b293a7964f037b25c0249ce1418bc9ab3c971060a03aa57861e252`. Converted with FontTools 4.64.0/Brotli 1.2.0 into WOFF2. Retains variable weights and the character ranges below. The original OFL license is preserved and embedded in generated pages.

Font character ranges:

~~~text
0020–00FF, 1100–11FF, 2000–206F, 2190–21FF, 2500–25FF,
3000–303F, 3130–318F, AC00–D7A3, FF00–FFEF
~~~

This includes all modern precomposed Hangul syllables. The font is a local fallback for Korean explanations on machines without Korean system fonts. FontTools is a development conversion tool; it is not a renderer runtime dependency.
