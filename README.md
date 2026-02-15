# StarDeck

Developer-first presentation tool for Python. Write slides in Markdown, present with a reactive UI powered by [StarHTML](https://github.com/banditburai/starhtml) and [Datastar](https://data-star.dev).

## Features

- **Markdown slides** — Write in familiar Markdown with `---` separators
- **Click animations** — Progressive reveal, hide, swap, bulk wrap, and explicit ranges with Motion-powered animations
- **Layouts** — cover, center, two-cols, three-cols, grid, quote, section, steps, and more
- **Region tags** — `<left>`, `<right>`, `<item>`, `<step>` for structured layouts
- **Inline HTML + Tailwind** — Use any HTML with Tailwind CSS v4 classes in your slides
- **Presenter mode** — Speaker notes, timer, next-slide preview, drawing tools
- **Live reload** — Edit slides, see changes instantly with `--watch`
- **Keyboard navigation** — Arrow keys, Space, grid overview (G/O)
- **Static export** — Self-contained HTML output, no server required
- **Tunnel sharing** — Share presentations publicly with `--share`
- **Themes** — Dark and light themes, themeable with CSS variables

## Quick Start

```bash
pip install stardeck
```

Create `slides.md`:

```markdown
---
title: My Presentation
---

# Hello World

My first slide

---

## Second Slide

- Point one
- Point two

<click>Revealed on click</click>

---
layout: two-cols
---

<left>

## Left Column

Content here

</left>

<right>

## Right Column

More content

</right>
```

Run it:

```bash
stardeck run slides.md
```

## Usage

```bash
# Run with live reload
stardeck run slides.md --watch

# Run with a theme
stardeck run slides.md --theme light

# Run with public tunnel
stardeck run slides.md --share

# Export to static HTML
stardeck export slides.md --output dist/
```

## Slide Authoring

### Frontmatter

Each slide can have YAML frontmatter for configuration:

```markdown
---
layout: cover
transition: slide-left
background: "#2563eb"
class: items-center justify-center
---
```

The first slide's frontmatter also sets deck-wide options: `title` (page title), `transition` (default transition), and click animation defaults (`click-animation`, `click-duration`, `click-delay`, `click-ease`, `click-spring`).

### Click Animations

Wrap content in `<click>` tags for progressive reveal:

```markdown
<click>First point appears</click>
<click>Then the second</click>
<click>Finally the third</click>
```

Press arrow keys or Space to step through clicks before advancing to the next slide.

Click reveals are powered by the [Motion](https://motion.dev) animation library in server mode, with spring physics and configurable presets.

**Available presets:** `fade` (default), `slide-up`, `slide-down`, `slide-left`, `slide-right`, `scale`, `bounce`.

#### Animation attributes

Set the animation per-click with inline attributes:

```markdown
<click animation="slide-up">Slides up into view</click>
<click animation="scale" duration="500">Slow scale-in</click>
<click animation="bounce" spring="bouncy">Bouncy entrance</click>
```

| Attribute | Description | Example |
|-----------|-------------|---------|
| `animation` | Preset name | `animation="slide-up"` |
| `duration` | Duration in ms | `duration="500"` |
| `delay` | Delay before animation in ms | `delay="200"` |
| `ease` | CSS easing function | `ease="ease-in-out"` |
| `spring` | Spring physics preset | `spring="bouncy"` |

Spring presets: `gentle`, `bouncy`, `tight`, `slow`.

#### Custom transforms

Override presets entirely with individual transform properties:

```markdown
<click x="30" opacity="0">Slide in from right with fade</click>
<click y="-20" scale="0.8">Drop in and grow</click>
<click rotate="10" opacity="0">Rotate in</click>
```

Properties: `x`, `y`, `scale`, `rotate`, `opacity`. When any transform property is set, the preset is bypassed.

#### Exit animations

Control how elements animate out when stepping backwards:

```markdown
<click exit-opacity="0" exit-duration="200">Fast fade out on reverse</click>
```

Exit attributes mirror enter attributes with an `exit-` prefix: `exit-duration`, `exit-delay`, `exit-ease`, `exit-spring`, `exit-x`, `exit-y`, `exit-scale`, `exit-rotate`, `exit-opacity`.

#### Per-slide and deck-wide defaults

Set defaults via frontmatter — per-slide overrides deck-wide:

```markdown
---
click-animation: slide-up
click-duration: 400
click-spring: gentle
---
```

Deck-wide defaults go in the first slide's frontmatter. Per-slide frontmatter overrides them. Inline attributes on individual `<click>` tags override both.

#### Same-step reveals with `<after>`

`<after>` shares the same click step as the preceding `<click>`:

```markdown
<click>Main point (click 1)</click>
<after>Also appears at click 1</after>
<after>This too (click 1)</after>

<click>Next point (click 2)</click>
<after>Also at click 2</after>
```

#### Hide on click

`<click hide>` starts visible and disappears on its click step:

```markdown
<click hide>This vanishes at click 1</click>
<after>This replaces it at click 1</after>
```

A `<click hide>` followed by `<after>` creates a swap — the hide and reveal animate together in-place.

#### Bulk reveals with `<clicks>`

`<clicks>` wraps each paragraph in a `<click>` tag automatically:

```markdown
<clicks animation="slide-up">

First point

Second point

Third point

</clicks>
```

Attributes on `<clicks>` cascade to all children. Equivalent to writing three separate `<click animation="slide-up">` tags.

#### Explicit numbering with `at=`

Pin elements to specific click numbers or visibility ranges:

```markdown
<click at="3">Appears at click 3</click>
<click at="2-4">Visible during clicks 2–3, gone at 4</click>
```

Sequential `<click>` tags and explicit `at=` numbering are independent — `max_clicks` is the maximum of both. Ranges can overlap.

### Speaker Notes

Add notes inside HTML comments with the `notes` keyword:

```markdown
# My Slide

Content here

<!-- notes
These notes appear in presenter mode only.
Multiple note blocks per slide are supported.
-->
```

### Backgrounds

Set solid colors or images via frontmatter:

```markdown
---
background: "#2563eb"
---

---
background: assets/hero.jpg
---
```

### Images

Standard Markdown images work. Place files in an `assets/` directory next to your slides — it's auto-mounted during serve and auto-copied on export:

```markdown
![diagram](assets/architecture.png)
```

For image-based layouts, use the `image` frontmatter key:

```markdown
---
layout: image-left
image: assets/photo.jpg
---
```

### Inline HTML & Tailwind

Raw HTML with Tailwind classes works directly in slides:

```markdown
<div class="text-blue-500 text-4xl p-8 rounded-lg bg-blue-500/10">
  Styled with Tailwind v4
</div>
```

The `cls=` alias is also supported (StarHTML convention): `<div cls="text-red-500">`.

You can also add classes to entire slides via frontmatter:

```markdown
---
class: items-center justify-center text-center
---
```

## Layouts

Set layouts in slide frontmatter:

```markdown
---
layout: cover
---
```

**Available layouts:** `default`, `cover`, `center`, `section`, `quote`, `fact`, `statement`, `full`, `two-cols`, `three-cols`, `grid`, `steps`, `comparison`, `sidebar-left`, `sidebar-right`, `image-left`, `image-right`, `hero`, `caption`.

### Region Tags

Multi-column and structured layouts use region tags:

```markdown
---
layout: two-cols
---

<left>
Left content
</left>

<right>
Right content
</right>
```

Available tags: `<left>`, `<right>`, `<top>`, `<bottom>`, `<main>`, `<sidebar>`, `<item>`, `<step>`.

The `grid` layout supports custom columns with `cols`:

```markdown
---
layout: grid
cols: 3
---

<item>Card 1</item>
<item>Card 2</item>
<item>Card 3</item>
```

## Transitions

Set per-slide transitions in frontmatter, or set a default in the first slide:

```markdown
---
transition: slide-left
---
```

**Available:** `fade` (default), `slide-left`, `slide-right`, `slide-up`, `slide-down`.

## Themes

Two built-in themes:

- **default** — Dark theme with teal accents (Monokai-inspired code highlighting)
- **light** — Light theme with teal accents (GitHub-inspired code highlighting)

```bash
stardeck run slides.md --theme light
stardeck export slides.md --theme light
```

Themes are CSS files in `stardeck/themes/`. Override CSS variables to customize:

```css
.stardeck-root {
    --accent: #8b5cf6;
    --bg-dark: #0a0a0a;
    --bg-slide: #171717;
    --text-primary: #e4e4e7;
    --text-heading: #fafafa;
}
```

### Utility Classes

Themes provide presentation-specific utility classes:

- **Typography:** `text-hero`, `text-title`, `text-subtitle`, `text-body`, `text-small`, `text-caption`
- **Color:** `text-accent`, `text-heading`, `text-muted`
- **Padding:** `slide-p-0`, `slide-p-sm`, `slide-p-lg`

## Presenter Mode

When you run `stardeck run`, the CLI prints a presenter URL with an auth token:

```
Presenter: http://localhost:5001/presenter?token=abc123
```

The presenter view includes:

- Current slide with drawing tools (pen, shapes, arrows)
- Next slide preview
- Speaker notes
- Elapsed timer
- Keyboard navigation (same as audience view)

Drawings sync to the audience view in real time.

## URL Hash Navigation

URLs update to `#slide.click` format (e.g., `#3.2` for slide 3, click 2). Share links to specific slides, and browser back/forward buttons work.

## Development

```bash
git clone https://github.com/banditburai/stardeck.git
cd stardeck
uv sync --all-extras

uv run pytest                  # tests
uv run ruff check              # lint
uv run ruff format --check     # format
uv run pyright                 # type check
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
