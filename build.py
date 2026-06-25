import re
import shutil
from pathlib import Path
import markdown

SITE_NAME = "bluntbangs"
SITE_URL = "https://www.bluntbangs.com"

CONTENT_DIR = Path("content")
POSTS_DIR = CONTENT_DIR / "posts"
PAGES_DIR = CONTENT_DIR / "pages"

ASSETS_DIR = Path("assets")
OUTPUT_DIR = Path("docs")

TEMPLATES_DIR = Path("templates")


# --------------------------------------------------
# utility
# --------------------------------------------------

def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def parse_frontmatter(text):

    meta = {}

    m = re.match(
        r"^---\s*\n(.*?)\n---\s*\n?(.*)$",
        text,
        re.DOTALL,
    )

    if not m:
        return meta, text

    header = m.group(1)
    body = m.group(2)

    for line in header.splitlines():

        if ":" not in line:
            continue

        k, v = line.split(":", 1)

        meta[k.strip().lower()] = v.strip()

    return meta, body


def extract_title(text, fallback):

    m = re.search(
        r"^#\s+(.+)$",
        text,
        re.MULTILINE
    )

    if m:
        return m.group(1).strip()

    return fallback


def clean_html_to_text(html_text):
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def format_date_only(date_str):
    if not date_str:
        return ""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", date_str.strip())
    if m:
        return m.group(1)
    return date_str.strip()



def markdown_to_html(text):
    # Remove TOC placeholder if present
    cleaned_text = re.sub(r'^\[TOC\]\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

    md = markdown.Markdown(
        extensions=[
            "fenced_code",
            "tables",
        ]
    )

    return md.convert(cleaned_text)



def extract_slug(filename):
    return Path(filename).stem


# --------------------------------------------------
# templates
# --------------------------------------------------

BASE_TEMPLATE = read_file(TEMPLATES_DIR / "base.html")
POST_TEMPLATE = read_file(TEMPLATES_DIR / "post.html")
INDEX_TEMPLATE = read_file(TEMPLATES_DIR / "index.html")


def render(template, **kwargs):

    html = template

    for k, v in kwargs.items():
        html = html.replace(
            "{{" + k + "}}",
            str(v)
        )

    return html


# --------------------------------------------------
# build
# --------------------------------------------------

posts = []
warnings = []
errors = []


def build_posts():

    for md_file in POSTS_DIR.glob("*.md"):

        try:

            raw = read_file(md_file)

            meta, body = parse_frontmatter(raw)

            title = meta.get(
                "title",
                extract_title(body, md_file.stem)
            )

            date = meta.get(
                "date",
                ""
            )

            modified = meta.get(
                "modified",
                date
            )

            summary = meta.get(
                "summary",
                ""
            )

            slug = extract_slug(md_file.name)

            html = markdown_to_html(body)

            formatted_date = format_date_only(date)
            formatted_modified = format_date_only(modified)

            published_txt = f"投稿日: {formatted_date}" if formatted_date else ""
            modified_txt = ""

            if formatted_modified and formatted_modified != formatted_date:
                modified_txt = f"更新日: {formatted_modified}"

            content = render(
                POST_TEMPLATE,
                title=title,
                published_date=published_txt,
                modified_date=modified_txt,
                content=html,
            )



            desc = summary if summary else clean_html_to_text(html)[:140]

            page = render(
                BASE_TEMPLATE,
                page_title=title,
                site_name=SITE_NAME,
                content=content,
                description=desc,
                page_url=f"{SITE_URL}/{slug}.html",
                og_type="article",
            )

            write_file(
                OUTPUT_DIR / f"{slug}.html",
                page
            )

            posts.append({
                "title": title,
                "date": date,
                "modified": modified,
                "slug": slug,
                "summary": summary,
                "content": content,
                "body_html": html,
            })


            print(f"[OK] {md_file.name}")

        except Exception as e:

            errors.append(str(e))

            print(
                f"[ERROR] {md_file.name}: {e}"
            )



def build_pages():

    for md_file in PAGES_DIR.glob("*.md"):

        try:

            raw = read_file(md_file)

            meta, body = parse_frontmatter(raw)

            title = meta.get(
                "title",
                extract_title(body, md_file.stem)
            )

            html = markdown_to_html(body)

            content = render(
                POST_TEMPLATE,
                title=title,
                published_date="",
                modified_date="",
                content=html,
            )



            desc = clean_html_to_text(html)[:140]

            page = render(
                BASE_TEMPLATE,
                page_title=title,
                site_name=SITE_NAME,
                content=content,
                description=desc,
                page_url=f"{SITE_URL}/{md_file.stem}.html",
                og_type="website",
            )

            write_file(
                OUTPUT_DIR / f"{md_file.stem}.html",
                page
            )

            print(f"[OK] {md_file.name}")

        except Exception as e:

            errors.append(str(e))

            print(
                f"[ERROR] {md_file.name}: {e}"
            )



def get_preview_html(html_text, min_chars=300):
    # Extract <p>...</p> tags
    p_tags = re.findall(r'<p>.*?</p>', html_text, re.DOTALL)
    preview_paragraphs = []
    current_length = 0
    for p_tag in p_tags:
        preview_paragraphs.append(p_tag)
        # Count characters excluding tags
        plain_text = re.sub(r'<[^>]+>', '', p_tag)
        current_length += len(plain_text)
        if current_length >= min_chars:
            break

    # Guarantee at least 2 paragraphs if available
    if len(preview_paragraphs) < 2 and len(p_tags) >= 2:
        preview_paragraphs = p_tags[:2]

    return "\n".join(preview_paragraphs)


def build_index():

    posts.sort(
        key=lambda p: p["date"],
        reverse=True
    )

    latest_html = ""

    if posts:

        p = posts[0]

        # Generate excerpt (preview) HTML
        preview_body = get_preview_html(p["body_html"])
        
        # Add "Read more" link
        read_more_html = (
            f'<p class="read-more">'
            f'  <a href="{p["slug"]}.html">「{p["title"]}」の続きを読む &rarr;</a>'
            f'</p>'
        )
        if preview_body:
            preview_body += "\n" + read_more_html
        else:
            preview_body = read_more_html

        # Re-render latest post preview using POST_TEMPLATE
        formatted_date = format_date_only(p["date"])
        formatted_modified = format_date_only(p["modified"])

        published_txt = f"投稿日: {formatted_date}" if formatted_date else ""
        modified_txt = ""
        if formatted_modified and formatted_modified != formatted_date:
            modified_txt = f"更新日: {formatted_modified}"

        # Make the title a link to the individual post page on the index page
        title_link = f'<a href="{p["slug"]}.html">{p["title"]}</a>'

        latest_html = render(
            POST_TEMPLATE,
            title=title_link,
            published_date=published_txt,
            modified_date=modified_txt,
            content=preview_body,
        )



    items = []

    # Display remaining posts in the list (excluding the latest one)
    for p in posts[1:]:

        formatted_date = format_date_only(p["date"])
        display_date = f"投稿日: {formatted_date}" if formatted_date else ""

        items.append(
            f'<li>'
            f'  <div class="date-container">'
            f'    <span class="date">{display_date}</span>'
            f'  </div>'
            f'  <a href="{p["slug"]}.html">{p["title"]}</a>'
            f'</li>'
        )



    index_content = render(
        INDEX_TEMPLATE,
        latest=latest_html,
        posts="\n".join(items),
    )

    site_desc = posts[0]["summary"] if (posts and posts[0]["summary"]) else "bluntbangs blog"

    page = render(
        BASE_TEMPLATE,
        page_title=SITE_NAME,
        site_name=SITE_NAME,
        content=index_content,
        description=site_desc,
        page_url=f"{SITE_URL}/",
        og_type="website",
    )

    write_file(
        OUTPUT_DIR / "index.html",
        page
    )



def build_rss():

    posts.sort(
        key=lambda p: p["date"],
        reverse=True
    )

    items = []

    for p in posts[:30]:

        items.append(
f"""
<item>
<title>{p['title']}</title>
<link>{SITE_URL}/{p['slug']}.html</link>
<guid>{SITE_URL}/{p['slug']}.html</guid>
<description>{p['summary']}</description>
</item>
"""
        )

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>

<rss version="2.0">
<channel>

<title>{SITE_NAME}</title>
<link>{SITE_URL}</link>

{''.join(items)}

</channel>
</rss>
"""

    write_file(
        OUTPUT_DIR / "rss.xml",
        rss
    )


def copy_assets():

    if not ASSETS_DIR.exists():
        return

    for item in ASSETS_DIR.iterdir():

        dest = OUTPUT_DIR / item.name

        if item.is_dir():
            shutil.copytree(
                item,
                dest,
                dirs_exist_ok=True
            )
        else:
            shutil.copy2(
                item,
                dest
            )


def clean():

    if OUTPUT_DIR.exists():
        shutil.rmtree(
            OUTPUT_DIR
        )

    OUTPUT_DIR.mkdir(
        parents=True
    )


# --------------------------------------------------
# main
# --------------------------------------------------

clean()

copy_assets()

build_posts()

build_pages()

build_index()

build_rss()

print()
print("--------------------------------")
print("Build Summary")
print("--------------------------------")
print(f"Posts  : {len(posts)}")
print(f"Errors : {len(errors)}")
print("--------------------------------")
