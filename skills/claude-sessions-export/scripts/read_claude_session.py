# -*- coding: utf-8 -*-
"""
Lire une session Claude Code depuis un bundle/zip exporte — Mode B « Claude lit et reprend ».

But : re-hydrater le contexte d'une session sur un AUTRE PC SANS reinjection native.
Claude (depuis l'autre PC) lit le transcript et continue le travail. Pas besoin que la
session "pop" dans la sidebar : c'est Claude qui porte la memoire.

- Sans requete  -> LISTE les sessions du bundle (titre + id court + projet + volume).
- Avec requete  -> imprime le TRANSCRIPT complet de la session qui matche (id prefixe OU
  sous-chaine du titre), pret a etre lu par Claude pour reprendre le fil.

Accepte un dossier bundle, un .zip (extrait en temporaire), OU un .jsonl LOCAL
direct (~/.claude/projects/<cwd-encode>/<id>.jsonl -> imprime ce transcript, sans
bundle ni zip : c'est le chemin canonique du chip Mode B, cf import § capture d'ecran).

Usage :
    py tools/read_claude_session.py "<bundle-ou-zip>"                 # liste
    py tools/read_claude_session.py "<bundle-ou-zip>" "LGM-CHROME"    # par titre
    py tools/read_claude_session.py "<bundle-ou-zip>" 7fd1f354        # par id
    py tools/read_claude_session.py "<...>/<id>.jsonl"                # .jsonl local direct
"""
from __future__ import annotations
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_claude_sessions import parse_session, parse_session_full, fmt_date, short


def _resolve_bundle(p: str):
    """Renvoie (dossier_bundle, tmp_a_nettoyer_ou_None). Gere .zip (extraction temp)."""
    path = Path(p)
    if path.is_file() and path.suffix.lower() == ".zip":
        tmp = Path(tempfile.mkdtemp(prefix="read-zip-"))
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(tmp)
        return tmp, tmp
    return path, None


def _load_sidebar_titles(bundle: Path) -> dict:
    """Lit INDEX-SIDEBAR.md / INDEX-ACTIVE.md du bundle pour mapper id8 -> TITRE EXACT.
    Detecte la colonne 'Titre' et 'Session' depuis l'entete : les 2 index ont des layouts
    differents (SIDEBAR = Titre en 1re colonne ; ACTIVE = 'Derniere activite' en 1re, Titre en 2e)."""
    titles: dict[str, str] = {}
    for name in ("INDEX-SIDEBAR.md", "INDEX-ACTIVE.md"):
        f = bundle / name
        if not f.exists():
            continue
        titre_idx, id_idx, header_seen = 0, -1, False
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("|"):
                continue
            if set(line.strip()) <= set("|-: "):   # ligne separatrice |---|
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            low = [c.lower() for c in cells]
            if not header_seen and any("titre" in c for c in low):
                titre_idx = next((i for i, c in enumerate(low) if "titre" in c), 0)
                id_idx = next((i for i, c in enumerate(low) if "session" in c), -1)
                header_seen = True
                continue
            if max(titre_idx, id_idx if id_idx >= 0 else 0) >= len(cells):
                continue
            title = cells[titre_idx]
            id8 = cells[id_idx].strip("` ")
            if (title and id8 and "---" not in title
                    and id8.lower() not in ("session cli (= jsonl)", "session", "")
                    and title.lower() not in ("titre (sidebar)", "titre", "derniere activite")):
                titles[id8] = title
    return titles


def _md_rows(bundle: Path):
    """Bundle md-only : liste (titre, id8, fichier_md) depuis md/. Nom = <date>_<titre>_<id8>.md."""
    md_dir = bundle / "md"
    files = sorted(md_dir.rglob("*.md")) if md_dir.exists() else []
    out = []
    for mf in files:
        stem = mf.stem
        first, last = stem.find("_"), stem.rfind("_")
        id8 = stem[last + 1:] if last != -1 else stem
        title = stem[first + 1:last].replace("-", " ") if last > first >= 0 else stem
        out.append((title or stem, id8, mf))
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    if len(sys.argv) < 2:
        print("usage: read_claude_session.py <bundle|zip|.jsonl> [titre|id]")
        sys.exit(1)

    # Cas direct : un .jsonl LOCAL (chip Mode B pointe le fichier de session sur le
    # disque, ~/.claude/projects/<cwd-encode>/<id>.jsonl). Pas de bundle a scanner,
    # pas de zip a batir -> c'est le chemin canonique de la § capture d'ecran (import).
    src_arg = Path(sys.argv[1])
    if src_arg.is_file() and src_arg.suffix.lower() == ".jsonl":
        info = parse_session(src_arg)
        title = info.get("ai_title") or info.get("first_user_msg") or src_arg.stem
        print(f"# {title}")
        print(f"- Session : {src_arg.stem}")
        print(f"- Projet  : {info.get('cwd')}")
        print(f"- Volume  : {info['n_user']} user / {info['n_assistant']} assistant")
        print("\n---\n")
        for role, text, ts in parse_session_full(src_arg):
            who = "FLORENT" if role == "user" else "CLAUDE"
            print(f"### {who}  [{fmt_date(ts)}]\n{text}\n")
        return

    bundle, tmp = _resolve_bundle(sys.argv[1])
    if not bundle.exists():
        print(f"[ERREUR] introuvable : {bundle}")
        sys.exit(1)
    query = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        sb_titles = _load_sidebar_titles(bundle)
        jsonls = sorted(bundle.rglob("*.jsonl"))

        if not jsonls:
            # Bundle md-only (leger, sans jsonl/screenshots) -> lire les transcripts md directement
            md_rows = [(sb_titles.get(id8) or title, id8, mf)
                       for (title, id8, mf) in _md_rows(bundle)]
            if not query:
                print(f"{len(md_rows)} sessions (md-only) dans le bundle :\n")
                for title, id8, mf in md_rows:
                    print(f"  [{id8}] {title[:68]}")
                print("\n-> relance avec un titre ou un id pour lire le transcript complet.")
                return
            q = query.lower()
            match = [r for r in md_rows if r[1].startswith(query) or q in r[0].lower()]
            if not match:
                print(f"Aucune session pour '{query}'. Lance sans argument pour voir la liste.")
                sys.exit(1)
            if len(match) > 1:
                print(f"{len(match)} sessions matchent '{query}' — precise :")
                for title, id8, mf in match:
                    print(f"  [{id8}] {title[:68]}")
                return
            print(match[0][2].read_text(encoding="utf-8", errors="replace"))
            return

        rows = []
        for jf in jsonls:
            info = parse_session(jf)
            title = (sb_titles.get(short(jf.stem))
                     or info["ai_title"] or info["first_user_msg"] or "(sans titre)")
            rows.append((title, jf.stem, jf, info))

        if not query:
            print(f"{len(rows)} sessions dans le bundle :\n")
            for title, sid, jf, info in rows:
                proj = (info.get("cwd") or "").rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
                print(f"  [{short(sid)}] {title[:68]}  ({info['n_user']}u/{info['n_assistant']}a)"
                      + (f"  · {proj}" if proj else ""))
            print("\n-> relance avec un titre ou un id pour lire le transcript complet.")
            return

        q = query.lower()
        match = [r for r in rows if r[1].startswith(query) or q in r[0].lower()]
        if not match:
            print(f"Aucune session pour '{query}'. Lance sans argument pour voir la liste.")
            sys.exit(1)
        if len(match) > 1:
            print(f"{len(match)} sessions matchent '{query}' — precise :")
            for title, sid, jf, info in match:
                print(f"  [{short(sid)}] {title[:68]}")
            return

        title, sid, jf, info = match[0]
        print(f"# {title}")
        print(f"- Session : {sid}")
        print(f"- Projet  : {info.get('cwd')}")
        print(f"- Volume  : {info['n_user']} user / {info['n_assistant']} assistant")
        print("\n---\n")
        for role, text, ts in parse_session_full(jf):
            who = "FLORENT" if role == "user" else "CLAUDE"
            print(f"### {who}  [{fmt_date(ts)}]\n{text}\n")
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
