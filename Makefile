# Publishes the viagem-china vault subtree as an encrypted GitHub Pages site.
# Plaintext content only ever exists locally under build/ (gitignored);
# only staticrypt-encrypted HTML is pushed to gh-pages.

include .env
export STATICRYPT_PASSWORD

publish: encrypt
	uv run ghp-import -n -p -f -m "publish site" build/encrypted
	@echo "→ https://dantaspg.github.io/viagem-china/"

encrypt: build
	rm -rf build/encrypted
	cd build && npx --yes staticrypt site -r -d encrypted --remember 30 --short \
		--template-title "Viagem Taiwan–China" \
		--template-instructions "Senha da viagem"
	@# staticrypt only writes .html files; bring over css/js/images
	rsync -a --ignore-existing build/site/ build/encrypted/site/
	mv build/encrypted/site/* build/encrypted/ 2>/dev/null; rmdir build/encrypted/site || true

build: export
	cd build && uv run mkdocs build

export:
	uv run python export.py

serve: export
	cd build && uv run mkdocs serve

.PHONY: publish encrypt build export serve
