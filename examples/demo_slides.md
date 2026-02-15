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

<click>First point fades in</click>

<click animation="slide-up">This slides up</click>

<click animation="scale">This scales in</click>

<click animation="slide-left">And this slides from the left</click>

<!-- notes
Press → or Space to reveal each point.
Press ← to reverse with exit animations.
URL updates to #slide.click as you go.
-->

---
click-animation: slide-up
---

## Progressive List

A common pattern — reveal bullet points one at a time:

<click>

- **Step 1** — Install with `pip install stardeck`

</click>

<click>

- **Step 2** — Write slides in Markdown with `---` separators

</click>

<click>

- **Step 3** — Run `stardeck run slides.md` and present

</click>

<!-- notes
Per-slide click-animation frontmatter sets the default.
Each click wraps a full markdown block — not just text.
-->

---
click-animation: slide-right
click-duration: 500
---

## Advanced Click Controls

Inline attributes give full control over each reveal:

<click animation="slide-left" duration="400">Slide in from the left (400ms)</click>

<click animation="slide-right" spring="bouncy">Bouncy slide from the right</click>

<click duration="800" ease="ease-in-out">Slow fade with custom easing</click>

<click x="30" opacity="0">Custom transform — no preset, pure x + opacity</click>

<!-- notes
Per-slide frontmatter: click-animation, click-duration, click-spring, click-ease.
Inline attrs override defaults: animation, duration, delay, spring, ease.
Custom transforms (x, y, scale, rotate, opacity) bypass presets entirely.
Exit attrs: exit-duration, exit-opacity, etc.
-->

---

## After Tags

Elements appearing at the same click step:

<click>Main point appears (click 1)</click>

<after>This appears at the same time (also click 1)</after>

<click>Next point (click 2)</click>

<after>Also at click 2</after>

<after>And this too (click 2)</after>

<!-- notes
<after> reuses the previous click number.
Multiple afters chain to the same step.
-->

---

## Click Hide

Elements that start visible and disappear:

<click hide>This text vanishes at click 1</click>

<after>This text appears at click 1</after>

<click hide>This vanishes at click 2</click>

<after>This appears at click 2</after>

<!-- notes
<click hide> + <after> creates a swap — hide and show happen on the same click.
<after> reuses the previous click number, so the pair animates together.
-->

---

## Clicks Wrapper

Auto-wrap each paragraph — no repetitive `<click>` tags:

<clicks animation="slide-up">

First item slides up

Second item slides up

Third item slides up

</clicks>

<!-- notes
<clicks> splits by paragraph breaks and wraps each in <click>.
Attributes cascade to all children.
-->

---

## Click Ranges

Explicit click numbering and timed visibility:

<click at="1">Appears at click 1 (explicit)</click>

<click at="2-4">Visible during clicks 2–3, gone at 4</click>

<click at="3">Appears at click 3 (overlaps with range)</click>

<click at="4">Appears at click 4 (after range ends)</click>

<!-- notes
at="N" pins to an explicit click number.
at="N-M" creates a range — visible from N, hidden at M.
Sequential counter and explicit numbers are independent.
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

# 166

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
cls: items-center justify-center text-center
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
