from pathlib import Path


def test_frontend_avoids_html_string_injection_sinks():
    js = Path("static/app.js").read_text(encoding="utf-8")

    assert "innerHTML" not in js
    assert "insertAdjacentHTML" not in js
    assert "document.write" not in js
    assert "eval(" not in js
    assert "new Function" not in js


def test_html_uses_local_scripts_only():
    html = Path("static/index.html").read_text(encoding="utf-8")

    assert "https://cdn" not in html
    assert "<script src=\"/static/app.js\" defer></script>" in html


def test_html_has_apple_clean_analytics_layout_markers():
    html = Path("static/index.html").read_text(encoding="utf-8")

    assert "apple-shell" in html
    assert "hero-summary" in html
    assert "insight-stack" in html
    assert "delivery-grid" in html


def test_anchor_targets_leave_room_for_sticky_nav():
    css = Path("static/styles.css").read_text(encoding="utf-8")

    assert "scroll-margin-top" in css
    assert "[id]" in css
