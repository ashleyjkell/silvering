#!/usr/bin/env python3
"""Build a fictional-company training pack from <workspace>/spec/.

Usage:
    python build_pack.py <workspace> [--no-zip]
    python build_pack.py --init <workspace> "<Fictional Name>"   # scaffold an empty workspace
    python build_pack.py --check                                # verify dependencies
    python build_pack.py --init-deploy <workspace>              # add a GitHub Actions -> Pages workflow
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPS = {"docx": "python-docx", "pptx": "python-pptx", "openpyxl": "openpyxl", "reportlab": "reportlab",
        "faker": "faker", "PIL": "pillow"}


def check_deps(install=True):
    missing = []
    for mod, pkg in DEPS.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing and install:
        print("Installing:", " ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing])
    return missing


def init(ws, name):
    ws = Path(ws)
    for d in ("spec/content", "spec/facts", "spec/scenarios", "research"):
        (ws / d).mkdir(parents=True, exist_ok=True)
    print(f"Scaffolded {ws} for {name}. See references/example-spec/ for a complete worked example.")


def init_deploy(ws):
    """Make a workspace a self-building GitHub repo: vendor the builder into tools/ and add a Pages workflow."""
    import shutil
    ws = Path(ws).resolve()
    dest = ws / "tools" / "fictional-company" / "scripts"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(HERE, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    wf = ws / ".github" / "workflows" / "build-and-deploy.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / "fcbuild" / "deploy_workflow.yml", wf)
    import importlib.metadata as md
    pins = []
    for pkg in DEPS.values():
        try:
            pins.append(f"{pkg}=={md.version(pkg)}")
        except md.PackageNotFoundError:
            pins.append(pkg)
    # same library versions as the local build, so CI regenerates identical data if the cache is missing
    (dest.parent / "requirements.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
    gi = ws / ".gitignore"
    lines = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    for l in ("build/", "*.zip", "__pycache__/", "spec/private.json", "research/private/"):  # .cache/ is committed: CI reuses the exact datasets
        if l not in lines:
            lines.append(l)
    gi.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ga = ws / ".gitattributes"  # keep bytes identical so the dataset cache key matches in CI
    if "-text" not in (ga.read_text(encoding="utf-8") if ga.exists() else ""):
        ga.write_text("* -text\n", encoding="utf-8")
    company = json.loads((ws / "spec" / "company.json").read_text(encoding="utf-8"))
    print(f"Deploy set up in {ws}\n  tools/fictional-company/scripts  (vendored builder - re-run --init-deploy to update)\n  {wf.relative_to(ws)}")
    if not company.get("as_of"):
        print("  ! company.json has no as_of: set it, or every CI build will shift 'today'")
    if company.get("real_company"):
        print("  ! company.json contains real_company - move it to spec/private.json (git-ignored) before pushing to a public repo")
    print("Next: commit and push to GitHub, then Settings > Pages > Source = GitHub Actions.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if args[0] == "--check":
        m = check_deps(install=False)
        print("All dependencies present" if not m else f"Missing: {m}")
        sys.exit(1 if m else 0)
    if args[0] == "--init":
        init(args[1], args[2] if len(args) > 2 else "Example Co")
        sys.exit(0)
    if args[0] == "--init-deploy":
        init_deploy(args[1])
        sys.exit(0)
    check_deps()
    sys.path.insert(0, str(HERE))
    from fcbuild.build import build
    build(args[0], make_zip="--no-zip" not in args)
