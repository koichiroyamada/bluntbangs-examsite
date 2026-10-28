import re
import shutil
from html import escape
from pathlib import Path
import markdown

SITE_NAME = "bluntbangs"
SITE_URL = "https://www.bluntbangs.com"
SITE_DESCRIPTION = "bluntbangsの個人サイトです。日々の記録や、興味を持ったことを掲載しています。"

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
                latest_label="",
            )



            desc = summary if summary else clean_html_to_text(html)[:140]

            page = render(
                BASE_TEMPLATE,
                page_title=f"{title} | {SITE_NAME}",
                site_name=SITE_NAME,
                content=content,
                description=escape(desc, quote=True),
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
            })


            print(f"[生成] {md_file.name}")

        except Exception as e:

            errors.append(f"{md_file}: {e}")

            print(
                f"[エラー] {md_file.name}: {e}"
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
                latest_label="",
            )



            desc = clean_html_to_text(html)[:140]

            page = render(
                BASE_TEMPLATE,
                page_title=f"{title} | {SITE_NAME}",
                site_name=SITE_NAME,
                content=content,
                description=escape(desc, quote=True),
                page_url=f"{SITE_URL}/{md_file.stem}.html",
                og_type="website",
            )

            write_file(
                OUTPUT_DIR / f"{md_file.stem}.html",
                page
            )

            print(f"[生成] {md_file.name}")

        except Exception as e:

            errors.append(f"{md_file}: {e}")

            print(
                f"[エラー] {md_file.name}: {e}"
            )



def build_index():

    posts.sort(
        key=lambda p: p["date"],
        reverse=True
    )

    latest_html = ""

    if posts:

        p = posts[0]

        formatted_date = format_date_only(p["date"])
        published_txt = f"投稿日: {formatted_date}" if formatted_date else ""

        title_link = f'<a href="{p["slug"]}.html">{p["title"]}</a>'
        summary_html = (
            f'<p>{escape(p["summary"])}</p>'
            if p["summary"]
            else ""
        )

        latest_html = render(
            POST_TEMPLATE,
            title=title_link,
            published_date=published_txt,
            modified_date="",
            content=summary_html,
            latest_label="最新記事",
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

    page = render(
        BASE_TEMPLATE,
        page_title=SITE_NAME,
        site_name=SITE_NAME,
        content=index_content,
        description=escape(SITE_DESCRIPTION, quote=True),
        page_url=f"{SITE_URL}/",
        og_type="website",
    )

    write_file(
        OUTPUT_DIR / "index.html",
        page
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


def main():
    clean()
    copy_assets()
    build_posts()
    build_pages()
    build_index()

    print()
    print("--------------------------------")
    print("ビルド結果")
    print("--------------------------------")
    print(f"記事数: {len(posts)}")
    print(f"エラー: {len(errors)}")
    print("--------------------------------")

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
