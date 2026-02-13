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
| → | Next slide / Next click |
| ← | Previous slide / Previous click |
| Space | Next slide / Next click |

---

## Click Animations

Build your slides progressively:

<click>First point appears</click>

<click>Then the second point</click>

<click>Finally the third!</click>

<!-- notes
Demo the click animations:
- Press → or Space to reveal each point
- Press ← to hide them again
- Notice the URL updates to #slide.click format
-->

---

## Inline Image

Here's an image loaded from the assets directory:

![Test image](assets/test-image.png)

---
background: assets/test-image.png
---

# Background Image

This slide uses a local asset as the background

---

# Thank You!

Built with ❤️ using StarHTML + Datastar
