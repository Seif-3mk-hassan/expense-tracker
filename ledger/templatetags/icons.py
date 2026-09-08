"""Consistent themeable SVG category icons (Lucide-style, inline, no dependency)."""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_PATHS = {
    "food": (
        '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/>'
        '<path d="M7 2v20"/>'
        '<path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3zm0 0v7"/>'
    ),
    "transport": (
        '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 '
        '10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.5 '
        '2.8A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/>'
        '<circle cx="7" cy="17" r="2"/><path d="M9 17h6"/>'
        '<circle cx="17" cy="17" r="2"/>'
    ),
    "housing": (
        '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
        '<path d="M9 22V12h6v10"/>'
    ),
    "fun": (
        '<path d="M6 11h4M8 9v4"/><path d="M15 12h.01M18 10h.01"/>'
        '<path d="M17.32 5H6.68a4 4 0 0 0-3.98 3.59C2.6 9.42 2 14.46 2 '
        '16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.41-1.41A2 2 0 0 1 9.83 16h4.34a2 '
        '2 0 0 1 1.41.59L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.54-.6-6.58-.68-7.26A4 '
        '4 0 0 0 17.32 5z"/>'
    ),
    "other": (
        '<path d="m7.5 4.27 9 5.15"/>'
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 '
        '3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
        '<path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>'
    ),
}


def category_icon(category, size=18):
    """Inline SVG for a Category (matched by name, falls back to a box)."""
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 18
    name = (getattr(category, "name", None) or str(category)).strip().lower()
    color = getattr(category, "color", None) or "#8B93A7"
    path = _PATHS.get(name, _PATHS["other"])
    return mark_safe(
        f'<span class="cicon"><svg width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{path}</svg></span>"
    )


register.filter("category_icon", category_icon)
