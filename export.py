"""Export the viagem-china subtree from the Obsidian vault into build/docs.

Selection: the root note plus every note whose frontmatter parent-chain
reaches it. Wikilinks between exported notes become relative md links;
links to anything else become plain text. Embedded/linked attachments are
copied under content-hashed names (unguessable URLs, since binary assets
are not encrypted by staticrypt).

Idempotent: build/ is wiped and regenerated on every run.
"""

import hashlib
import re
import shutil
import unicodedata
from pathlib import Path

VAULT = Path("/Users/dantas/local/obsidian/sysroot")
NODES = VAULT / "nodes"
FILES = VAULT / "files"
ROOT_NOTE = "viagem-china"

BUILD = Path(__file__).parent / "build"
DOCS = BUILD / "docs"
ASSETS = DOCS / "assets"

SITE_NAME = "Viagem Taiwan–China 2026"

WIKILINK = re.compile(r"(!?)\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
PARENT = re.compile(r"^parent:\s*'?\[\[([^\]]+)\]\]'?", re.MULTILINE)

IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "note"


def load_notes() -> dict[str, Path]:
    return {nfc(p.stem): p for p in NODES.glob("*.md")}


def parent_of(path: Path) -> str | None:
    m = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if not m:
        return None
    pm = PARENT.search(m.group(1))
    return nfc(pm.group(1)) if pm else None


def select_subtree(notes: dict[str, Path]) -> list[str]:
    parents = {name: parent_of(path) for name, path in notes.items()}
    included = []
    for name in notes:
        chain, cur = set(), name
        while cur is not None and cur not in chain:
            if cur == ROOT_NOTE:
                included.append(name)
                break
            chain.add(cur)
            cur = parents.get(cur)
    return sorted(included)


def find_asset(name: str) -> Path | None:
    for candidate in (FILES / name, NODES / name):
        if candidate.exists():
            return candidate
    hits = [p for p in VAULT.rglob(name) if ".trash" not in p.parts]
    return hits[0] if hits else None


def copy_asset(src: Path) -> str:
    digest = hashlib.sha256(src.read_bytes()).hexdigest()[:16]
    dest = ASSETS / f"{digest}{src.suffix.lower()}"
    if not dest.exists():
        shutil.copy2(src, dest)
    return f"assets/{dest.name}"


def rewrite(body: str, slugs: dict[str, str]) -> str:
    def sub(m: re.Match) -> str:
        embed, target, label = m.group(1), nfc(m.group(2).strip()), m.group(3)
        label = label or target
        if target in slugs:
            return f"[{label}]({slugs[target]}.md)"
        if "." in target:  # attachment
            src = find_asset(target)
            if src is None:
                return label
            rel = copy_asset(src)
            if embed and src.suffix.lower() in IMG_EXTS:
                return f"![{label}]({rel})"
            return f"[{label}]({rel})"
        return label

    return WIKILINK.sub(sub, body)


def preserve_tree_lines(body: str) -> str:
    # The ascii-tree block collapses into one paragraph without hard breaks.
    return "\n".join(
        line + "  " if line.startswith("┣") else line for line in body.splitlines()
    )


def nav_tree(name: str, children: dict[str, list[str]], slugs: dict[str, str]):
    kids = sorted(children.get(name, []), key=str.lower)
    page = "index.md" if name == ROOT_NOTE else f"{slugs[name]}.md"
    if not kids:
        return {name: page}
    entries = [{name: page}] + [nav_tree(k, children, slugs) for k in kids]
    return {name: entries}


def write_mkdocs_yml(nav) -> None:
    import yaml

    config = {
        "site_name": SITE_NAME,
        "docs_dir": "docs",
        "site_dir": "site",
        "theme": {
            "name": "material",
            "palette": [
                {
                    "media": "(prefers-color-scheme: light)",
                    "scheme": "default",
                    "primary": "red",
                    "toggle": {"icon": "material/brightness-7", "name": "Dark mode"},
                },
                {
                    "media": "(prefers-color-scheme: dark)",
                    "scheme": "slate",
                    "primary": "red",
                    "toggle": {"icon": "material/brightness-4", "name": "Light mode"},
                },
            ],
            "features": ["navigation.expand", "navigation.top", "toc.integrate"],
        },
        "plugins": [],  # no search: its index would leak plaintext content
        "markdown_extensions": ["tables", "admonition", "attr_list"],
        "use_directory_urls": False,
        "nav": nav,
    }
    (BUILD / "mkdocs.yml").write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def main() -> None:
    shutil.rmtree(BUILD, ignore_errors=True)
    ASSETS.mkdir(parents=True)

    notes = load_notes()
    included = select_subtree(notes)
    slugs = {name: slugify(name) for name in included}

    children: dict[str, list[str]] = {}
    for name in included:
        if name != ROOT_NOTE:
            children.setdefault(parent_of(notes[name]) or ROOT_NOTE, []).append(name)

    for name in included:
        body = FRONTMATTER.sub("", notes[name].read_text(encoding="utf-8"))
        body = preserve_tree_lines(rewrite(body, slugs))
        if not body.lstrip().startswith("# "):
            body = f"# {name}\n\n{body}"
        out = "index" if name == ROOT_NOTE else slugs[name]
        (DOCS / f"{out}.md").write_text(body, encoding="utf-8")

    root_nav = nav_tree(ROOT_NOTE, children, slugs)
    nav = [{"Home": "index.md"}] + root_nav[ROOT_NOTE][1:]
    write_mkdocs_yml(nav)
    print(f"exported {len(included)} notes, {len(list(ASSETS.iterdir()))} assets")


if __name__ == "__main__":
    main()
