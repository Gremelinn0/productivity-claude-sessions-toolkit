# claude-sessions-toolkit

Retrouve, relance et transporte des sessions Claude Code — sans jamais perdre le contexte, sans
dépendre d'un abonnement actif, et sans consommer un seul token pour la recherche elle-même.

## Le problème que ça résout

Claude Code range chaque session dans un fichier local : `~/.claude/projects/<projet-encodé>/<sessionId>.jsonl`.
Ce fichier existe **indépendamment du compte Claude connecté** — mais rien dans l'interface ne le
dit clairement, et deux pièges classiques en découlent :

- **Tu changes de compte Claude sur le même PC** (le tien a résilié un abonnement, tu en ouvres un
  autre) → ta sidebar redémarre à vide. Tes anciennes sessions te semblent perdues. **Elles ne le
  sont pas** : le disque garde tout, et le store des titres de session est lui aussi partagé entre
  comptes — il suffit de savoir où regarder.
- **Tu changes de PC** → là, il faut réellement transporter un fichier (export → clé USB / cloud
  → import), pas de raccourci possible.

Ce plugin porte les deux gestes, et surtout : il aide à savoir **lequel des deux** s'applique à ta
situation, avant de perdre du temps sur le mauvais.

## Les skills

| Skill | Ce qu'il fait |
|---|---|
| **`/claude-sessions-export`** | Sort les sessions locales hors de la machine, ou les inventorie : filet de sauvegarde avant de changer de compte, index Markdown de toutes tes sessions, ou bundle `.zip` prêt pour un autre PC. |
| **`/claude-sessions-import`** | Retrouve et relance une session avec tout son contexte — y compris une session ouverte sur un **autre compte Claude du même PC**, sans qu'aucun export n'ait été fait au préalable. Réinjecte aussi un bundle venu d'un autre PC (produit par le skill export), avec remap automatique si le nom d'utilisateur diffère. |

Les deux skills partagent un bloc d'entrée identique (« quelle est ta situation ? ») qui route vers
le bon des deux selon 3 cas : session invisible sur cette machine, session sur une autre machine,
ou simple sauvegarde préventive. Peu importe lequel des deux tu invoques en premier, il te renvoie
vers le bon.

## Installation

```
/plugin marketplace add Gremelinn0/productivity-claude-sessions-toolkit
/plugin install claude-sessions-toolkit
```

## 🌍 Portabilité — ce que tu dois savoir avant d'installer

**Classe : ADAPTABLE.** Le plugin ne dépend d'aucun compte, chemin ou dépôt de son auteur — mais il
n'est pas neutre pour autant, et voici exactement où :

| Point | État | Ce que ça implique pour toi |
|---|---|---|
| **Chemins** | Aucun chemin en dur. Tout part de `~/.claude/projects/` et de `%USERPROFILE%` | Rien à changer |
| **Système** | **Windows-first** (voir la section suivante) | Sur Mac/Linux, le cœur marche, la recherche sidebar non |
| **Python** | 3.x, **zéro dépendance externe** (`json`, `pathlib`, `zipfile` seulement) | Rien à installer |
| **Compte Claude** | Aucun. Les scripts lisent des fichiers locaux | Marche même abonnement résilié |
| **Exemples dans les skills** | Génériques (`mon-projet`, `C:\Users\<toi>\...`) | À remplacer par tes vrais chemins |

Les fichiers que les scripts écrivent (exports, `.zip`, index) vont **où tu le demandes** via `--out`,
avec un défaut sous `~/.claude/sessions-export/`. Rien n'est écrit ailleurs sans que tu l'aies dit.

## ⚠️ Setup requis côté plateforme

- **Pensé et testé sur Windows.** Le mécanisme de base (`~/.claude/projects/*.jsonl`, en Python
  pur) est cross-plateforme. Mais la recherche dans la **sidebar Claude Desktop** (titres exacts,
  utilisée par `/claude-sessions-import` pour retrouver une session par nom) lit
  `%APPDATA%\Claude\claude-code-sessions\` et s'appuie sur des snippets PowerShell — sur Mac/Linux,
  ce chemin et ces commandes ne s'appliquent pas tels quels (l'équivalent macOS serait sous
  `~/Library/Application Support/Claude/`, non vérifié par ce plugin). Sans la sidebar, retrouver
  une session déjà visible sur le disque reste possible, juste moins direct.
- **Le lanceur Python `py` (Windows) peut mentir.** S'il honore un shebang `#!/usr/bin/env python3`
  du script et route vers une version de Python différente de celle par défaut (ex. une install
  qui ne voit pas `%APPDATA%`), le script répondra à tort « store introuvable » alors que les
  sessions sont bien là. Si ça arrive : forcer explicitement une version connue-fiable, par exemple
  `py -3.12 scripts/export_claude_sessions.py --sidebar --dry-run` au lieu de `py scripts/export_claude_sessions.py ...`.
  Sur Mac/Linux (pas de lanceur `py`), ce piège précis ne s'applique pas.

## Scripts inclus

Chaque skill embarque sa propre copie de `export_claude_sessions.py`, `import_claude_sessions.py`
et `read_claude_session.py` (`scripts/` — Python pur, aucune dépendance externe). C'est fait exprès
en double : chaque skill reste installable et utilisable seul, sans dépendre de l'autre.
