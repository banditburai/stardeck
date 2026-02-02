# Slidev Presenter Mode Research

> **Purpose:** Document Slidev's presenter mode to inform StarDeck implementation
> **Source:** [Slidev UI Guide](https://sli.dev/guide/ui)

## Access

- URL: `http://localhost:<port>/presenter`
- Button in navigation panel

## Core Layout

Presenter view displays:
1. **Current slide** - prominently displayed
2. **Next slide preview** - below current slide
3. **Speaker notes** - rendered markdown/HTML from slide comments
4. **Timer** - elapsed time since start

## Layout Options (v0.50.0+)

Three layouts available, cycled via button:

| Layout | Description |
|--------|-------------|
| 1 | Current slide top, notes + next below |
| 2 | Notes left, current + next stacked right |
| 3 | Notes + current left, larger next right |

## Multi-Window Sync

**Key feature:** Open two browser windows:
- Window 1: Play mode (audience view)
- Window 2: Presenter mode (speaker view)

When navigating in presenter mode, **all other windows automatically follow**.

Implementation: Likely uses BroadcastChannel API or similar for cross-window communication.

## Speaker Notes Syntax

Notes are HTML comments at end of each slide:

```markdown
---
layout: cover
---

# Slide 1

Content here.

<!--
Speaker notes go here.
**Markdown** and HTML supported.
-->
```

⚠️ Notes must be at the **end of the slide** to be recognized.

## Additional Features

| Feature | Description |
|---------|-------------|
| Screen Mirror | Display another monitor/window in presenter view |
| Notes Editor | Batch edit notes at `/notes-edit` |
| Camera View | Overlay camera feed on slides |
| Recording | Built-in recording with RecordRTC |

## Keyboard Shortcuts

Same as play mode:
- `→` / `Space`: Next animation/slide
- `←`: Previous animation/slide
- `↑`: Previous slide (skip animations)
- `↓`: Next slide (skip animations)
- `f`: Toggle fullscreen
- `o`: Quick overview
- `d`: Dark mode toggle
- `g`: Goto slide

## StarDeck Implementation Priority

### MVP (Phase 3b)
1. `/presenter` route
2. Current slide display
3. Next slide preview
4. Speaker notes display (already parsed)
5. Timer (elapsed time)
6. Multi-window sync via SSE

### Later
- Multiple layout options
- Notes editor
- Camera overlay
- Recording

## Comparison: Slidev vs StarDeck

| Feature | Slidev | StarDeck (current) | StarDeck (planned) |
|---------|--------|-------------------|-------------------|
| Notes parsing | Yes | Yes | Yes |
| Notes display | Yes | No | Phase 3b |
| Current slide | Yes | No | Phase 3b |
| Next preview | Yes | No | Phase 3b |
| Timer | Yes | No | Phase 3b |
| Multi-window sync | Yes | No | Phase 3b |
| Layout options | 3 | 0 | Future |
| Notes editor | Yes | No | Future |
| Camera | Yes | No | Future |
| Recording | Yes | No | Phase 5 |

## Technical Considerations

### Multi-Window Sync Options

1. **BroadcastChannel API** - Modern, simple, same-origin only
2. **SharedWorker** - More complex, persistent
3. **Server-Sent Events** - Already using, server manages state
4. **localStorage events** - Works across tabs

**Recommended for StarDeck:** SSE-based sync
- Server already manages slide state
- Presenter sends navigation commands
- All connected clients receive updates
- Already have the infrastructure

### Timer Implementation

Options:
1. **Client-side only** - Simple, no server needed
2. **Server-synced** - Accurate across windows

**Recommended:** Client-side timer in presenter view, server provides start timestamp for sync if needed.
