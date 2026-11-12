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
    '    "fonts.googleapis.com",\n    "fonts.gstatic.com",\n)',
    '    "fonts.googleapis.com",\n    "fonts.gstatic.com",\n    "rawcdn.githack.com",\n    "bbcdn.githack.com",\n    "raw.githubusercontent.com",\n)',
)
text = text.replace(
    '    "kizi", "sdk.crazygames.com", "githack.com", "raw.githubusercontent.com",\n    "github.com", "docs.google.com",',
    '    "kizi", "sdk.crazygames.com",\n    "github.com", "docs.google.com",',
)
text = text.replace(
    '    parts = urllib.parse.urlsplit(url)\n    path = urllib.parse.unquote(parts.path)\n    q = urllib.parse.parse_qs(parts.query)',
    '    parts = urllib.parse.urlsplit(url)\n    host = parts.netloc.lower()\n    path = urllib.parse.unquote(parts.path)\n    if host.endswith("githack.com") or host == "raw.githubusercontent.com":\n        bits = path.strip("/").split("/", 3)\n        if len(bits) == 4:\n            owner, repo, ref, subdir = bits\n            return mirror_github(owner, repo, ref, subdir.rstrip("/"), game)\n        return False\n    q = urllib.parse.parse_qs(parts.query)',
)
text = text.replace('text = text.replace(emu, "../_shared/emu/")', 'text = text.replace(emu, rel_for(SHARED / "emu", page) + "/")')
text = text.replace(
    '    m = re.match(r"https://cdn\\.jsdelivr\\.net/gh/([^/]+)/([^@]+)@([^/]+)/?", emu_url)',
    '    m = re.match(r"https://cdn\\.jsdelivr\\.net/gh/([^/]+)/([^@]+)@([^/]+)(?:/(.*?))?/?$", emu_url)',
)
text = text.replace('    owner, repo, ref = m.groups()', '    owner, repo, ref, subdir = m.groups()\n    base = None')
text = text.replace('        engine.mkdir(parents=True, exist_ok=True)', '        base = tmp / subdir if subdir else tmp\n        engine.mkdir(parents=True, exist_ok=True)')
text = text.replace('            src = tmp / name', '            src = base / name')
text = text.replace('        core_dir = tmp / "cores"', '        core_dir = base / "cores"')
text = text.replace(
    '            log.append(f"EMU MISS {owner}/{repo}@{ref}")\n            return False',
    '            log.append(f"EMU MISS {owner}/{repo}@{ref}/{subdir or \'\'}")\n            shutil.rmtree(engine, ignore_errors=True)\n            return False',
)
text = text.replace(
    '        log.append(f"EMU OK {owner}/{repo}@{ref} cores=',
    '        if not (engine / "loader.js").exists():\n'
    '            log.append(f"EMU MISS {owner}/{repo}@{ref}")\n'
    '            return False\n'
    '        log.append(f"EMU OK {owner}/{repo}@{ref} cores=',
)
script.write_text(text, encoding="utf-8")
