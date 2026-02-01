---
title: StarDeck Demo
theme: default
---

# Welcome to StarDeck

A Python-native presentation framework

*Slidev for Python*

---

## Features Built So Far

- Markdown parsing with `---` delimiters
- Syntax highlighted code blocks
- Keyboard navigation (←, →, Space)
- Responsive scaling
- CLI: `stardeck run slides.md`

---

## Code Example

```python
from stardeck.server import create_app
from pathlib import Path

app, rt, deck = create_app(Path("slides.md"))
print(f"Loaded {deck.total} slides")
```

---
layout: cover
---

# Cover Layout

This slide uses the `cover` layout

---
background: "#2563eb"
---

# Custom Background

This slide has a blue background

<!-- notes
These are speaker notes.
They won't be displayed in the presentation.
-->

---

## Navigation

| Key | Action |
|-----|--------|
| → | Next slide |
| ← | Previous slide |
| Space | Next slide |

---

# Thank You!

Built with ❤️ using StarHTML + Datastar
