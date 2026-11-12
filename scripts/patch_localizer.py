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
script.write_text(text, encoding="utf-8")
