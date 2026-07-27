---
description: Vérifie que le toolkit de sessions voit bien tes sessions Claude Code sur cette machine, diagnostique le piège Python de Windows, et explique lequel des deux skills s'applique à ta situation.
argument-hint: "[--uninstall]"
---

# Setup — claude-sessions-toolkit

Tu exécutes le setup de ce pack. Trois fonctions, **dans cet ordre** : VÉRIFIER, INSTALLER, EXPLIQUER.

> ⚠️ **Le verdict se CALCULE.** Chaque ligne vient d'une sonde lancée à l'instant. **« Non vérifiable »
> est une réponse autorisée** ; une case cochée sans mesure est pire qu'une case absente.
>
> 🔢 **Et ici, un zéro se prouve.** Ce pack compte des sessions. Un « 0 session » peut vouloir dire
> « il n'y en a pas » **ou** « je ne regardais pas au bon endroit » — les deux sont indiscernables, et
> c'est précisément le piège que la section (b) existe pour attraper. Ne conclus jamais d'un zéro sans
> avoir prouvé que l'instrument sait voir.

## Si l'argument est `--uninstall`

Ce pack ne modifie **rien** en s'installant : pas de configuration, pas de fichier posé.

En revanche, **utilisé**, il **écrit des exports** là où tu les lui as demandés — par défaut sous
`~/.claude/sessions-export/`, sinon au chemin passé en `--out`. Ce sont **tes** archives : liste-les
(nombre, emplacement, taille totale) et **laisse-le décider**. Ne supprime rien de toi-même : un export
est parfois le dernier exemplaire d'une session.

⚠️ **Ne touche jamais à `~/.claude/projects/`** — ce sont les sessions elles-mêmes, pas des artefacts
du pack.

## 1 — VÉRIFIER

**a) Les deux compétences sont-elles là ?** Liste `skills/`. Le résultat est le verdict.

**b) Python voit-il tes sessions ?** C'est **le** point qui décide de tout, et il ne se suppose pas.
Lance le script d'export **en mode simulation** (`--dry-run`), qui n'écrit rien :

- **Il liste des projets et des sessions** → ✅ l'instrument voit. C'est la seule preuve.
- **Il rend « 0 session »** → ⚠️ **ne conclus pas « pas de sessions »**. Vérifie d'abord que
  `~/.claude/projects/` contient bien des fichiers `.jsonl`. Si le dossier est plein et que le script
  rend zéro, **c'est l'instrument qui est aveugle, pas la machine qui est vide.**
- **Sur Windows** : le lanceur `py` peut router vers une version de Python qui ne voit pas
  `%APPDATA%`, et le script annonce alors « store introuvable » alors que tout est là. Teste avec une
  version explicite (`py -3.12 …`) avant de conclure quoi que ce soit.

**c) La recherche par titre (sidebar) fonctionne-t-elle ?** C'est la partie **Windows-first** du pack :
elle lit le store de Claude Desktop sous `%APPDATA%\Claude`. Sonde son existence. Sur Mac ou Linux,
elle ne s'applique pas — dis-le franchement, ça ne rend pas le reste inutile.

## 2 — INSTALLER

Rien à installer : Python 3 suffit, **aucune dépendance externe** (le pack n'utilise que la
bibliothèque standard). Vérifie juste que Python répond.

Si la sonde (b) est rouge, le seul geste utile est de **trouver le bon interpréteur** — pas de
réinstaller quoi que ce soit.

## 3 — EXPLIQUER

**Comment ça marche.** Claude Code range chaque session dans un fichier local, indépendant du compte
connecté. Le pack sait où regarder. C'est tout — et c'est pour ça qu'il ne consomme aucun token et ne
demande aucun abonnement actif.

**Quel skill pour quelle situation** — c'est la question qui fait perdre le plus de temps :

| Ta situation | Le bon skill |
|---|---|
| Tes sessions ont disparu de la barre latérale après un changement de compte | **`/claude-sessions-import`** — elles sont sur le disque, aucun export n'est nécessaire |
| Tu changes de **PC** | **`/claude-sessions-export`** puis import de l'autre côté — là, il faut vraiment transporter un fichier |
| Tu veux une sauvegarde avant de bricoler | **`/claude-sessions-export`** |

**Pourquoi ça n'a rien fait.**
1. **Le mauvais interpréteur Python** (piège `py` ci-dessus) — la cause n°1 sur Windows.
2. Tu cherchais à **retrouver** une session et tu as lancé l'**export** : l'export ne sert pas à ça.
3. Tu es sur Mac ou Linux et tu comptais sur la **recherche par titre** — elle est Windows-first.

## Le rapport final

```
Compétences        : <n> trouvée(s) — <noms>
Python voit        : ✅ <n> projets / <n> sessions | ❌ 0 (instrument suspect, cf b)
Recherche sidebar  : ✅ store trouvé | ⚠️ hors Windows, non applicable | ❌ absent
Écrit à l'install  : rien
Exports existants  : <n> sous <chemin> (tes archives, pas des artefacts)
```

Puis **une** phrase : ce qu'il peut faire, ou le seul geste qui manque.
