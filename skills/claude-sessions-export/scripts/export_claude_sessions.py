# -*- coding: utf-8 -*-
"""
Export / index de TOUTES les sessions Claude Code locales.

Les sessions Claude Code sont stockees en local dans ~/.claude/projects/<projet>/<sessionId>.jsonl
INDEPENDAMMENT du compte Claude connecte. Ce script les scanne et produit :

  1. Un INDEX.md unique = liste de toutes les vraies sessions de travail
     (titre, date debut/fin, nb messages, projet reel via cwd, taille, chemin du .jsonl).
     -> sert a IDENTIFIER / RETROUVER n'importe quelle session, sans abonnement actif.

  2. (option --full) Un export Markdown LISIBLE par session (user / assistant en clair)
     -> sert a RELIRE le contenu sans Claude Code, et a push sur git si voulu.

Aucun appel reseau, aucun token Claude consomme : c'est de la lecture de fichiers locaux.

Usage :
    py tools/export_claude_sessions.py                  # index seul (toutes vraies sessions)
    py tools/export_claude_sessions.py --full           # index + export MD complet de chaque session
    py tools/export_claude_sessions.py --full --project speak-app-dev   # full mais 1 projet cible
    py tools/export_claude_sessions.py --include-subagents              # inclut aussi les 736 subagents
    py tools/export_claude_sessions.py --out "D:\\backup\\sessions"     # dossier de sortie custom
"""

from __future__ import annotations
import argparse
import json
import os
import re
import hashlib
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECTS_DIR = Path(os.path.expanduser("~")) / ".claude" / "projects"
DEFAULT_OUT = Path(os.path.expanduser("~")) / ".claude" / "sessions-export"

# Dossiers qui ne sont PAS de vraies sessions de travail Florent
INTERNAL_DIR_PREFIXES = ("subagents", "wf_")


def is_internal_dir(dir_name: str) -> bool:
    return any(dir_name.startswith(p) for p in INTERNAL_DIR_PREFIXES)


def extract_text(obj: dict) -> str:
    """Extrait le texte lisible d'un event JSONL, quel que soit son format."""
    # Format standard Claude Code : obj["message"]["content"]
    msg = obj.get("message")
    content = None
    if isinstance(msg, dict):
        content = msg.get("content")
    if content is None:
        content = obj.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
                elif block.get("type") == "tool_result":
                    # on ignore le detail des tool_result pour la lisibilite
                    pass
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()
    return ""


def clean_title(text: str, maxlen: int = 90) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # vire les marqueurs systeme / caveats / commandes
    if text.startswith("<") or text.startswith("Caveat:"):
        return ""
    if len(text) > maxlen:
        text = text[:maxlen].rstrip() + "..."
    return text


def parse_session(jsonl_path: Path) -> dict:
    """Lit un .jsonl et renvoie un resume de la session."""
    info = {
        "session_id": jsonl_path.stem,
        "path": jsonl_path,
        "cwd": None,
        "ai_title": "",
        "first_user_msg": "",
        "n_user": 0,
        "n_assistant": 0,
        "ts_start": None,
        "ts_end": None,
        "size_bytes": jsonl_path.stat().st_size,
        "messages": [],  # rempli seulement si --full
    }
    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(obj, dict):
                    continue

                etype = obj.get("type")
                ts = obj.get("timestamp")
                if ts:
                    if info["ts_start"] is None:
                        info["ts_start"] = ts
                    info["ts_end"] = ts
                if info["cwd"] is None and obj.get("cwd"):
                    info["cwd"] = obj.get("cwd")

                if etype == "ai-title":
                    t = extract_text(obj) or obj.get("title") or ""
                    if t:
                        info["ai_title"] = clean_title(t, 120)
                elif etype == "user":
                    info["n_user"] += 1
                    if not info["first_user_msg"]:
                        c = clean_title(extract_text(obj))
                        if c:
                            info["first_user_msg"] = c
                elif etype == "assistant":
                    info["n_assistant"] += 1
    except OSError:
        pass
    return info


def parse_session_full(jsonl_path: Path) -> list:
    """Renvoie la liste des echanges (role, text, ts) pour l'export MD complet."""
    rows = []
    try:
        with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get("type") in ("user", "assistant"):
                    text = extract_text(obj)
                    if text:
                        rows.append((obj.get("type"), text, obj.get("timestamp")))
    except OSError:
        pass
    return rows


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_date(ts: str | None) -> str:
    if not ts:
        return "?"
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return ts[:16]


def short(sid: str) -> str:
    return sid[:8] if sid else "?"


def _recency(s: dict) -> int:
    """Recence d'une session pour le tri sidebar : `lastFocusedAt` (derniere fois OUVERTE
    dans l'UI = fidele a l'ordre de la sidebar) en priorite, sinon `lastActivityAt`
    (fausse par l'auto-sync git -> ne reflete pas l'usage reel), sinon 0.
    Tolere les manifests qui n'ont que `last` (pas de `focused`)."""
    return int(s.get("focused") or 0) or int(s.get("last") or 0)


def _maybe_zip(out_dir: Path, do_zip: bool, dry_run: bool = False):
    """Si --zip : compresse le bundle (out_dir) en <out_dir>.zip, pret a transferer
    sur un autre PC puis a reinjecter via import_claude_sessions.py."""
    if not do_zip or dry_run:
        return None
    zp = shutil.make_archive(str(out_dir), "zip", root_dir=str(out_dir))
    print(f"  ZIP            : {zp}  ({os.path.getsize(zp) // 1024} Ko)")
    return zp


def _dominant_project(bundle: Path) -> str:
    """Nom de projet pour le dossier d'export : si toutes les sessions du bundle
    appartiennent a UN seul projet -> ce nom (= dossier repo) ; sinon 'tous-projets'."""
    jsonl_root = bundle / "jsonl"
    if jsonl_root.exists():
        subs = [d.name for d in jsonl_root.iterdir() if d.is_dir()]
        if len(subs) == 1:
            return safe_filename(subs[0], 40)
    return "tous-projets"


def organized_zip(out_root: Path, bundle: Path, project_hint: str | None,
                  export_name: str | None) -> tuple:
    """Range proprement un export : <out_root>/<annee>/<projet>/<stamp>[_<nom>]/<projet>_<stamp>.zip
    = 1 dossier par export, 1 seul .zip propre (pas de fichiers en vrac a la racine).
    Le bundle temporaire est compresse puis supprime. Renvoie (export_folder, zip_path)."""
    now = datetime.now()
    year = now.strftime("%Y")
    stamp = now.strftime("%Y-%m-%d_%H%M")
    proj = safe_filename(project_hint, 40) if project_hint else _dominant_project(bundle)
    leaf = stamp if not export_name else f"{stamp}_{safe_filename(export_name, 40)}"
    export_folder = out_root / year / proj / leaf
    export_folder.mkdir(parents=True, exist_ok=True)
    zp = Path(shutil.make_archive(str(export_folder / f"{proj}_{stamp}"), "zip", root_dir=str(bundle)))
    shutil.rmtree(bundle, ignore_errors=True)
    return export_folder, zp


def project_label(cwd: str | None, dir_name: str) -> str:
    """Nom de projet lisible : le cwd reel si dispo, sinon le nom du dossier.
    Les worktrees (...\\.claude\\worktrees\\<nom>) sont regroupes sous leur projet parent."""
    if cwd:
        for marker in ("\\.claude\\worktrees\\", "/.claude/worktrees/"):
            idx = cwd.find(marker)
            if idx != -1:
                return cwd[:idx]
        return cwd
    return f"(interne) {dir_name}"


def is_worktree(cwd: str | None) -> bool:
    return bool(cwd) and (".claude\\worktrees\\" in cwd or ".claude/worktrees/" in cwd)


def safe_filename(s: str, maxlen: int = 60) -> str:
    s = re.sub(r'[<>:"/\\|?*\n\r\t]+', "-", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return (s[:maxlen] or "session").strip("-")


def write_session_md(s: dict, rows: list, folder: Path) -> Path:
    """Ecrit un MD lisible (user/assistant en clair) pour une session. Renvoie le chemin."""
    folder.mkdir(parents=True, exist_ok=True)
    label = project_label(s.get("cwd"), s["dir_name"])
    date_prefix = (s["ts_end"] or "0000")[:10]
    title = s["ai_title"] or s["first_user_msg"] or "session"
    fname = f"{date_prefix}_{safe_filename(title, 50)}_{short(s['session_id'])}.md"
    md = [f"# {title}", "",
          f"- Projet : `{label}`",
          f"- Session : `{s['session_id']}`",
          f"- Periode : {fmt_date(s['ts_start'])} -> {fmt_date(s['ts_end'])}",
          f"- Messages : {s['n_user']} user / {s['n_assistant']} assistant",
          f"- Source : `{s['path']}`",
          f"- Reprendre : `claude --resume {s['session_id']}` (depuis `{label}`)",
          "", "---", ""]
    for role, text, ts in rows:
        who = "🧑 **Florent**" if role == "user" else "🤖 **Claude**"
        md.append(f"### {who}  _{fmt_date(ts)}_")
        md.append("")
        md.append(text)
        md.append("")
    target = folder / fname
    target.write_text("\n".join(md), encoding="utf-8")
    return target


def _ts_dt(ts: str | None):
    """Parse un timestamp ISO en datetime aware, ou None."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _norm_path(p: str | None) -> str:
    """Normalise un chemin pour comparaison EXACTE cross-shell.
    Reconcilie Windows (C:\\Users\\...) et Git Bash (/c/Users/...) :
    C:/users  -> c/users   et   /c/users -> c/users  (donc egaux)."""
    if not p:
        return ""
    q = p.replace("\\", "/").lower().replace(":", "")  # C:/ -> c/
    return q.lstrip("/").rstrip("/")                     # /c/ -> c/


def export_active(sessions: list, out_dir: Path, days: int, limit: int | None = None,
                  per_project: int | None = None, dry_run: bool = False,
                  md_only: bool = False) -> int:
    """Mode MIGRATION : exporte les sessions ACTIVES vers out_dir.
    Critere = DERNIERE ACTIVITE REELLE (dernier message dans la session, pas la date
    du fichier qui est faussee par l'auto-sync git). Filtre sur `days` + cap `limit`.
    Pour chaque session : copie du .jsonl brut + MD lisible. Plus INDEX-ACTIVE.md + REPRISE.md."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    active = []
    for s in sessions:
        dt = _ts_dt(s["ts_end"])
        if dt is not None and dt >= cutoff:
            active.append(s)
    active.sort(key=lambda s: (s["ts_end"] or ""), reverse=True)

    # Cap par projet : garde les `per_project` sessions les plus recentes de chaque projet
    if per_project:
        seen: dict[str, int] = {}
        capped = []
        for s in active:
            label = project_label(s.get("cwd"), s["dir_name"])
            if seen.get(label, 0) < per_project:
                capped.append(s)
                seen[label] = seen.get(label, 0) + 1
        active = capped

    if limit:
        active = active[:limit]

    by_project: dict[str, list] = {}
    for s in active:
        label = project_label(s.get("cwd"), s["dir_name"])
        proj = safe_filename(Path(label).name if s.get("cwd") else label, 50)
        s["_proj_folder"] = proj
        by_project.setdefault(label, []).append(s)

    if dry_run:
        print(f"[DRY-RUN] {len(active)} sessions actives (derniere activite < {days} j"
              + (f", limit {limit}" if limit else "") + ") :")
        for label, sess in sorted(by_project.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(sess):3d}  {label}")
            for s in sess[:8]:
                t = (s['ai_title'] or s['first_user_msg'] or '?')[:62]
                print(f"          {fmt_date(s['ts_end'])}  {t}")
        return len(active)

    jsonl_root = out_dir / "jsonl"
    md_root = out_dir / "md"
    # nettoyage idempotent des exports precedents (dossiers dedies a ce script)
    for r in (jsonl_root, md_root):
        if r.exists():
            shutil.rmtree(r, ignore_errors=True)

    for s in active:
        proj = s["_proj_folder"]
        # 1) copie du .jsonl brut (resume natif / cross-PC) — SAUF en --md-only (sans screenshots/junk)
        if not md_only:
            dst_dir = jsonl_root / proj
            dst_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(s["path"], dst_dir / s["path"].name)
            except OSError:
                pass
        # 2) MD lisible
        rows = parse_session_full(s["path"])
        if rows:
            write_session_md(s, rows, md_root / proj)

    # INDEX-ACTIVE.md
    idx = [f"# Sessions actives — export du {datetime.now().strftime('%Y-%m-%d %H:%M')}",
           "",
           f"> {len(active)} sessions touchees ces {days} derniers jours, sur {len(by_project)} projets.",
           f"> JSONL bruts dans `jsonl/`, versions lisibles dans `md/`.",
           ""]
    for label, sess in sorted(by_project.items(), key=lambda kv: -len(kv[1])):
        idx.append(f"## `{label}` — {len(sess)} sessions")
        idx.append("")
        idx.append("| Derniere activite | Titre | Msgs | Session |")
        idx.append("|---|---|---|---|")
        for s in sess:
            title = (s["ai_title"] or s["first_user_msg"] or "_(sans titre)_").replace("|", "\\|")
            idx.append(f"| {fmt_date(s['ts_end'])} | {title} | {s['n_user']}↔{s['n_assistant']} | `{short(s['session_id'])}` |")
        idx.append("")
    (out_dir / "INDEX-ACTIVE.md").write_text("\n".join(idx), encoding="utf-8")

    # REPRISE.md — comment relancer proprement
    rep = ["# Reprendre mes sessions proprement", "",
           "> **IMPORTANT - NE RELANCE PAS UNE SESSION TROP VITE (sinon elle est PERDUE).**",
           "> Le 1er message en haut de la session rechargee doit etre : "
           "\"Reprends la session << titre >> ...\" (c'est lui qui recharge tout le contexte).",
           "> Laisse l'IA finir de charger (elle affiche \"contexte charge\" + un resume) AVANT que tu ecrives.",
           "> Si tu vois \"go\" / ton texte / un message tronque a la place = chargement coupe = "
           "l'IA repart a vide = session perdue, a relancer.",
           "",
           "Chaque session Claude Code se reprend en local, **sans dependre du compte connecte**.",
           "", "## Sur CE PC", "",
           "Ouvre un terminal, va dans le dossier du projet, et lance la commande `--resume` :", "",
           "```", 'cd "<dossier du projet>"', "claude --resume <sessionId>", "```", "",
           "## Sur un AUTRE PC", "",
           "1. Copie le `.jsonl` (dossier `jsonl/`) dans `~/.claude/projects/<hash-du-projet>/` du PC cible.",
           "2. Ouvre le projet et lance `claude --resume <sessionId>`.",
           "", "---", ""]
    for label, sess in sorted(by_project.items(), key=lambda kv: -len(kv[1])):
        rep.append(f"## {label}")
        rep.append("")
        for s in sess:
            title = s["ai_title"] or s["first_user_msg"] or "(sans titre)"
            rep.append(f"### {title}")
            rep.append(f"- Derniere activite : {fmt_date(s['ts_end'])} — {s['n_user']}↔{s['n_assistant']} messages")
            rep.append(f"- Reprendre : `claude --resume {s['session_id']}`")
            rep.append(f"- JSONL : `jsonl/{s['_proj_folder']}/{s['path'].name}`")
            rep.append("")
    (out_dir / "REPRISE.md").write_text("\n".join(rep), encoding="utf-8")

    return len(active)


def read_cd_sidebar() -> list:
    """Lit la SOURCE DE VERITE de la sidebar Claude Desktop :
    %APPDATA%/Claude/claude-code-sessions/<fenetre>/local_<id>.json (1 fichier par session).
    Donne le TITRE EXACT (custom) + cwd + isArchived + lien JSONL via cliSessionId.
    Dedup par sessionId (garde le plus recemment actif)."""
    candidates = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "Claude" / "claude-code-sessions")
    candidates.append(Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "Claude" / "claude-code-sessions")
    store = next((c for c in candidates if c.exists()), None)
    if store is None:
        print(f"[sidebar] Store introuvable. Chemins testes : {[str(c) for c in candidates]}")
        print("[sidebar] Si Claude Desktop EST installe : ce Python ne voit pas %APPDATA% "
              "(souvent un Python virtualise Microsoft Store). Relance avec un vrai Python "
              "(python.org) -- le lanceur 'py' peut pointer vers le Store -- ou utilise "
              "--manifest (cf skill /claude-sessions-export, section Pont manifest).")
        return []
    by_id: dict[str, dict] = {}
    for f in store.rglob("local_*.json"):
        try:
            j = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, ValueError, OSError):
            continue
        sid = j.get("sessionId")
        if not sid:
            continue
        rec = {
            "sessionId": sid,
            "cli": j.get("cliSessionId"),
            "cwd": j.get("cwd"),
            "title": (j.get("title") or "").strip(),
            "archived": bool(j.get("isArchived")),
            "pinned": bool(j.get("isPinned")) if j.get("isPinned") is not None else False,
            "exempt": bool(j.get("autoArchiveExempt")),
            "focused": j.get("lastFocusedAt") or 0,   # derniere ouverture UI = ordre sidebar
            "last": j.get("lastActivityAt") or 0,     # fausse par auto-sync git
        }
        if sid not in by_id or _recency(rec) > _recency(by_id[sid]):
            by_id[sid] = rec
    return list(by_id.values())


def build_jsonl_index() -> dict:
    """{nom-de-fichier-sans-extension -> chemin} pour tous les .jsonl, afin de resoudre
    un cliSessionId vers son fichier JSONL reel sans deviner l'encodage du dossier projet."""
    idx = {}
    for jf in PROJECTS_DIR.rglob("*.jsonl"):
        idx[jf.stem] = jf
    return idx


def export_sidebar(out_dir: Path, include_archived: bool = False, dry_run: bool = False,
                   manifest: str | None = None, project: str | None = None,
                   days: int | None = None, limit: int | None = None) -> int:
    """Mode SIDEBAR : exporte EXACTEMENT les sessions de la sidebar Claude Desktop
    (titres custom inclus), non-archivees par defaut. C'est le mode fidele au screenshot.
    `non-archive` = sessions ACTIVES/OUVERTES (Claude Desktop auto-archive les vieilles).
    Filtres optionnels : `project` (sous-chaine du cwd = 1 seul depot), `days` (recence par
    lastActivityAt), `limit` (cap des N plus recentes).
    Si `manifest` est fourni (JSON list de {sessionId,cli,cwd,title,archived,last}), on lit
    cette liste au lieu du store AppData (utile si AppData n'est pas accessible au process)."""
    if manifest:
        try:
            rows_store = json.loads(Path(manifest).read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, ValueError, OSError) as e:
            print(f"[sidebar] manifest illisible ({manifest}): {e}")
            return 0
    else:
        rows_store = read_cd_sidebar()
    if not rows_store:
        print("[sidebar] Store introuvable (%APPDATA%/Claude/claude-code-sessions). "
              "Claude Desktop est-il installe sur ce PC ?")
        return 0
    sel = [s for s in rows_store if include_archived or not s["archived"]]
    if project:
        sel = [s for s in sel if project.lower() in (s.get("cwd") or "").lower()]
    if days is not None:
        cutoff_ms = (time.time() - days * 86400) * 1000
        sel = [s for s in sel if _recency(s) >= cutoff_ms]
    sel.sort(key=_recency, reverse=True)   # ordre = lastFocusedAt (fidele sidebar)
    if limit:
        sel = sel[:limit]

    idx = build_jsonl_index()
    for s in sel:
        s["_jsonl"] = idx.get(s.get("cli")) or idx.get(s["sessionId"])

    by_project: dict[str, list] = {}
    for s in sel:
        by_project.setdefault(s.get("cwd") or "(inconnu)", []).append(s)

    if dry_run:
        n_link = sum(1 for s in sel if s["_jsonl"])
        print(f"[DRY-RUN sidebar] {len(sel)} sessions actives ({n_link} rattachees a un JSONL) :")
        for label, sess in sorted(by_project.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(sess):3d}  {Path(label).name if label != '(inconnu)' else label}")
            for s in sess[:10]:
                flag = "" if s["_jsonl"] else "  [JSONL absent]"
                print(f"          {s['title'][:64]}{flag}")
        return len(sel)

    jsonl_root = out_dir / "jsonl"
    md_root = out_dir / "md"
    for r in (jsonl_root, md_root):
        if r.exists():
            shutil.rmtree(r, ignore_errors=True)

    n_written, n_missing = 0, 0
    for s in sel:
        jf = s["_jsonl"]
        proj = safe_filename(Path(s["cwd"]).name if s.get("cwd") else "inconnu", 50)
        if not jf or not jf.exists():
            n_missing += 1
            continue
        info = parse_session(jf)
        info["ai_title"] = s["title"] or info["ai_title"]   # TITRE EXACT de la sidebar
        info["dir_name"] = jf.parent.name
        info["cwd"] = s.get("cwd") or info.get("cwd")
        s["_info"] = info
        dst_dir = jsonl_root / proj
        dst_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(jf, dst_dir / jf.name)
        except OSError:
            pass
        rows = parse_session_full(jf)
        if rows:
            write_session_md(info, rows, md_root / proj)
        n_written += 1

    # INDEX-SIDEBAR.md
    idxmd = [f"# Ma sidebar Claude Desktop — export du {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             "",
             f"> {len(sel)} sessions actives (non archivees), titres exacts de la sidebar.",
             f"> {n_written} exportees, {n_missing} sans JSONL local trouvable.",
             ""]
    for label, sess in sorted(by_project.items(), key=lambda kv: -len(kv[1])):
        idxmd.append(f"## `{label}` — {len(sess)} sessions")
        idxmd.append("")
        idxmd.append("| Titre (sidebar) | Msgs | Session CLI (= JSONL) |")
        idxmd.append("|---|---|---|")
        for s in sess:
            info = s.get("_info")
            msgs = f"{info['n_user']}↔{info['n_assistant']}" if info else "—"
            title = (s["title"] or "_(sans titre)_").replace("|", "\\|")
            cli = short(s.get("cli") or s["sessionId"])
            idxmd.append(f"| {title} | {msgs} | `{cli}` |")
        idxmd.append("")
    (out_dir / "INDEX-SIDEBAR.md").write_text("\n".join(idxmd), encoding="utf-8")

    # REPRISE.md
    rep = ["# Reprendre mes sessions (sidebar Claude Desktop)", "",
           "> IMPORTANT - NE RELANCE PAS UNE SESSION TROP VITE (sinon elle est PERDUE).",
           "> Le 1er message en haut de la session rechargee doit etre : "
           "\"Reprends la session << titre >> ...\" (c'est lui qui recharge tout le contexte).",
           "> Laisse l'IA finir de charger : elle affiche \"contexte charge\" + un resume AVANT que tu ecrives.",
           "> Si tu vois \"go\" / ton texte / un message tronque a la place = chargement coupe = "
           "l'IA repart a vide = session perdue, a relancer.",
           "",
           "Chaque session se reprend en local, sans dependre du compte connecte :", "",
           "```", 'cd "<dossier du projet>"', "claude --resume <sessionCLI>", "```",
           "Sur un autre PC : copier d'abord le .jsonl (dossier `jsonl/`) dans "
           "`~/.claude/projects/<hash-projet>/`, puis `claude --resume`.", "", "---", ""]
    for label, sess in sorted(by_project.items(), key=lambda kv: -len(kv[1])):
        rep.append(f"## {label}")
        rep.append("")
        for s in sess:
            cli = s.get("cli") or s["sessionId"]
            rep.append(f"- **{s['title'] or '(sans titre)'}** — `claude --resume {cli}`")
        rep.append("")
    (out_dir / "REPRISE.md").write_text("\n".join(rep), encoding="utf-8")

    print("=" * 60)
    print(f"EXPORT SIDEBAR -> {out_dir}")
    print(f"  Sessions actives (sidebar) : {len(sel)}")
    print(f"  Exportees (JSONL trouve)   : {n_written}")
    print(f"  Sans JSONL local           : {n_missing}")
    print(f"  - INDEX-SIDEBAR.md / REPRISE.md / jsonl/ / md/")
    print("=" * 60)
    return n_written


def write_account_status(out_dir: Path, label: str, manifest: str | None = None) -> str:
    """Capture une EMPREINTE du store sidebar pour comparer entre comptes Claude.
    Ecrit account-snapshots/<timestamp>_<label>.json (liste sessions + fingerprint).
    Compare 2 snapshots faits sous 2 comptes differents :
      - meme fingerprint = store PARTAGE (1 seul store local pour tous les comptes)
      - fingerprint different = store RECHARGE par compte (chaque compte a ses sessions)."""
    if manifest:
        try:
            rows = json.loads(Path(manifest).read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, ValueError, OSError) as e:
            print(f"[status] manifest illisible ({manifest}): {e}")
            return ""
    else:
        rows = read_cd_sidebar()
    if not rows:
        print("[status] store vide / introuvable.")
        return ""

    ids = sorted(str(r.get("sessionId", "")) for r in rows)
    fp = hashlib.md5("\n".join(ids).encode("utf-8")).hexdigest()[:12]
    non_arch = [r for r in rows if not r.get("archived")]
    by_proj: dict[str, int] = {}
    for r in non_arch:
        key = r.get("cwd") or "(inconnu)"
        by_proj[key] = by_proj.get(key, 0) + 1

    snap_dir = out_dir / "account-snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snap = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "label": label,
        "total_store": len(rows),
        "non_archived": len(non_arch),
        "fingerprint": fp,
        "by_project_non_archived": dict(sorted(by_proj.items(), key=lambda kv: -kv[1])),
        "sessions": [{"sessionId": r.get("sessionId"), "cli": r.get("cli"),
                      "title": r.get("title"), "cwd": r.get("cwd"),
                      "archived": bool(r.get("archived"))} for r in rows],
    }
    fn = snap_dir / f"{ts}_{safe_filename(label, 30)}.json"
    fn.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print(f"SNAPSHOT STORE -> {fn}")
    print(f"  label             : {label}")
    print(f"  total store       : {len(rows)}")
    print(f"  non-archivees     : {len(non_arch)}")
    print(f"  EMPREINTE         : {fp}")
    for proj, n in list(snap['by_project_non_archived'].items())[:8]:
        print(f"     {n:4d}  {Path(proj).name if proj != '(inconnu)' else proj}")
    print("  --> Change de compte Claude, relance la meme commande avec --label <autre-compte>,")
    print("      puis compare les EMPREINTES (memes = store partage, differentes = store par compte).")
    print("=" * 60)
    return fp


def main():
    # Console Windows en UTF-8 (les titres contiennent des emojis -> evite UnicodeEncodeError cp1252)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Genere aussi un MD lisible par session")
    ap.add_argument("--sidebar", action="store_true", help="Mode SIDEBAR (recommande) : exporte EXACTEMENT la sidebar Claude Desktop (titres custom, sessions non-archivees)")
    ap.add_argument("--include-archived", action="store_true", help="Mode --sidebar : inclut aussi les sessions archivees")
    ap.add_argument("--manifest", default=None, help="Mode --sidebar/--status : lit la liste depuis ce JSON au lieu du store AppData")
    ap.add_argument("--status", action="store_true", help="Capture une EMPREINTE du store sidebar (account-snapshots/) pour comparer entre comptes Claude")
    ap.add_argument("--label", default="compte-inconnu", help="Mode --status : etiquette du compte au moment de la capture (ex: compte-F-pro)")
    ap.add_argument("--active", action="store_true", help="Mode MIGRATION par recence (fallback si pas de Claude Desktop) : .jsonl + md + REPRISE.md")
    ap.add_argument("--days", type=int, default=None, help="Fenetre de derniere activite en jours. --active : defaut 7. --sidebar : optionnel (filtre recence).")
    ap.add_argument("--limit", type=int, default=None, help="Mode --active : cap global du nombre de sessions (les N plus recentes)")
    ap.add_argument("--per-project", type=int, default=None, help="Mode --active : garde les N sessions les plus recentes de CHAQUE projet")
    ap.add_argument("--dry-run", action="store_true", help="Mode --active : compte et liste sans rien ecrire")
    ap.add_argument("--project", default=None, help="Filtre SOUS-CHAINE (subtree) : prend tous les projets dont le cwd/dossier CONTIENT ce texte (= ce dossier ET ses sous-dossiers). Pour le strict par niveau, preferer --exact.")
    ap.add_argument("--exact", action="store_true", help="Filtre STRICT par niveau : ne prend QUE les sessions dont le cwd == --cwd EXACTEMENT (exclut les sous-dossiers). 1 dossier a CLAUDE.md = 1 scope (cf /sessions). RECOMMANDE pour EXPORT.")
    ap.add_argument("--cwd", default=None, help="Mode --exact : le dossier-scope a photographier (defaut: dossier courant). Les sessions des SOUS-dossiers sont exclues (a synchroniser depuis eux-memes).")
    ap.add_argument("--md-only", action="store_true", help="N'exporte QUE les .md lisibles (PAS les .jsonl bruts). Bundle LEGER, sans screenshots/base64 ni junk. Resume = Mode B (Claude lit le .md). RECOMMANDE pour le transport git.")
    ap.add_argument("--include-subagents", action="store_true", help="Inclut les sessions subagents/workflows")
    ap.add_argument("--zip", action="store_true", help="Compresse le bundle en <out>.zip (utile seulement avec --flat ; sans --flat le rangement auto zippe deja)")
    ap.add_argument("--flat", action="store_true", help="Desactive le rangement auto. Ecrit directement dans --out (jsonl/ md/ INDEX) au lieu de <out>/<annee>/<projet>/<date>/<...>.zip. Comportement historique.")
    ap.add_argument("--export-name", default=None, help="Suffixe lisible du dossier d'export range (ex: sidebar-active) — modes --sidebar / --active sans --flat")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="Dossier de sortie (racine du rangement <annee>/<projet>/<export>/ sauf si --flat)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not PROJECTS_DIR.exists():
        print(f"[ERREUR] Dossier introuvable : {PROJECTS_DIR}")
        sys.exit(1)

    # ---- Mode STATUS : empreinte du store pour comparaison multi-comptes ----
    if args.status:
        write_account_status(out_dir, args.label, manifest=args.manifest)
        return

    # ---- Mode SIDEBAR : export fidele a la sidebar Claude Desktop (titres exacts) ----
    if args.sidebar:
        # --flat ou --dry-run : comportement historique (ecrit direct dans --out)
        if args.flat or args.dry_run:
            export_sidebar(out_dir, include_archived=args.include_archived, dry_run=args.dry_run,
                           manifest=args.manifest, project=args.project, days=args.days,
                           limit=args.limit)
            _maybe_zip(out_dir, args.zip, args.dry_run)
            return
        # DEFAUT : rangement auto propre = 1 dossier par export, 1 seul .zip
        bundle = out_dir / ".export-build"
        if bundle.exists():
            shutil.rmtree(bundle, ignore_errors=True)
        bundle.mkdir(parents=True, exist_ok=True)
        n = export_sidebar(bundle, include_archived=args.include_archived, dry_run=False,
                           manifest=args.manifest, project=args.project, days=args.days,
                           limit=args.limit)
        if n > 0:
            export_folder, zp = organized_zip(out_dir, bundle, args.project, args.export_name)
            print("")
            print("  ✅ EXPORT PRET — 1 dossier = 1 export, 1 seul .zip propre")
            print(f"  ZIP     : {zp}  ({os.path.getsize(zp) // 1024} Ko)")
            print(f"  Dossier : {export_folder}")
        else:
            shutil.rmtree(bundle, ignore_errors=True)
            print("[sidebar] Aucune session exportee — rien a ranger.")
        return

    jsonl_files = list(PROJECTS_DIR.rglob("*.jsonl"))
    sessions = []
    n_internal = 0
    n_skipped_filter = 0
    exact_target = _norm_path(args.cwd or os.getcwd()) if args.exact else None

    for jf in jsonl_files:
        dir_name = jf.parent.name
        internal = is_internal_dir(dir_name)
        if internal and not args.include_subagents:
            n_internal += 1
            continue
        info = parse_session(jf)
        info["dir_name"] = dir_name
        info["internal"] = internal

        if exact_target is not None:
            # Strict par niveau : cwd EXACT == --cwd (les sous-dossiers sont exclus)
            if _norm_path(info.get("cwd")) != exact_target:
                n_skipped_filter += 1
                continue
        elif args.project:
            hay = f"{info.get('cwd') or ''} {dir_name}".lower()
            if args.project.lower() not in hay:
                n_skipped_filter += 1
                continue

        sessions.append(info)

    # ---- Mode MIGRATION : export des sessions actives ----
    if args.active:
        _days = args.days if args.days is not None else 7
        # --flat ou --dry-run : comportement historique (ecrit direct dans --out)
        if args.flat or args.dry_run:
            n = export_active(sessions, out_dir, _days, limit=args.limit,
                              per_project=args.per_project, dry_run=args.dry_run,
                              md_only=args.md_only)
            if args.dry_run:
                return
            print("=" * 60)
            print(f"EXPORT SESSIONS ACTIVES -> {out_dir}")
            print(f"  Sessions actives (< {_days} j) : {n}" + ("  [MD-ONLY, sans jsonl/screenshots]" if args.md_only else ""))
            if not args.md_only:
                print(f"  - JSONL bruts   : {out_dir / 'jsonl'}")
            print(f"  - MD lisibles   : {out_dir / 'md'}")
            print(f"  - Recapitulatif : {out_dir / 'INDEX-ACTIVE.md'}")
            print(f"  - Comment relancer : {out_dir / 'REPRISE.md'}")
            _maybe_zip(out_dir, args.zip, args.dry_run)
            print("=" * 60)
            return
        # DEFAUT : rangement auto propre = 1 dossier par export, 1 seul .zip
        bundle = out_dir / ".export-build"
        if bundle.exists():
            shutil.rmtree(bundle, ignore_errors=True)
        bundle.mkdir(parents=True, exist_ok=True)
        n = export_active(sessions, bundle, _days, limit=args.limit,
                          per_project=args.per_project, dry_run=False,
                          md_only=args.md_only)
        if n > 0:
            export_folder, zp = organized_zip(out_dir, bundle, args.project, args.export_name)
            print("=" * 60)
            print(f"  ✅ EXPORT PRET — {n} sessions actives (< {_days} j) — 1 dossier = 1 export")
            print(f"  ZIP     : {zp}  ({os.path.getsize(zp) // 1024} Ko)")
            print(f"  Dossier : {export_folder}")
            print("=" * 60)
        else:
            shutil.rmtree(bundle, ignore_errors=True)
            print("[active] Aucune session active a exporter.")
        return

    # Groupe par projet (cwd reel)
    by_project: dict[str, list] = {}
    for s in sessions:
        label = project_label(s.get("cwd"), s["dir_name"])
        by_project.setdefault(label, []).append(s)

    # Tri : projets par nb de sessions desc ; sessions par date fin desc
    projects_sorted = sorted(by_project.items(), key=lambda kv: -len(kv[1]))

    total_size = sum(s["size_bytes"] for s in sessions)
    lines = []
    lines.append("# Index de toutes mes sessions Claude Code")
    lines.append("")
    lines.append(f"> Genere le {datetime.now().strftime('%Y-%m-%d %H:%M')} — "
                 f"**{len(sessions)} sessions** sur **{len(by_project)} projets** — "
                 f"**{fmt_size(total_size)}**")
    lines.append(f">")
    lines.append(f"> Source locale : `{PROJECTS_DIR}` (independant du compte Claude connecte).")
    if not args.include_subagents:
        lines.append(f"> {n_internal} sessions internes (subagents/workflows) exclues. "
                     f"Relance avec `--include-subagents` pour les voir.")
    lines.append("")
    lines.append("## Sommaire des projets")
    lines.append("")
    for label, sess in projects_sorted:
        anchor = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        lines.append(f"- **{len(sess)}** sessions — `{label}`")
    lines.append("")

    for label, sess in projects_sorted:
        sess_sorted = sorted(sess, key=lambda s: (s["ts_end"] or ""), reverse=True)
        lines.append("")
        lines.append(f"## `{label}`")
        lines.append(f"_{len(sess_sorted)} sessions_")
        lines.append("")
        lines.append("| Derniere activite | Titre | Msgs | Taille | Session | Fichier JSONL |")
        lines.append("|---|---|---|---|---|---|")
        for s in sess_sorted:
            title = s["ai_title"] or s["first_user_msg"] or "_(sans titre)_"
            title = title.replace("|", "\\|")
            if is_worktree(s.get("cwd")):
                title = "🌿 " + title  # session lancee dans un worktree
            msgs = f"{s['n_user']}↔{s['n_assistant']}"
            row = (f"| {fmt_date(s['ts_end'])} "
                   f"| {title} "
                   f"| {msgs} "
                   f"| {fmt_size(s['size_bytes'])} "
                   f"| `{short(s['session_id'])}` "
                   f"| `{s['path']}` |")
            lines.append(row)

    index_path = out_dir / "INDEX.md"
    index_path.write_text("\n".join(lines), encoding="utf-8")

    # ---- Export complet optionnel ----
    n_full = 0
    if args.full:
        full_root = out_dir / "sessions"
        for s in sessions:
            rows = parse_session_full(s["path"])
            if not rows:
                continue
            label = project_label(s.get("cwd"), s["dir_name"])
            proj_folder = full_root / safe_filename(Path(label).name if s.get("cwd") else label, 50)
            proj_folder.mkdir(parents=True, exist_ok=True)
            date_prefix = (s["ts_end"] or "0000")[:10]
            title = s["ai_title"] or s["first_user_msg"] or "session"
            fname = f"{date_prefix}_{safe_filename(title, 50)}_{short(s['session_id'])}.md"
            md = [f"# {title}", "",
                  f"- Projet : `{label}`",
                  f"- Session : `{s['session_id']}`",
                  f"- Periode : {fmt_date(s['ts_start'])} -> {fmt_date(s['ts_end'])}",
                  f"- Messages : {s['n_user']} user / {s['n_assistant']} assistant",
                  f"- Source : `{s['path']}`", "", "---", ""]
            for role, text, ts in rows:
                who = "🧑 **Florent**" if role == "user" else "🤖 **Claude**"
                md.append(f"### {who}  _{fmt_date(ts)}_")
                md.append("")
                md.append(text)
                md.append("")
            (proj_folder / fname).write_text("\n".join(md), encoding="utf-8")
            n_full += 1

    # ---- Resume console ----
    print("=" * 60)
    print(f"INDEX genere : {index_path}")
    print(f"  Sessions indexees : {len(sessions)}")
    print(f"  Projets           : {len(by_project)}")
    print(f"  Taille JSONL      : {fmt_size(total_size)}")
    if not args.include_subagents:
        print(f"  Internes exclues  : {n_internal} (subagents/wf)")
    if args.project:
        print(f"  Filtre projet     : '{args.project}' ({n_skipped_filter} hors filtre)")
    if args.full:
        print(f"  Export MD complet : {n_full} fichiers dans {out_dir / 'sessions'}")
    print("=" * 60)
    print("\nTop projets :")
    for label, sess in projects_sorted[:10]:
        print(f"  {len(sess):4d}  {label}")


if __name__ == "__main__":
    main()
