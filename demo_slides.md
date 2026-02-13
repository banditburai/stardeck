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
<div class="text-blue-500 p-4">styled whatever we want</div>
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
layout: center
---

# Centered Layout

Everything centered — great for title cards

---
layout: section
---

# Section Heading

Use this to introduce a new topic

---
layout: quote
---

> The best way to predict the future is to invent it.
>
> — Alan Kay

---
layout: fact
---

# 120

tests passing

---
layout: two-cols
---

<left>

## Benefits

- Fast rendering
- Python native
- Zero config
- Hot reload

</left>

<right>

## Stack

- StarHTML for components
- Datastar for reactivity
- markdown-it for parsing
- Pygments for syntax

</right>

---
layout: statement
---

# Markdown In. Slides Out.

---
layout: grid
cols: 3
---

## Our Stack

<item>

### Python

Backend power

</item>

<item>

### Datastar

Reactive UI

</item>

<item>

### Markdown

Simple authoring

</item>

---
layout: steps
---

## Getting Started

<step>

### Install

`pip install stardeck`

</step>

<step>

### Write Slides

Create a `slides.md` file with `---` separators

</step>

<step>

### Present

Run `stardeck run slides.md`

</step>

---
class: items-center justify-center text-center
---

# Tailwind Utilities

This slide uses `class: items-center justify-center text-center` in frontmatter

All standard Tailwind classes work — powered by Tailwind Browser v4

---
layout: full
---

# Full Layout

This slide has no padding — content goes edge to edge.

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
