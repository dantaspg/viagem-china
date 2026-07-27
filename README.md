# viagem-china-site

Publishes the `viagem-china` subtree of the Obsidian vault as a
password-protected static site on GitHub Pages.

- **Site**: https://dantaspg.github.io/viagem-china/ (staticrypt password prompt)
- **Source of truth**: the vault at `~/local/obsidian/sysroot/nodes/` — never edit content here.
- **This repo contains no content.** Exported markdown and built HTML live in
  `build/` (gitignored); only AES-encrypted pages are pushed to `gh-pages`.

## Usage

```sh
make publish   # export from vault → mkdocs build → encrypt → push to gh-pages
make serve     # local preview (unencrypted) at http://localhost:8000
```

Password lives in `.env` (gitignored): `STATICRYPT_PASSWORD=...`

## Pipeline

1. `export.py` walks the vault's `parent:` frontmatter chains from
   `viagem-china.md`, exports that subtree, rewrites `[[wikilinks]]` to
   relative links, copies attachments under content-hashed names, and
   generates `build/mkdocs.yml` with a nav mirroring the note tree.
2. `mkdocs build` (Material theme, search disabled — its plaintext index
   would defeat the encryption).
3. `staticrypt` encrypts every HTML page with the shared password.
4. `ghp-import` force-pushes the encrypted output to `gh-pages`.

Note: binary assets (images/PDFs) are not encrypted — they are served under
content-hashed (unguessable) filenames instead.
