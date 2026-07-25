#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import / RE-INJECTION de sessions Claude Code exportees.

Pendant de `export_claude_sessions.py` : remet sur CE PC (le PC/compte cible) des sessions
exportees ailleurs, pour les reprendre nativement avec `claude --resume <sessionId>`.
Aucun appel reseau, aucun token consomme : c'est de la copie de fichiers locaux.

Comment Claude Code range une session :

    ~/.claude/projects/<cwd-encode>/<sessionId>.jsonl

ou <cwd-encode> = le chemin de travail (cwd) avec CHAQUE caractere non alphanumerique
remplace par '-'. Exemple verifie :

    C:\\Users\\Utilisateur\\PROJECTS\\3- Wisper\\speak-app-dev
 -> C--Users-Utilisateur-PROJECTS-3--Wisper-speak-app-dev

Donc "reinjecter" = recalculer ce dossier sur le PC cible et y deposer le .jsonl. Le piege :
le nom d'utilisateur / le chemin DIFFERE souvent d'un PC a l'autre (ex Administrateur vs
Utilisateur) -> le dossier encode change -> sans remap, `claude --resume` ne retrouve rien.

Ce script lit le `cwd` d'origine DANS chaque .jsonl, le remappe (--auto-user par defaut +
--remap optionnels), l'encode, et copie le .jsonl au bon endroit. Il ecrit aussi un
REPRISE-IMPORT.md avec les commandes exactes, deja remappees.

La logique vit dans `import_bundle()` (reutilisable par l'app SpeakApp = bouton Reglages).

Usage CLI :
    py tools/import_claude_sessions.py "<dossier-bundle-exporte>"
    py tools/import_claude_sessions.py "<bundle>" --dry-run
    py tools/import_claude_sessions.py "<bundle>" --remap "Utilisateur=Administrateur"
    py tools/import_claude_sessions.py "<bundle>" --remap "C:\\Users\\Flo\\old=D:\\projets" --force
    py tools/import_claude_sessions.py "<bundle>" --projects-dir "<dossier de test>"

Puis sur le PC cible :
    cd "<dossier du projet>"
    claude --resume <sessionId>
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECTS_DIR_DEFAULT = Path(os.path.expanduser("~")) / ".claude" / "projects"


def encode_cwd(cwd: str) -> str:
    """Reproduit l'encodage Claude Code : tout caractere non [a-zA-Z0-9] -> '-'.
    Verifie empiriquement sur ~/.claude/projects (chemins, espaces, worktrees `.claude`).
    NB : PAS de collapse de sequences (`3- Wisper` -> `3--Wisper`, deux tirets)."""
    return re.sub(r"[^a-zA-Z0-9]", "-", cwd)


def read_cwd_from_jsonl(path: Path) -> str | None:
    """Renvoie le 1er `cwd` trouve dans le .jsonl. Tous les events ne le portent pas
    (ex les events `operation`), donc on scanne jusqu'a en trouver un."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(obj, dict) and obj.get("cwd"):
                    return str(obj["cwd"])
    except OSError:
        pass
    return None


def apply_remaps(cwd: str, remaps: list[tuple[str, str]], auto_user: bool,
                 current_user: str) -> str:
    """Applique d'abord les remaps literaux (dans l'ordre), puis le remap auto du
    segment d'utilisateur (\\Users\\X\\, /Users/X/ ou /home/X/) vers l'utilisateur courant."""
    out = cwd
    for old, new in remaps:
        out = out.replace(old, new)
    if auto_user and current_user:
        def _sub(m):
            return m.group(1) + current_user + m.group(3)
        out = re.sub(r"(?i)([\\/](?:Users|home)[\\/])([^\\/]+)([\\/])", _sub, out, count=1)
    return out


def _write_reprise(bundle: Path, by_target: dict, projects_dir: Path, current_user: str):
    rep = [f"# Sessions reinjectees — {datetime.now().strftime('%Y-%m-%d %H:%M')}", "",
           f"> Importees dans `{projects_dir}` sur ce PC (utilisateur `{current_user}`).",
           "> Reprends chaque session **dans le dossier de son projet** :", "",
           "```", 'cd "<dossier du projet>"', "claude --resume <sessionId>", "```", "",
           "> Le projet doit exister a ce chemin sur ce PC (git clone / meme arborescence).",
           "", "---", ""]
    for cwd, items in sorted(by_target.items()):
        rep.append(f"## `{cwd}` — {len(items)} session(s)")
        rep.append("")
        for sid in items:
            rep.append(f'- `cd "{cwd}" ; claude --resume {sid}`')
        rep.append("")
    (bundle / "REPRISE-IMPORT.md").write_text("\n".join(rep), encoding="utf-8")


def import_bundle(bundle, projects_dir=None, remaps=None, auto_user=True,
                  force=False, dry_run=False, write_reprise=True) -> dict:
    """Reinjecte les .jsonl d'un bundle exporte. Reutilisable (CLI + app SpeakApp).

    Retourne un summary :
        {found, injected, copied, skip_exists, no_cwd, projects, current_user,
         by_target: {cwd_remappe: [sessionId, ...]}, reprise_path, errors}
    """
    bundle = Path(bundle)
    projects_dir = Path(projects_dir) if projects_dir else PROJECTS_DIR_DEFAULT
    remaps = remaps or []
    current_user = Path(os.path.expanduser("~")).name

    jsonls = sorted(bundle.rglob("*.jsonl"))
    n_ok = n_skip_exists = n_no_cwd = n_copied = 0
    by_target: dict[str, list[str]] = {}
    errors: list[str] = []

    for jf in jsonls:
        sid = jf.stem
        raw_cwd = read_cwd_from_jsonl(jf)
        if not raw_cwd:
            n_no_cwd += 1
            continue
        target_cwd = apply_remaps(raw_cwd, remaps, auto_user, current_user)
        dst_dir = projects_dir / encode_cwd(target_cwd)
        dst = dst_dir / jf.name
        by_target.setdefault(target_cwd, []).append(sid)
        if dst.exists() and not force:
            n_skip_exists += 1
            continue
        if dry_run:
            n_ok += 1
            continue
        try:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(jf, dst)
            n_copied += 1
            n_ok += 1
        except OSError as e:
            errors.append(f"{jf.name}: {e}")

    reprise_path = None
    if write_reprise and not dry_run and by_target:
        try:
            _write_reprise(bundle, by_target, projects_dir, current_user)
            reprise_path = str(bundle / "REPRISE-IMPORT.md")
        except OSError as e:
            errors.append(f"REPRISE-IMPORT.md: {e}")

    return {
        "found": len(jsonls),
        "injected": n_ok,
        "copied": n_copied,
        "skip_exists": n_skip_exists,
        "no_cwd": n_no_cwd,
        "projects": len(by_target),
        "current_user": current_user,
        "by_target": by_target,
        "reprise_path": reprise_path,
        "errors": errors,
    }


def main():
    # Console Windows en UTF-8 (titres/emoji -> evite UnicodeEncodeError cp1252)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(
        description="Reinjecte des sessions Claude Code exportees (pour `claude --resume`)."
    )
    ap.add_argument("bundle", help="Dossier d'export (contient des .jsonl, typiquement dans jsonl/)")
    ap.add_argument("--projects-dir", default=str(PROJECTS_DIR_DEFAULT),
                    help="Dossier cible (defaut ~/.claude/projects)")
    ap.add_argument("--remap", action="append", default=[],
                    help='Remplacement de chemin "ANCIEN=NOUVEAU" (repetable). Ex "Utilisateur=Administrateur"')
    ap.add_argument("--no-auto-user", action="store_true",
                    help="Desactive le remap automatique du nom d'utilisateur (Users/home)")
    ap.add_argument("--force", action="store_true", help="Ecrase une session deja presente")
    ap.add_argument("--dry-run", action="store_true", help="Montre ce qui serait fait sans rien copier")
    args = ap.parse_args()

    bundle = Path(args.bundle)
    if not bundle.exists():
        print(f"[ERREUR] Bundle introuvable : {bundle}")
        sys.exit(1)

    # Support .zip : extraire vers un dossier temporaire (REPRISE recopie a cote du .zip)
    _zip_tmp = None
    _reprise_dest = None
    if bundle.is_file() and bundle.suffix.lower() == ".zip":
        import tempfile
        import zipfile
        _reprise_dest = bundle.parent
        _zip_tmp = Path(tempfile.mkdtemp(prefix="import-zip-"))
        with zipfile.ZipFile(bundle, "r") as zf:
            zf.extractall(_zip_tmp)
        bundle = _zip_tmp

    remaps: list[tuple[str, str]] = []
    for r in args.remap:
        if "=" not in r:
            print(f"[ERREUR] --remap doit etre 'ANCIEN=NOUVEAU' (recu: {r})")
            sys.exit(1)
        old, new = r.split("=", 1)
        remaps.append((old, new))

    if not list(bundle.rglob("*.jsonl")):
        print(f"[ERREUR] Aucun .jsonl trouve sous {bundle}")
        sys.exit(1)

    s = import_bundle(bundle, projects_dir=args.projects_dir, remaps=remaps,
                      auto_user=not args.no_auto_user, force=args.force, dry_run=args.dry_run)

    for e in s["errors"]:
        print(f"[skip] {e}")

    print("=" * 60)
    head = "[DRY-RUN] " if args.dry_run else ""
    print(f"{head}IMPORT sessions -> {args.projects_dir}")
    print(f"  .jsonl trouves        : {s['found']}")
    print(f"  a (re)injecter        : {s['injected']}")
    if not args.dry_run:
        print(f"  copies                : {s['copied']}")
    print(f"  deja presents (skip)  : {s['skip_exists']}  (--force pour ecraser)")
    print(f"  sans cwd (ignores)    : {s['no_cwd']}")
    print(f"  projets cibles        : {s['projects']}")
    if not args.no_auto_user:
        print(f"  auto-user             : -> '{s['current_user']}'")
    if remaps:
        print(f"  remaps                : {remaps}")
    if s["reprise_path"]:
        print(f"  reprise               : {s['reprise_path']}")
    print("=" * 60)
    if args.dry_run and s["by_target"]:
        print("\nApercu des dossiers cibles :")
        for cwd, items in list(sorted(s["by_target"].items()))[:20]:
            print(f"  {len(items):3d}  {encode_cwd(cwd)}")

    # Cleanup extraction .zip (+ recopie REPRISE-IMPORT.md a cote du .zip d'origine)
    if _zip_tmp is not None:
        if s.get("reprise_path") and not args.dry_run:
            try:
                dest = _reprise_dest / "REPRISE-IMPORT.md"
                shutil.copy2(s["reprise_path"], dest)
                print(f"  reprise (zip)         : {dest}")
            except OSError:
                pass
        shutil.rmtree(_zip_tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
