# 🌟 StarDeck: Product Requirements Document (MVP)

## 1. Product Vision
**"Slidev for Python."**
StarDeck is a developer-first presentation tool that treats slides as code. It allows users to write presentations in Markdown, style them with StarUI, and execute live Python code on the server—all without a single Node.js dependency.

**Core Philosophy:**
*   **Hypermedia-Driven:** No complex client-side router. The server determines the slide state; Datastar updates the DOM.
*   **Motion-First:** Animations are not an afterthought. They are powered by Motion.dev and Flubber via StarHTML plugins.
*   **Zero-Config:** `stardeck run slides.md` is all a user needs.

---

## 2. Core Mechanics & Architecture

### A. The "Slide as Code" Engine
Instead of Vue components (Slidev), we use **StarHTML Components**.
*   **Input:** A single `slides.md` file (or a folder of markdown files).
*   **Delimiter:** Slides are separated by `---`.
*   **Frontmatter:** Each slide block supports YAML frontmatter for layout, transitions, and background.

```markdown
---
layout: cover
background: ./assets/stars.jpg
transition: slide-left
---
# Welcome to StarDeck
Built with **StarHTML**
```

### B. The Rendering Pipeline
1.  **Parser:** Use `markdown-it-py` or `mistletoe` to parse Markdown to HTML.
2.  **Injector:** Middleware intercepts the HTML generation to:
    *   Wrap code blocks in **Starlighter** (syntax highlighting).
    *   Wrap standard HTML in **Motion.dev** wrappers (for entry animations).
    *   Inject interactive components (like **Starimo** for charts).
3.  **Server State:** The server holds the session state.
    *   `GET /`: Renders the full shell + Slide 0.
    *   `GET /slides/{idx}`: Returns *only* the inner HTML of the requested slide to be swapped via Datastar.

---

## 3. Key Features (The "Reveal.js" Parity)

### 3.1. Navigation & Routing
*   **Linear Navigation:** Left/Right arrow keys.
*   **Deep Linking:** URL updates automatically (`localhost:8000/#3`). Reloading the page keeps you on Slide 3.
*   **Overview Mode:** Press `o` or `Esc` to zoom out and see a grid of all slides (The "Light Table" view).
    *   *Tech:* Use Motion.dev `layoutId` animations to smoothly transition from full screen to grid card.

### 3.2. "Magic" Animations (The Slidev/Keynote Feel)
This is where your **Motion.dev** and **Flubber** plugins shine.
*   **Element Matching:** If an element on Slide 1 has `id="hero-img"` and Slide 2 has `id="hero-img"`, StarDeck automatically handles the layout animation (shared element transition) using Motion.dev.
*   **Shape Morphing:** A special Markdown syntax for SVG morphs using Flubber.
    ```html
    <!-- Slide 1 -->
    <star-shape type="circle" id="morph-me" />
    <!-- Slide 2 -->
    <star-shape type="star" id="morph-me" />
    <!-- The plugin handles the flubber interpolation automatically -->
    ```

### 3.3. Live Code Execution (The Python Advantage)
Slidev runs JS. StarDeck runs Python.
*   **The Feature:** A "Runner" block in Markdown.
    ```markdown
    ```python {run}
    import matplotlib.pyplot as plt
    plt.plot([1, 2, 3])
    # StarDeck automatically captures the plot and renders it here
    ```
*   **Implementation:** Backend captures `stdout` or returned image buffers and injects them into the slide HTML before sending to client.

### 3.4. Presenter Mode
A separate window meant for the second screen.
*   **Current Slide:** Live sync with the main window.
*   **Next Slide:** Preview of `idx + 1`.
*   **Notes:** Parsed from `<!-- comments -->` in Markdown.
*   **Timer:** A simple StarUI timer component.

---

## 4. UI/UX & The StarHTML Ecosystem Integration

### A. Layouts (StarUI)
StarDeck should come with pre-built layouts defined as StarHTML components. Users can switch them via frontmatter.
*   `cover`: Centered, big text.
*   `split-left` / `split-right`: Text on one side, image/code on the other.
*   `code-focus`: Dark mode, full screen code editor.

### B. Theming
*   Use **Tailwind* or CSS.

---

## 5. Technical Specification (Draft)

### Dependencies
*   **StarHTML:** Core server.
*   **Datastar:** Reactivity (signals for slide index, fragment swapping).
*   **Watchfiles:** To trigger a "Hot Reload" signal when `slides.md` is saved.
*   **Motion Plugin:** For entry/exit and layout animations.
*   **Flubber Plugin:** For SVG tweening.

### Datastar Signals Strategy
We will use signals to manage client-side ephemeral state while the server manages the source of truth.

```javascript
/* Client State Signals */
{
    slideIndex: 0,
    totalSlides: 15,
    presenterMode: false,
    scale: 1.0
}
```

### The "Hot Reload" Flow
1.  User edits `slides.md`.
2.  Python `watchfiles` detects change.
3.  Server sends an **SSE (Server Sent Event)** to the client.
4.  Client triggers a Datastar `get` request to re-fetch the *current* slide content.
5.  **Result:** Instant update without a full page refresh (preserving scroll/state).

---

## 6. MVP Roadmap

### Phase 1: The Engine (Week 1)
*   [ ] Markdown parser that splits by `---`.
*   [ ] Basic FastHTML server serving slides by index.
*   [ ] Datastar navigation (Next/Prev buttons swapping HTML).
*   [ ] Starlighter integration for static code blocks.

### Phase 2: The Experience (Week 2)
*   [ ] Keyboard shortcuts (Arrows, Space).
*   [ ] Motion.dev integration (Slide transitions: Fade, Slide-in).
*   [ ] URL Hash synchronization.
*   [ ] "Watch mode" (Hot reloading).

### Phase 3: The "Star" Polish (Week 3)
*   [ ] **Starimo** Integration: Interactive charts in slides.
*   [ ] **Flubber**: Demo of shape morphing between slides.
*   [ ] Presenter Mode (Multi-window sync).
*   [ ] `pip install stardeck` CLI tool.

---

## 7. Competitive Differentiation (Marketing)

| Feature | Slidev | Reveal.js | **StarDeck** |
| :--- | :--- | :--- | :--- |
| **Language** | Vue / JS | HTML / JS | **Python / StarHTML** |
| **Live Code** | JS only | JS only | **Full Python Backend** |
| **Animations** | CSS / Vue Transition | CSS | **Motion.dev + Flubber** |
| **Build Tool** | Vite (npm) | Gulp/Webpack | **None (Just Python)** |
| **Complexity** | High (Vue knowledge helpful) | Medium | **Low (Markdown only)** |

### Naming Confirmation
**Project Name:** `StarDeck`
**CLI Command:** `stardeck` (e.g., `stardeck dev slides.md`)

This PRD leverages your existing `star*` ecosystem to provide a tool that is functionally superior for Python developers than anything currently on the market.