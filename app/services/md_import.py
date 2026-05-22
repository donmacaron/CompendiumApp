import re
import markdown as md_lib


def md_to_html(md_text: str) -> str:
    """
    Convert Markdown to clean HTML using python-markdown.
    Extensions: tables, fenced_code, nl2br, sane_lists, attr_list.
    """
    html = md_lib.markdown(
        md_text,
        extensions=[
            "tables",
            "fenced_code",
            "nl2br",
            "sane_lists",
            "attr_list",
            "md_in_html",
        ],
        output_format="html",
    )
    return html


def extract_title(md_text: str, filename: str = "") -> str:
    """
    Extract title from the first # heading in the Markdown.
    Falls back to filename (without extension) if no heading found.
    """
    for line in md_text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    # Fallback: use filename
    if filename:
        name = Path(filename).stem
        # Convert snake_case / kebab-case to Title Case
        name = re.sub(r"[_\-]+", " ", name)
        return name.title()
    return "Imported Page"


def strip_first_h1(md_text: str) -> str:
    """Remove the first # heading from content (it becomes the page title)."""
    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("# "):
            # Remove this line and any blank line immediately after
            rest = lines[i+1:]
            while rest and rest[0].strip() == "":
                rest = rest[1:]
            return "\n".join(rest)
    return md_text


def parse_md_file(content_bytes: bytes, filename: str = "") -> dict:
    """
    Full parse: decode → extract title → convert body to HTML.
    Returns {"title": str, "html": str, "raw": str}.
    """
    # Try UTF-8, fall back to latin-1
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("latin-1")

    title   = extract_title(text, filename)
    body_md = strip_first_h1(text)
    html    = md_to_html(body_md)

    return {"title": title, "html": html, "raw": text}
