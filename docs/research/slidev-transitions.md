# Slidev Transitions Research

> **Purpose:** Document Slidev's transition system to inform StarDeck implementation
> **Source:** [Slidev Animation Documentation](https://sli.dev/guide/animations.html)

## Slidev Built-in Transitions

| Transition | Description | Reverses on Back |
|------------|-------------|------------------|
| `fade` | Crossfade effect | No |
| `fade-out` | Fade out then fade in (sequential) | No |
| `slide-left` | Slides to the left | Yes |
| `slide-right` | Slides to the right | Yes |
| `slide-up` | Slides upward | Yes |
| `slide-down` | Slides downward | Yes |
| `view-transition` | Uses View Transitions API | Browser-dependent |

## Frontmatter Syntax

### Global (all slides)
```yaml
---
transition: slide-left
---
```

### Per-slide override
```yaml
---
transition: fade
---

# This slide fades

---

# Back to global transition
```

### Forward/Backward Different Transitions
```yaml
---
transition: slide-left | slide-right
---
```
- First value = forward navigation
- Second value = backward navigation

## CSS Implementation

Slidev uses Vue's `<Transition>` component. Custom transitions follow Vue's naming convention:

```css
.my-transition-enter-active,
.my-transition-leave-active {
  transition: opacity 0.5s ease;
}

.my-transition-enter-from,
.my-transition-leave-to {
  opacity: 0;
}
```

### Built-in Transition CSS (approximation)

```css
/* fade */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* slide-left */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.slide-left-enter-from {
  transform: translateX(100%);
  opacity: 0;
}
.slide-left-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}
```

## StarDeck Implementation Approach

### Priority 1: Basic Transitions (MVP)
- `fade` - Simple, universal
- `slide-left` - Most common for forward progression
- `slide-right` - For backward or alternative flow

### Priority 2: Directional Transitions
- `slide-up`, `slide-down` - Vertical navigation
- Forward/backward syntax with `|` separator

### Priority 3: Advanced
- `view-transition` - Browser API (experimental)
- Custom transitions via CSS

### Implementation Strategy

1. **CSS-only approach** - No JavaScript needed for basic transitions
2. **Use CSS `@keyframes`** - Already have animations in default theme
3. **Data attribute for direction** - Track navigation direction to reverse when needed
4. **Frontmatter parsing** - Already support `transition` in frontmatter

### Current StarDeck State

StarDeck already has:
- `transition` frontmatter parsing
- `transition-fade` CSS class
- `render_slide()` applies `transition-{name}` class

What's needed:
- Add more built-in transition CSS
- Handle forward/backward direction
- Implement `|` syntax for directional transitions

### Recommended CSS for StarDeck

```css
/* Base transition timing */
.slide-viewport {
  position: relative;
  overflow: hidden;
}

/* Fade */
.transition-fade {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Slide Left (entering from right) */
.transition-slide-left {
  animation: slideInFromRight 0.3s ease-out;
}

@keyframes slideInFromRight {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

/* Slide Right (entering from left) */
.transition-slide-right {
  animation: slideInFromLeft 0.3s ease-out;
}

@keyframes slideInFromLeft {
  from { transform: translateX(-100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

/* Slide Up (entering from bottom) */
.transition-slide-up {
  animation: slideInFromBottom 0.3s ease-out;
}

@keyframes slideInFromBottom {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* Slide Down (entering from top) */
.transition-slide-down {
  animation: slideInFromTop 0.3s ease-out;
}

@keyframes slideInFromTop {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
```

## Comparison: Slidev vs StarDeck

| Feature | Slidev | StarDeck (current) | StarDeck (planned) |
|---------|--------|-------------------|-------------------|
| Fade | Yes | Yes | Yes |
| Slide-left/right | Yes | No | Yes |
| Slide-up/down | Yes | No | Yes |
| Forward/backward | Yes (`\|`) | No | Future |
| Custom CSS | Yes | Yes | Yes |
| View Transitions API | Yes | No | Future |
| Motion animations | Yes (@vueuse/motion) | No | Out of scope |

## Sources
- [Slidev Animation Documentation](https://sli.dev/guide/animations.html)
- [Vue Transition Documentation](https://vuejs.org/guide/built-ins/transition.html)
