"""Tests for stardeck parser."""

from stardeck.parser import (
    ClickDefaults,
    ClickResult,
    extract_notes,
    parse_deck,
    parse_frontmatter,
    split_slides,
    transform_click_tags,
    transform_clicks_wrapper,
)


def test_split_slides_basic():
    content = "# Slide 1\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert result[0] == "# Slide 1"
    assert result[1] == "# Slide 2"


def test_split_slides_single():
    content = "# Single Slide"
    result = split_slides(content)
    assert len(result) == 1
    assert result[0] == "# Single Slide"


def test_split_slides_empty_slides():
    content = "# Slide 1\n---\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 3
    assert result[1] == ""


def test_split_slides_only_delimiter_at_line_start():
    content = "# Slide with --- in middle\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert "---" in result[0]


def test_split_slides_empty_value_frontmatter():
    content = "# Slide 1\n---\nclass:\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert "class:" in result[1]


def test_split_slides_mid_deck_frontmatter():
    content = """# Slide 1
---
layout: cover
---
# Cover Slide
---
# Slide 3"""
    result = split_slides(content)
    assert len(result) == 3
    assert "layout: cover" in result[1]
    assert "Cover Slide" in result[1]


def test_parse_frontmatter():
    raw = "---\nlayout: cover\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert content == "# Title"


def test_parse_frontmatter_multiple_keys():
    raw = "---\nlayout: cover\ntransition: slide-left\nbackground: ./bg.jpg\n---\n# Content"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert fm["transition"] == "slide-left"
    assert fm["background"] == "./bg.jpg"
    assert content == "# Content"


def test_parse_frontmatter_no_frontmatter():
    raw = "# Just Content\nNo frontmatter here"
    fm, content = parse_frontmatter(raw)
    assert fm == {}
    assert content == raw


def test_parse_frontmatter_empty():
    raw = "---\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm == {}
    assert content == "# Title"


def test_parse_frontmatter_empty_value():
    """Frontmatter with empty value (class:) should parse as None."""
    raw = "---\nclass:\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert "class" in fm
    assert fm["class"] is None
    assert content.strip() == "# Title"


def test_extract_notes():
    content = "# Slide\n<!-- notes\nSpeaker notes here\n-->"
    result, notes = extract_notes(content)
    assert "Speaker notes here" in notes
    assert "<!--" not in result


def test_extract_notes_no_notes():
    content = "# Slide\nNo notes here"
    result, notes = extract_notes(content)
    assert notes == ""
    assert result == content


def test_extract_notes_regular_comments():
    content = "# Slide\n<!-- regular comment -->\n<!-- notes\nSpeaker notes\n-->"
    result, notes = extract_notes(content)
    assert "regular comment" in result
    assert "Speaker notes" in notes


def test_extract_notes_multiline():
    content = "# Slide\n<!-- notes\nLine 1\nLine 2\nLine 3\n-->"
    result, notes = extract_notes(content)
    assert "Line 1" in notes
    assert "Line 2" in notes
    assert "Line 3" in notes


def test_extract_notes_multiple_blocks():
    """Multiple note blocks should all be captured."""
    content = "# Slide\n<!-- notes\nFirst\n-->\nMore content\n<!-- notes\nSecond\n-->"
    result, notes = extract_notes(content)
    assert "First" in notes
    assert "Second" in notes
    assert "<!--" not in result


# --- Click tag tests (CSS mode) ---


def test_transform_click_tags_css_mode():
    content = "<click>First</click><click>Second</click>"
    cr = transform_click_tags(content)
    assert isinstance(cr, ClickResult)
    assert cr.max_clicks == 2
    assert 'data-click="1"' in cr.content
    assert 'data-click="2"' in cr.content
    assert 'class="click-reveal"' in cr.content
    assert 'data-class:revealed="$clicks >= 1"' in cr.content
    assert 'data-class:revealed="$clicks >= 2"' in cr.content


def test_transform_click_tags_motion_mode():
    content = "<click>First</click><click>Second</click>"
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 2
    assert 'data-click="1"' in cr.content
    assert "data-motion=" in cr.content
    assert "type:visibility" in cr.content
    assert "data-computed" not in cr.content
    assert "signal:$vis1" in cr.content
    assert "signal:$vis2" in cr.content
    assert "enter_preset:fade" in cr.content


def test_transform_click_tags_motion_custom_animation():
    content = '<click animation="slide-up">Sliding</click>'
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 1
    assert "enter_preset:slide-up" in cr.content
    assert "signal:$vis1" in cr.content


def test_transform_click_tags_motion_default_animation():
    content = "<click>Content</click>"
    defaults = ClickDefaults(animation="bounce")
    cr = transform_click_tags(content, defaults=defaults, use_motion=True)
    assert "enter_preset:bounce" in cr.content


def test_transform_click_tags_per_click_overrides_default():
    content = '<click animation="scale">Override</click><click>Default</click>'
    defaults = ClickDefaults(animation="bounce")
    cr = transform_click_tags(content, defaults=defaults, use_motion=True)
    assert "enter_preset:scale" in cr.content
    assert "enter_preset:bounce" in cr.content


def test_transform_click_tags_preserves_content():
    content = "<click><p>Hello</p></click>"
    cr = transform_click_tags(content)
    assert "<p>Hello</p>" in cr.content


def test_transform_click_tags_no_clicks():
    content = "No click tags here"
    cr = transform_click_tags(content)
    assert cr.content == content
    assert cr.max_clicks == 0


def test_parse_deck(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n---\n# Slide 2")
    deck = parse_deck(md_file)
    assert deck.total == 2
    assert "<h1>" in deck.slides[0].content


def test_parse_deck_with_frontmatter(tmp_path):
    md_file = tmp_path / "slides.md"
    content = "---\nlayout: cover\n---\n# Title Slide\n---\n# Regular Slide"
    md_file.write_text(content)
    deck = parse_deck(md_file)
    assert deck.slides[0].layout == "cover"
    assert deck.slides[1].layout == "default"


def test_parse_deck_with_notes(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n<!-- notes\nSpeaker notes\n-->")
    deck = parse_deck(md_file)
    assert deck.total == 1
    assert "Speaker notes" in deck.slides[0].note


def test_parse_deck_mid_deck_frontmatter(tmp_path):
    md_file = tmp_path / "slides.md"
    content = """# Slide 1
---
layout: cover
---
# Cover Slide
---
# Slide 3"""
    md_file.write_text(content)
    deck = parse_deck(md_file)
    assert deck.total == 3
    assert deck.slides[1].layout == "cover"
    assert deck.slides[0].layout == "default"
    assert deck.slides[2].layout == "default"


def test_parse_deck_with_click_tags(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide\n<click>One</click>\n<click>Two</click>")
    deck = parse_deck(md_file)
    assert deck.slides[0].max_clicks == 2
    assert 'data-click="1"' in deck.slides[0].content
    assert 'data-click="2"' in deck.slides[0].content


def test_parse_deck_motion_mode(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide\n<click>One</click>\n<click>Two</click>")
    deck = parse_deck(md_file, use_motion=True)
    assert deck.slides[0].max_clicks == 2
    assert "type:visibility" in deck.slides[0].content
    assert "signal:$vis1" in deck.slides[0].content
    assert "signal:$vis2" in deck.slides[0].content


def test_parse_deck_click_animation_frontmatter(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("---\nclick-animation: slide-up\n---\n# Slide\n<click>A</click>")
    deck = parse_deck(md_file, use_motion=True)
    assert deck.config.click_animation == "slide-up"
    assert "enter_preset:slide-up" in deck.slides[0].content


def test_parse_deck_per_slide_click_animation(tmp_path):
    """Per-slide click-animation overrides the deck default."""
    md_file = tmp_path / "slides.md"
    md_file.write_text(
        "---\nclick-animation: fade\n---\n# S1\n<click>A</click>\n"
        "---\nclick-animation: bounce\n---\n# S2\n<click>B</click>"
    )
    deck = parse_deck(md_file, use_motion=True)
    assert "enter_preset:fade" in deck.slides[0].content
    assert "enter_preset:bounce" in deck.slides[1].content


def test_cls_to_class_in_html(tmp_path):
    """cls= in inline HTML should become class= (StarHTML convention)."""
    md_file = tmp_path / "slides.md"
    md_file.write_text('<div cls="text-blue-500 p-4">styled</div>')
    deck = parse_deck(md_file)
    assert 'class="text-blue-500 p-4"' in deck.slides[0].content
    assert "cls=" not in deck.slides[0].content


def test_cls_preserved_in_code_blocks(tmp_path):
    """cls= inside code fences should NOT be transformed."""
    md_file = tmp_path / "slides.md"
    md_file.write_text('```html\n<div cls="example">demo</div>\n```')
    deck = parse_deck(md_file)
    assert "cls" in deck.slides[0].content


def test_slide_left_preset():
    content = '<click animation="slide-left">Left</click>'
    cr = transform_click_tags(content, use_motion=True)
    assert "enter_preset:slide-left" in cr.content


def test_slide_right_preset():
    content = '<click animation="slide-right">Right</click>'
    cr = transform_click_tags(content, use_motion=True)
    assert "enter_preset:slide-right" in cr.content


def test_click_defaults_duration():
    defaults = ClickDefaults(duration=500)
    cr = transform_click_tags("<click>A</click>", defaults=defaults, use_motion=True)
    assert "enter_duration:500" in cr.content


def test_click_defaults_spring():
    defaults = ClickDefaults(spring="bouncy")
    cr = transform_click_tags("<click>A</click>", defaults=defaults, use_motion=True)
    assert "enter_spring:bouncy" in cr.content


def test_click_defaults_ease():
    defaults = ClickDefaults(ease="ease-in-out")
    cr = transform_click_tags("<click>A</click>", defaults=defaults, use_motion=True)
    assert "enter_ease:ease-in-out" in cr.content


def test_click_defaults_delay():
    defaults = ClickDefaults(delay=100)
    cr = transform_click_tags("<click>A</click>", defaults=defaults, use_motion=True)
    assert "enter_delay:100" in cr.content


def test_parse_deck_click_duration_frontmatter(tmp_path):
    md = tmp_path / "slides.md"
    md.write_text("---\nclick-duration: 500\n---\n# Slide\n<click>A</click>")
    deck = parse_deck(md, use_motion=True)
    assert deck.config.click_duration == 500
    assert "enter_duration:500" in deck.slides[0].content


def test_parse_deck_per_slide_click_duration(tmp_path):
    md = tmp_path / "slides.md"
    md.write_text("# S1\n<click>A</click>\n---\nclick-duration: 800\n---\n# S2\n<click>B</click>")
    deck = parse_deck(md, use_motion=True)
    assert "enter_duration:300" in deck.slides[0].content  # default
    assert "enter_duration:800" in deck.slides[1].content


def test_inline_duration_overrides_default():
    defaults = ClickDefaults(duration=500)
    cr = transform_click_tags(
        '<click duration="200">A</click>',
        defaults=defaults,
        use_motion=True,
    )
    assert "enter_duration:200" in cr.content


def test_inline_spring():
    cr = transform_click_tags(
        '<click spring="gentle">A</click>',
        use_motion=True,
    )
    assert "enter_spring:gentle" in cr.content


def test_inline_custom_transform():
    """Direct x/y/scale/rotate bypass preset."""
    cr = transform_click_tags(
        '<click x="30" opacity="0">A</click>',
        use_motion=True,
    )
    assert "enter_x:30" in cr.content
    assert "enter_opacity:0" in cr.content
    assert "enter_preset" not in cr.content


def test_inline_exit_attrs():
    cr = transform_click_tags(
        '<click exit-duration="400" exit-opacity="0">A</click>',
        use_motion=True,
    )
    assert "exit_duration:400" in cr.content
    assert "exit_opacity:0" in cr.content


def test_mixed_animation_and_duration():
    cr = transform_click_tags(
        '<click animation="slide-up" duration="600">A</click>',
        use_motion=True,
    )
    assert "enter_preset:slide-up" in cr.content
    assert "enter_duration:600" in cr.content


# --- Phase 1: <after> tag ---


def test_after_css_mode():
    content = "<click>A</click><after>B</after>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1
    assert 'data-class:revealed="$clicks >= 1"' in cr.content
    assert cr.content.count('data-click="1"') == 2


def test_after_motion_mode():
    content = "<click>A</click><after>B</after>"
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 1
    assert cr.content.count("signal:$vis1") == 2


def test_multiple_afters():
    content = "<click>A</click><after>B</after><after>C</after>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1
    assert cr.content.count('data-click="1"') == 3


def test_after_between_clicks():
    content = "<click>A</click><after>B</after><click>C</click><after>D</after>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 2
    assert 'data-class:revealed="$clicks >= 1"' in cr.content
    assert 'data-class:revealed="$clicks >= 2"' in cr.content
    # A and B at click 1, C and D at click 2
    parts = cr.content.split('data-click="2"')
    assert parts[0].count('data-click="1"') == 2


def test_after_with_attributes():
    content = '<click>A</click><after animation="slide-up">B</after>'
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 1
    assert "enter_preset:slide-up" in cr.content
    assert cr.content.count("signal:$vis1") == 2


def test_after_with_no_preceding_click():
    """<after> with no preceding <click> defaults to click 1."""
    content = "<after>A</after>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1
    assert 'data-click="1"' in cr.content
    assert 'data-class:revealed="$clicks >= 1"' in cr.content


# --- Phase 2: <click hide> ---


def test_hide_css_mode():
    content = "<click hide>Goes away</click>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1
    assert 'class="click-hide"' in cr.content
    assert 'data-class:click-hidden="$clicks >= 1"' in cr.content


def test_hide_motion_mode():
    """Hide elements use CSS opacity even in motion mode (no display:none layout shift)."""
    content = "<click hide>Goes away</click>"
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 1
    assert 'class="click-hide"' in cr.content
    assert 'data-class:click-hidden="$clicks >= 1"' in cr.content
    assert "data-motion" not in cr.content


def test_mixed_show_hide():
    content = "<click hide>Vanish</click><click>Appear</click>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 2
    assert 'data-class:click-hidden="$clicks >= 1"' in cr.content
    assert 'data-class:revealed="$clicks >= 2"' in cr.content


def test_hide_produces_correct_classes():
    content = "<click hide>A</click><click>B</click><click hide>C</click>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 3
    assert cr.content.count('class="click-hide"') == 2
    assert cr.content.count('class="click-reveal"') == 1


def test_after_hide():
    """<after hide> reuses previous click number with hide semantics."""
    content = "<click>A</click><after hide>B</after>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1
    assert 'data-class:revealed="$clicks >= 1"' in cr.content
    assert 'data-class:click-hidden="$clicks >= 1"' in cr.content


def test_hide_after_pair_wrapped_in_swap():
    """<click hide> followed by <after> wraps both in a .click-swap container."""
    content = "<click hide>Vanish</click>\n<after>Appear</after>"
    cr = transform_click_tags(content)
    assert 'class="click-swap"' in cr.content
    assert cr.content.count("click-swap") == 1
    assert "click-hide" in cr.content
    assert "click-reveal" in cr.content


def test_hide_without_after_no_swap():
    """<click hide> without a following <after> is not wrapped."""
    content = "<click hide>Vanish</click>\n<click>Show</click>"
    cr = transform_click_tags(content)
    assert "click-swap" not in cr.content


def test_multiple_hide_after_pairs():
    """Two hide+after pairs each get their own swap wrapper."""
    content = "<click hide>A</click><after>B</after><click hide>C</click><after>D</after>"
    cr = transform_click_tags(content)
    assert cr.content.count("click-swap") == 2
    assert cr.max_clicks == 2


# --- Phase 3: <clicks> wrapper ---


def test_clicks_wrapper_basic():
    content = "<clicks>\n\nFirst\n\nSecond\n\nThird\n\n</clicks>"
    result = transform_clicks_wrapper(content)
    assert result.count("<click>") == 3
    assert result.count("</click>") == 3
    assert "First" in result
    assert "Second" in result
    assert "Third" in result


def test_clicks_wrapper_attribute_passthrough():
    content = '<clicks animation="slide-up">\n\nA\n\nB\n\n</clicks>'
    result = transform_clicks_wrapper(content)
    assert result.count('<click animation="slide-up">') == 2


def test_clicks_wrapper_empty_paragraphs_skipped():
    content = "<clicks>\n\nA\n\n\n\nB\n\n</clicks>"
    result = transform_clicks_wrapper(content)
    assert result.count("<click>") == 2


def test_clicks_wrapper_integration(tmp_path):
    """<clicks> wrapper integrates with parse_deck."""
    md = tmp_path / "slides.md"
    md.write_text("# Slide\n<clicks>\n\nA\n\nB\n\nC\n\n</clicks>")
    deck = parse_deck(md)
    assert deck.slides[0].max_clicks == 3


def test_clicks_wrapper_empty():
    content = "<clicks></clicks>"
    result = transform_clicks_wrapper(content)
    assert "<click>" not in result


def test_clicks_wrapper_single_paragraph():
    content = "<clicks>\n\nOnly one\n\n</clicks>"
    result = transform_clicks_wrapper(content)
    assert result.count("<click>") == 1


# --- Phase 4: Click ranges at= ---


def test_at_explicit_number_css():
    content = '<click at="3">Late</click>'
    cr = transform_click_tags(content)
    assert cr.max_clicks == 3
    assert 'data-click="3"' in cr.content
    assert 'data-class:revealed="$clicks >= 3"' in cr.content


def test_at_explicit_number_motion():
    content = '<click at="3">Late</click>'
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 3
    assert "signal:$vis3" in cr.content


def test_at_range_css():
    content = '<click at="2-4">Temporary</click>'
    cr = transform_click_tags(content)
    assert cr.max_clicks == 4
    assert 'data-click="2-4"' in cr.content
    assert 'data-class:revealed="$clicks >= 2 && $clicks < 4"' in cr.content
    assert cr.range_clicks == frozenset({(2, 4)})


def test_at_range_motion():
    """Ranges use motion plugin like regular reveals."""
    content = '<click at="2-4">Temporary</click>'
    cr = transform_click_tags(content, use_motion=True)
    assert cr.max_clicks == 4
    assert "data-motion" in cr.content
    assert "signal:$vis_2_4" in cr.content
    assert cr.range_clicks == frozenset({(2, 4)})


def test_mixed_sequential_and_explicit():
    """Sequential counter stays independent from explicit at= numbers."""
    content = '<click>A</click><click at="5">B</click><click>C</click>'
    cr = transform_click_tags(content)
    assert cr.max_clicks == 5  # max(2, 5)
    assert 'data-click="1"' in cr.content
    assert 'data-click="5"' in cr.content
    assert 'data-click="2"' in cr.content


def test_at_with_hide():
    content = '<click hide at="3">Goes away at 3</click>'
    cr = transform_click_tags(content)
    assert cr.max_clicks == 3
    assert 'data-class:click-hidden="$clicks >= 3"' in cr.content


def test_max_clicks_accounting():
    """max_clicks = max(sequential_counter, highest_explicit)."""
    content = '<click>A</click><click at="10">B</click><click>C</click><click>D</click>'
    cr = transform_click_tags(content)
    assert cr.max_clicks == 10  # max(3, 10)


def test_overlapping_ranges():
    content = '<click at="1-3">X</click><click at="2-4">Y</click>'
    cr = transform_click_tags(content)
    assert cr.range_clicks == frozenset({(1, 3), (2, 4)})
    assert cr.max_clicks == 4


def test_range_signal_generation():
    """Range clicks produce vis_{lo}_{hi} signals in ClickResult."""
    content = '<click at="2-5">A</click><click at="1-3">B</click>'
    cr = transform_click_tags(content)
    assert cr.range_clicks == frozenset({(2, 5), (1, 3)})


# --- Code protection ---


def test_click_in_backtick_not_matched():
    """Backtick inline code `<click>` should not be matched as a click tag."""
    content = "Use `<click>` for reveals\n\n<click>Real</click>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1
    assert "`<click>`" in cr.content
    assert "Real" in cr.content


def test_click_in_code_fence_not_matched():
    """Code fences should protect <click> from being matched."""
    content = "```\n<click>Example</click>\n```\n\n<click>Real</click>"
    cr = transform_click_tags(content)
    assert cr.max_clicks == 1


def test_clicks_wrapper_skips_code():
    """<clicks> inside code blocks should not be expanded."""
    content = "Use `<clicks>` for bulk wrapping\n\n<clicks>\n\nA\n\nB\n\n</clicks>"
    result = transform_clicks_wrapper(content)
    assert "`<clicks>`" in result
    assert result.count("<click>") == 2
