from pathlib import Path

script = Path(__file__).with_name("localize_cdn.py")
text = script.read_text(encoding="utf-8")
old = '''        for item in src.iterdir():
            if item.name in (".git", "index.html"):
                continue
            dst = game / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)'''
new = '''        ignore = shutil.ignore_patterns(".git", ".github", ".DS_Store", "*.html", "*.htm")
        for item in src.iterdir():
            if item.name in (".git", ".github", ".DS_Store") or item.suffix.lower() in (".html", ".htm"):
                continue
            dst = game / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True, ignore=ignore)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)'''
text = text.replace(
    'ROOT = Path(__file__).resolve().parent.parent',
    'ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent',
)
if old in text:
    text = text.replace(old, new)

old_emu = r'''EMU_RE = re.compile(r"https://cdn\.jsdelivr\.net/gh/(?:bubblfan|genizy)/emu@[^/\"'\s<>)]+/")'''
new_emu = r'''EMU_RE = re.compile(r"EJS_pathtodata\s*=\s*[\"'](https://cdn\.jsdelivr\.net/gh/[^\"']+/?)[\"']")'''
text = text.replace(old_emu, new_emu)
text = text.replace("if size > 120 * 1024 * 1024:", "if size > 60 * 1024 * 1024:")
text = text.replace(
    '    ".js", ".mjs", ".css", ".json", ".wasm", ".data", ".bin", ".mem", ".symbols",',
    '    ".js", ".mjs", ".css", ".json", ".wasm", ".data", ".bin", ".mem", ".symbols",\n    ".html", ".htm",',
)
text = text.replace(
    '        log.append(f"EMU OK {owner}/{repo}@{ref} cores=',
    '        if not (engine / "loader.js").exists():\n'
    '            log.append(f"EMU MISS {owner}/{repo}@{ref}")\n'
    '            return False\n'
    '        log.append(f"EMU OK {owner}/{repo}@{ref} cores=',
)
script.write_text(text, encoding="utf-8")
