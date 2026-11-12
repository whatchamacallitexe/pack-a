#!/usr/bin/env python3
"""Copy static CDN dependencies into a pack repo and rewrite game pages to use them.

Handles the forms used by the UGS pack pages:
  * <base href="https://cdn.jsdelivr.net/gh/owner/repo@ref/path/">
  * script/link/img/embed/param URLs and inline JS strings
  * jsDelivr, cdnjs, unpkg, Google Fonts and jQuery CDN files

Ad/tracking/API endpoints are deliberately left alone: they are live services,
not files that can be copied into the repo.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "_shared"
CDN_HOSTS = (
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "ajax.googleapis.com",
    "code.jquery.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)
STATIC_EXTS = {
    ".js", ".mjs", ".css", ".json", ".wasm", ".data", ".bin", ".mem", ".symbols",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".bmp",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp3", ".ogg", ".wav", ".m4a", ".mp4", ".webm", ".ogv",
    ".swf", ".unity3d", ".atlas", ".xml", ".txt", ".csv",
    ".zip", ".7z", ".rar", ".gz", ".tar",
    ".nes", ".sfc", ".smc", ".gb", ".gbc", ".gba", ".nds", ".n64", ".z64", ".v64",
    ".md", ".gen", ".sms", ".gg", ".pce", ".ngp", ".ngc", ".ws", ".wsc",
    ".chd", ".iso", ".cue", ".img", ".rom",
}
MAX_BYTES = 60 * 1024 * 1024
BAD_SUBSTRINGS = (
    "googleads", "doubleclick", "googletagmanager", "google-analytics",
    "gamedistribution", "gamemonetize", "gamemonkey", "gamedock", "poki",
    "crazygames", "kongregate", "newgrounds", "admeen", "headerlift",
    "improvedigital", "yandex", "eponesh", "softgames", "minijuegos",
    "kizi", "sdk.crazygames.com", "githack.com", "raw.githubusercontent.com",
    "github.com", "docs.google.com",
)
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
BASE_RE = re.compile(r"<base\s+[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>", re.I)
CSS_URL_RE = re.compile(r"url\(\s*([\"']?)(https?://[^)\"']+)\1\s*\)", re.I)
CSS_IMPORT_RE = re.compile(r"@import\s+(?:url\(\s*)?[\"']?(https?://[^)\"';]+)", re.I)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
EMU_RE = re.compile(r"https://cdn\.jsdelivr\.net/gh/(?:bubblfan|genizy)/emu@[^/\"'\s<>)]+/")
CORE_RE = re.compile(r"EJS_core\s*=\s*[\"']([^\"']+)")
CORE_PREFIXES = {
    "nes": ["fceumm"], "snes": ["snes9x"], "n64": ["mupen64plus_next"],
    "gb": ["gambatte"], "gbc": ["gambatte"], "gba": ["mgba"],
    "nds": ["melonds"], "psx": ["mednafen_psx"], "segaMD": ["genesis_plus_gx"],
    "segaMS": ["smsplus"], "segaGG": ["genesis_plus_gx"], "segaCD": ["genesis_plus_gx"],
    "segaSaturn": ["mednafen_saturn"], "pce": ["mednafen_pce"], "atari2600": ["stella2014"],
    "arcade": ["fbneo"], "mame2003": ["mame2003"], "vb": ["beetle_vb"],
}

downloaded: dict[str, Path] = {}
shared_counts: dict[str, int] = {}
log: list[str] = []


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def is_cdn(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower()
    return any(host == h or host.endswith("." + h) for h in CDN_HOSTS)


def is_bad(url: str) -> bool:
    low = url.lower()
    return any(b in low for b in BAD_SUBSTRINGS)


def ext_of(url: str) -> str:
    return Path(urllib.parse.urlsplit(url).path).suffix.lower()


def looks_static(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower()
    return ext_of(url) in STATIC_EXTS or host == "fonts.googleapis.com"


def safe_name(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parts.path)
    name = os.path.basename(path.rstrip("/")) or "index"
    if parts.netloc.lower() == "fonts.googleapis.com":
        return "fonts-" + hashlib.sha1(url.encode()).hexdigest()[:10] + ".css"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if len(name) > 90:
        stem, dot, ext = name.rpartition(".")
        name = (stem[:70] + "." + ext) if dot else name[:90]
    return name


def digest(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:12]


def fetch(url: str, dest: Path) -> bool:
    """Download one URL. Returns False for oversized/failed downloads."""
    if dest.exists() and dest.stat().st_size:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    cmd = [
        "curl", "-L", "--fail", "--silent", "--show-error", "--retry", "3",
        "--retry-delay", "2", "--connect-timeout", "20", "--max-time", "240",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "-o", str(tmp), url,
    ]
    try:
        run(cmd)
    except subprocess.CalledProcessError as e:
        tmp.unlink(missing_ok=True)
        log.append(f"FAILED {url}: {str(e.stdout)[-300:]}")
        return False
    size = tmp.stat().st_size
    if size > MAX_BYTES:
        tmp.unlink(missing_ok=True)
        log.append(f"SKIP size {size / 1048576:.1f}MB {url}")
        return False
    tmp.replace(dest)
    return True


def rel_for(path: Path, page: Path) -> str:
    rel = os.path.relpath(path, page.parent).replace(os.sep, "/")
    return urllib.parse.quote(rel, safe="/._~-")


def target_for(url: str, game: Path) -> Path:
    name = safe_name(url)
    if shared_counts.get(url, 0) > 1:
        return SHARED / f"{digest(url)}-{name}"
    return game / "assets" / "cdn" / f"{digest(url)[:8]}-{name}"


def relink_css(css: Path) -> None:
    text = css.read_text("utf-8", "ignore")

    def repl(m: re.Match) -> str:
        url = m.group(2)
        if not (is_cdn(url) and looks_static(url)) or is_bad(url):
            return m.group(0)
        dest = css.parent / safe_name(url)
        if not fetch(url, dest):
            return m.group(0)
        rel = urllib.parse.quote(os.path.relpath(dest, css.parent).replace(os.sep, "/"), safe="/._~-")
        return f"url({m.group(1)}{rel}{m.group(1)})"

    new = CSS_URL_RE.sub(repl, text)
    if new != text:
        css.write_text(new, encoding="utf-8")
        text = new

    def imp(m: re.Match) -> str:
        url = m.group(1)
        if not (is_cdn(url) and (ext_of(url) == ".css" or "fonts.googleapis.com" in url)) or is_bad(url):
            return m.group(0)
        dest = css.parent / safe_name(url)
        if not fetch(url, dest):
            return m.group(0)
        relink_css(dest)
        return f'@import url("{urllib.parse.quote(dest.name)}")'

    changed = CSS_IMPORT_RE.sub(imp, text)
    if changed != text:
        css.write_text(changed, encoding="utf-8")


def mirror_base(url: str, game: Path) -> bool:
    """Copy a jsDelivr directory (gh/npm) into the game folder."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parts.path)
    q = urllib.parse.parse_qs(parts.query)
    version = q.get("v", [None])[0]
    prefix = "/gh/" if path.startswith("/gh/") else "/npm/" if path.startswith("/npm/") else None
    if not prefix:
        return False
    rest = path[len(prefix):]
    if prefix == "/npm/":
        at = rest.rfind("@")
        pkg = rest[:at] if at > 0 else rest
        ver = rest[at + 1:] if at > 0 else (version or "latest")
        return mirror_npm(pkg, ver, game)
    owner, repo_rest = rest.split("/", 1)
    repo, _, remainder = repo_rest.partition("/")
    ref = None
    if "@" in repo:
        repo, ref = repo.rsplit("@", 1)
    subdir = remainder.rstrip("/")
    if not ref:
        ref = version or "HEAD"
    return mirror_github(owner, repo, ref, subdir, game)


def mirror_github(owner: str, repo: str, ref: str, subdir: str, game: Path) -> bool:
    key = hashlib.sha1(f"{owner}/{repo}/{ref}/{subdir}".encode()).hexdigest()[:16]
    tmp = Path(tempfile.gettempdir()) / "cdn-upstreams" / key
    try:
        if not (tmp / ".git").exists():
            tmp.parent.mkdir(parents=True, exist_ok=True)
            run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                 f"https://github.com/{owner}/{repo}.git", str(tmp)])
        fetched = run(["git", "-C", str(tmp), "fetch", "--depth", "1", "origin", ref], check=False)
        target = "FETCH_HEAD" if fetched.returncode == 0 else "HEAD"
        run(["git", "-C", str(tmp), "checkout", "--force", target])
        if subdir:
            run(["git", "-C", str(tmp), "sparse-checkout", "set", subdir])
            src = tmp / subdir
        else:
            run(["git", "-C", str(tmp), "sparse-checkout", "disable"], check=False)
            src = tmp
        if not src.is_dir():
            log.append(f"BASE MISS {owner}/{repo}@{ref}/{subdir}")
            return False
        size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
        if size > 120 * 1024 * 1024:
            log.append(f"BASE SKIP {size / 1048576:.1f}MB {owner}/{repo}@{ref}/{subdir}")
            return False
        game.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name in (".git", "index.html"):
                continue
            dst = game / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
        log.append(f"BASE OK {owner}/{repo}@{ref}/{subdir or '.'} -> {game.name}")
        return True
    except subprocess.CalledProcessError as e:
        log.append(f"BASE FAIL {owner}/{repo}@{ref}/{subdir}: {str(e.stdout)[-300:]}")
        return False


def mirror_npm(pkg: str, version: str, game: Path) -> bool:
    url = f"https://registry.npmjs.org/{pkg}/-/{pkg.split('/')[-1]}-{version}.tgz"
    tmp = Path(tempfile.gettempdir()) / "cdn-upstreams" / (digest(url) + ".tgz")
    if not fetch(url, tmp):
        log.append(f"NPM MISS {pkg}@{version}")
        return False
    try:
        with tarfile.open(tmp) as tf:
            for member in tf.getmembers():
                if not member.isfile() or not member.name.startswith("package/"):
                    continue
                rel = member.name[len("package/"):]
                if not rel or rel == "index.html":
                    continue
                out = game / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                if src:
                    out.write_bytes(src.read())
        log.append(f"NPM OK {pkg}@{version} -> {game.name}")
        return True
    except Exception as e:
        log.append(f"NPM FAIL {pkg}@{version}: {e}")
        return False


def prepare_emu(emu_url: str, pages: list[Path]) -> bool:
    """Copy the EmulatorJS runtime once per pack, with only the needed cores."""
    engine = SHARED / "emu"
    if (engine / "loader.js").exists():
        return True
    m = re.match(r"https://cdn\.jsdelivr\.net/gh/([^/]+)/([^@]+)@([^/]+)/?", emu_url)
    if not m:
        return False
    owner, repo, ref = m.groups()
    tmp = Path(tempfile.gettempdir()) / "cdn-upstreams" / f"emu-{digest(emu_url)}"
    try:
        if not (tmp / ".git").exists():
            run(["git", "clone", "--depth", "1",
                 f"https://github.com/{owner}/{repo}.git", str(tmp)])
        if ref not in ("master", "main", "HEAD"):
            run(["git", "-C", str(tmp), "fetch", "--depth", "1", "origin", ref], check=False)
            run(["git", "-C", str(tmp), "checkout", "--force", "FETCH_HEAD"], check=False)
        engine.mkdir(parents=True, exist_ok=True)
        for name in ("loader.js", "emulator.min.js", "emulator.min.css", "version.json"):
            src = tmp / name
            if src.exists():
                shutil.copy2(src, engine / name)
        for name in ("src", "compression", "localization"):
            src = tmp / name
            if src.is_dir():
                shutil.copytree(src, engine / name, dirs_exist_ok=True)
        cores = set()
        for page in pages:
            for core in CORE_RE.findall(page.read_text("utf-8", "ignore")):
                cores.update(CORE_PREFIXES.get(core, []))
        core_dir = tmp / "cores"
        if core_dir.is_dir():
            (engine / "cores").mkdir(exist_ok=True)
            for core in sorted(cores) or ["mgba"]:
                for f in core_dir.glob(core + "*"):
                    if f.is_file():
                        shutil.copy2(f, engine / "cores" / f.name)
            reports = core_dir / "reports"
            if reports.is_dir():
                shutil.copytree(reports, engine / "cores" / "reports", dirs_exist_ok=True)
        log.append(f"EMU OK {owner}/{repo}@{ref} cores={','.join(sorted(cores)) or 'mgba'}")
        return True
    except subprocess.CalledProcessError as e:
        log.append(f"EMU FAIL {owner}/{repo}@{ref}: {str(e.stdout)[-300:]}")
        return False


def html_files() -> list[Path]:
    return sorted(
        p for p in ROOT.glob("**/*.html")
        if "_shared" not in p.parts and ".git" not in p.parts
    )


def process_page(page: Path) -> None:
    game = ROOT / page.relative_to(ROOT).parts[0]
    text = page.read_text("utf-8", "ignore")
    comments = [(m.start(), m.end()) for m in COMMENT_RE.finditer(text)]

    def in_comment(pos: int) -> bool:
        return any(a <= pos < b for a, b in comments)

    # EmulatorJS: share one engine and make every EJS_pathtodata/loader URL local.
    for emu in set(EMU_RE.findall(text)):
        if prepare_emu(emu, html_files()):
            text = text.replace(emu, "../_shared/emu/")
            page.write_text(text, encoding="utf-8")

    base_match = BASE_RE.search(text)
    if base_match:
        base_url = base_match.group(1)
        if base_url.startswith("//"):
            base_url = "https:" + base_url
        if is_cdn(base_url) and ("cdn.jsdelivr.net/gh/" in base_url or "cdn.jsdelivr.net/npm/" in base_url):
            if mirror_base(base_url, game):
                base_rel = os.path.relpath(game, page.parent).replace(os.sep, "/") + "/"
                text = text[:base_match.start(1)] + base_rel + text[base_match.end(1):]
                # Also rewrite JS variables such as modernclient's BASE_URL.
                text = text.replace(base_url, base_rel)
                page.write_text(text, encoding="utf-8")
                log.append(f"BASE REWRITE {page.parent.name}")

    found: dict[str, list[tuple[int, int]]] = {}
    for m in URL_RE.finditer(text):
        if in_comment(m.start()):
            continue
        url = m.group(0).rstrip(".,;:")
        if not is_cdn(url) or is_bad(url) or not looks_static(url):
            continue
        found.setdefault(url, []).append((m.start(), m.end()))

    for url, spans in found.items():
        dest = target_for(url, game)
        if not fetch(url, dest):
            continue
        downloaded[url] = dest
        rel = rel_for(dest, page)
        text = text.replace(url, rel)
        log.append(f"FILE {page.parent.name}: {url} -> {rel}")
    page.write_text(text, encoding="utf-8")

    for css in game.rglob("*.css"):
        relink_css(css)


def main() -> int:
    pages = html_files()
    if not pages:
        print("No game pages found")
        return 1
    for page in pages:
        text = page.read_text("utf-8", "ignore")
        for m in URL_RE.finditer(text):
            url = m.group(0).rstrip(".,;:")
            if is_cdn(url) and not is_bad(url) and looks_static(url):
                shared_counts[url] = shared_counts.get(url, 0) + 1
    for page in pages:
        process_page(page)
    for css in SHARED.glob("*.css"):
        relink_css(css)
    (ROOT / "cdn-localize-report.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"Processed {len(pages)} pages, {len(downloaded)} unique files")
    print(f"Report: cdn-localize-report.txt ({len(log)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
