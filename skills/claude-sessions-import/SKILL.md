---
name: claude-sessions-import
description: >-
  RETROUVE et RELANCE une session Claude Code avec tout son contexte — y compris une session
  ouverte sur un AUTRE COMPTE Claude du même PC (cas n°1, aucun export préalable requis : le
  store sur disque est partagé entre comptes, seule la sidebar affichée est filtrée ; `list_sessions`
  ne les voit pas, `--sidebar` si). Aussi : réinjecte un bundle venu d'un autre PC (produit par
  /claude-sessions-export) avec remap automatique du username (Administrateur ↔ Utilisateur).
  Zéro réseau, zéro token, zéro crédit. Mode B recommandé : un chip par session, Claude lit le
  transcript et reprend le fil. Triggers : "/claude-sessions-import", "cherche la session X sur ce PC",
  "la session est sur un autre compte", "réimporte cette session ici", "récupère les sessions",
  "récupère mes sessions", "récupère les sessions du zip", "importer mes sessions",
  "réinjecter le zip", "récupérer mes sessions sur ce PC", "lis cette session exportée",
  "continue le travail de la session", "relance ces sessions", "j'ai changé de compte Claude",
  "reprendre mes sessions sur mon autre compte", "plus de crédits reprends mes sessions",
  "voici une capture de mes sessions relance-les", "session morte contexte plein".
---

# Import / Réinjection des sessions Claude Code

## 🧭 PORTE D'ENTRÉE — établir le cas AVANT de toucher à quoi que ce soit

> ⚠️ **Ce bloc est IDENTIQUE dans `/claude-sessions-export` et `/claude-sessions-import`.** C'est
> volontaire, et c'est tout l'intérêt : les deux compétences se ressemblent et font des choses
> **opposées**. Quelqu'un qui découvre le système ouvre naturellement la mauvaise — c'est le seul
> vrai piège du sujet. Peu importe celle qu'il a ouverte, il repart d'ici avec la bonne.
> **Toute modification de ce bloc se répercute dans l'autre skill, même passe.**

### 1. Déduire d'abord — la demande contient presque toujours la réponse

Ne jamais ouvrir par un interrogatoire : la plupart des formulations tranchent déjà.

| Ce que dit l'utilisateur | Cas |
|---|---|
| « sur ce PC », « un autre compte », « je ne la vois plus », « ma sidebar est vide », « session morte / contexte plein » — ou il **nomme** simplement une session | **A** |
| il parle d'un `.zip`, d'une **clé USB**, de « l'autre PC », « mon portable », « celui du bureau » | **B** |
| « je vais changer de compte / de PC », « sauvegarde », « avant que je parte », « au cas où » | **C** |

Signal clair → **annoncer le cas en une ligne et avancer**. Pas de question.

### 2. Demander seulement si c'est réellement ambigu — UNE question

Au moindre doute, poser la question (via `AskUserQuestion`), parce que se tromper de branche coûte
bien plus cher que dix secondes :

> **« La session que tu veux récupérer, elle est sur CE PC, ou sur un AUTRE PC ? »**
> A — sur ce PC, mais je ne la vois plus · B — sur un autre PC · C — je veux juste sauvegarder avant de partir

### 3. Les trois cas

**A — Elle est sur CE PC, mais je ne la vois plus.** *(le plus fréquent)*
Autre compte Claude, sidebar vide après une bascule de compte, session morte (contexte plein).
→ **`/claude-sessions-import`**, tout de suite, § 📸 Méthode capture d'écran ci-dessous.
**Aucun export n'est nécessaire — ni maintenant, ni rétroactivement.** Les fichiers de session sont
sur le disque, liés au compte **Windows** et non au compte Claude, et le store des titres est
**partagé entre les comptes**. C'est le cas qu'on rate le plus souvent, en croyant à tort qu'il
faut d'abord avoir exporté.

**B — Elle est sur un AUTRE PC.**
Là, il faut réellement transporter un fichier. Trois gestes, dans l'ordre :
1. **Sur le PC d'origine** → `/claude-sessions-export` : il produit un `.zip`.
2. **Copier ce `.zip`** sur une clé USB (ou tout autre transport : dossier partagé, cloud, ou `/claude-sessions-sync` pour les petits dépôts git).
3. **Sur le PC d'arrivée** → `/claude-sessions-import` en pointant le `.zip`.

   La clé USB est **parfaitement légitime ici** — c'est exactement le cas pour lequel elle existe.

**C — Je pars, je veux juste une sauvegarde.**
Bascule de compte, réinstallation, prudence.
→ **`/claude-sessions-export`** seul. Zéro token, aucun abonnement actif requis.
Nuance à dire pour éviter la fausse inquiétude : sur le **même PC**, cet export est une **assurance**,
pas un péage — le cas A fonctionnera de toute façon sans lui. Il devient vraiment indispensable dès
qu'on quitte la machine (cas B) ou qu'on risque de perdre le disque.

> Le principe commun aux trois : **Claude lit la session et reprend le fil.** L'utilisateur ne tape
> aucune commande, aucun identifiant — il dit où il en est, et on s'occupe du reste.

> ⛔ **RÈGLE D'OR — UNE SESSION = UNE SESSION, JAMAIS DE FORK/DOUBLON.**
> 1. **On spawn TOUS les chips D'UN COUP, dans le MÊME tour** — zéro lot, zéro pause, zéro « je reviendrai finir ». **Le rationnement 5-par-5 côté Claude est ABOLI (2026-07-16)** : il n'a jamais rien protégé (10 chips OK le 2026-06-20, 12 OK le 2026-07-16) et c'est LUI qui faisait oublier la moitié des sessions. Le « 5 par 5 » n'est PAS une limite de spawn : c'est une consigne **pour l'USER au moment de CLIQUER** → cf 🖐️ ci-dessous.
> 2. Chaque chip lance **UNE session propre** — jamais un fork, jamais un doublon.
> 3. **Si la session existe DÉJÀ / est vivante** (visible dans la sidebar, trackée) → on **POSTE le message DEDANS** (`send_message` via `/sessions`), on ne la rouvre pas, on ne la re-crée pas. On ne spawne un chip **que** pour une session qui n'a **pas** déjà sa fenêtre vivante.
> 4. **ZÉRO LECTURE DE CONTENU ICI.** Relancer = un lookup MÉCANIQUE `titre → chemin .jsonl` (dict local, quelques lignes), puis `spawn_task`. Point. **Jamais** de `parse_session`/dump de métadonnées (nb messages, dates, aperçu du 1er message) ni de lecture du transcript **dans cette session orchestratrice** — ni pour "vérifier", ni pour "un meilleur titre" (le titre vient déjà de la sidebar). Le contenu se lit **UNE SEULE FOIS**, DANS le chip, à son ouverture. Le relire ici = payer deux fois la même lecture pour zéro décision utile.
>
> *(Jurisprudence 2026-07-10 : forks en masse sur le même PC = doublons inutiles = à ne jamais refaire. « Une session = une session. » — Jurisprudence 2026-07-15 : dump `parse_session` (métadonnées) d'une session déjà résolue, juste avant de spawner son chip = gaspillage pur. Florent : « 2K token pr relancer une session mdr c une blague ? ». Dès que titre+cwd+chemin `.jsonl` sont connus → spawn IMMÉDIAT, zéro étape de plus.)*

> 🖐️ **LE « 5 PAR 5 » EST UN RAPPEL VÉNÈRE À SERVIR À L'USER — PAS UN RATIONNEMENT DE MES SPAWNS (gravé 2026-07-16).**
> **Moi** : je spawn **TOUTES** les sessions de la liste, d'un coup, tour unique. Mon job de lancement est fini là.
> **Lui** : c'est **au CLIC** que le paquet doit être petit. Donc **toute réponse qui livre des chips de relance se termine par un rappel EXPLICITE et bien visible** (pas une note de bas de page) :
> - ⚠️ **« CLIQUE-LES 5 PAR 5 MAX — attends que le paquet précédent affiche `✅ contexte chargé` avant d'en lancer 5 de plus. »**
> - ⚠️ **« Si une session n'a pas démarré, ou est repartie à vide → relance CE chip-là, lui seul. »** (repère de panne : 1er message ≠ « Reprends la session … » ⇒ ratée, cf ⏳ ci-dessous.)
> - ⛔ **INTERDIT de rationner MES spawns « pour aider »** — c'est exactement ce qui a produit l'oubli : je m'auto-limitais à 5, je ne revenais jamais finir, et des sessions restaient au tapis **en silence**. Un chip en trop se dismisse d'un clic ; une session jamais lancée, personne ne la voit.
>
> *(Jurisprudence 2026-07-16 : rationnement 5-par-5 côté Claude → 5/12 lancées, puis 12/13 (Pricing oubliée). Florent : « ça a déjà marché très bien… toi tu oublies complètement de te réactiver, donc on enlève ça, et on met juste un rappel bien vénère à l'utilisateur de les valider 5 par 5… tu as oublié la moitié des sessions, frérot, je n'ai pas que ça à branler. »)*

> ⏳ **NE LANCE PAS LA SESSION TROP VITE — sinon elle est PERDUE.** Quand tu cliques un chip / rouvres une session importée, le **tout 1er message en haut de la session** doit être **« Reprends la session « &lt;titre&gt; » … »** — c'est LUI qui recharge tout le contexte (lecture du `.jsonl`). **Laisse l'IA finir de charger** : elle répond **« ✅ contexte chargé »** + un résumé **avant** que tu écrives.
>
> 🚨 **Repère de panne** : si tu vois **autre chose en haut** (juste `go`, ton propre texte, un message tronqué) au lieu de « Reprends la session « … » » → le chargement a été **coupé / tapé par-dessus** → l'IA repart **À VIDE** (elle ne sait plus quelle session elle est, elle devine faux) → **session perdue, à RELANCER**. Ne tape **rien** tant que le « Reprends la session « … » » + le **feu vert** (« ✅ contexte chargé ») ne sont pas affichés.

## 📸 MÉTHODE CAPTURE D'ÉCRAN — même PC, changement de compte (la plus simple, 0 crédit)

> 🔑 **Le cas normal, dit clairement** : ces sessions étaient TOUTES ouvertes sur un **AUTRE compte Claude**, sur CE MÊME PC (compte A vidé → tu passes sur B). Elles ne sont PAS liées au compte Claude mais à ta session **Windows** → le nouveau compte les retrouve toutes en local. La capture sert juste à dire **lesquelles** relancer ; le travail (retrouver + rouvrir via chips) se fait sur le **compte cible** (celui qui a des crédits). C'est exactement ce que Florent fait quand il change de compte.
>
> ↔️ **Symétrie export → import (à dire à l'utilisateur)** : si quelqu'un **exporte** ses sessions via `/claude-sessions-export`, on le prévient que **l'import se fait depuis son AUTRE compte Claude** via `/claude-sessions-import` — jamais sur le compte qu'il quitte (celui-là n'a plus de crédits, c'est justement la raison du transfert).

**Quand l'utiliser** : tu es sur le **même PC** et tu as **changé de compte Claude** (ex : le compte A n'a plus de crédits, tu passes sur B). Tes sessions sont liées à ta **session Windows**, **pas** au compte Claude → elles sont **déjà là**, le compte B peut les rouvrir. **Aucun crédit consommé sur le compte A** (screenshoter est gratuit), **aucune clé USB**, **aucun export**.

**👤 Côté toi (débutant) — 3 gestes :**
1. Sur le **compte A** : fais une **capture d'écran de ta sidebar** Claude Code (les sessions à garder).
2. Passe sur le **compte B** (même PC).
3. Donne la capture à Claude et dis : *« relance ces sessions »*. C'est tout.

**🤖 Côté Claude (ce que JE fais sur le compte cible)** :
1. **Lire les titres** de sessions dans la capture (vision).
   - ⚠️ **JAMAIS présumer qu'une ligne est un INTERTITRE** parce qu'elle est en MAJUSCULES / sans emoji : un **titre de session** peut y ressembler à s'y méprendre. Une ligne n'est un intertitre **que si AUCUNE session du store ne porte ce titre** — ça se **vérifie** à l'étape 2, ça ne se devine pas à l'œil. En cas de doute → on la traite comme une session (un chip en trop se dismisse ; une session oubliée, personne ne la voit).
   - *(Jurisprudence 2026-07-16 : `PRICING - PAUSE` classée « intertitre » par ressemblance avec `MARKETING` juste au-dessus — qui, lui, en était vraiment un. Résultat : session oubliée, 12 lancées sur 13. Florent : « Tu as oublié la session PRicing, voilà. » Le contrôle coûte un grep ; l'oubli est silencieux.)*
2. **Les retrouver en local** (même utilisateur Windows → mêmes fichiers) — **UNE commande, celle-ci** :
   ```powershell
   py -3.12 scripts/export_claude_sessions.py --sidebar --dry-run   # titre EXACT -> cliSessionId -> cwd
   ```
   → matcher chaque titre de la capture à son `cliSessionId` + `cwd`. Puis étape 3, direct.

   > 🚨 **`py -3.12`, JAMAIS `py` nu — sinon l'outil MENT en silence** (gravé 2026-07-25, ça a coûté une session entière). `py` honore le shebang `#!/usr/bin/env python3` du script et route vers un Python 3.14 qui **ne voit pas `%APPDATA%`** → le script répond **« [sidebar] Store introuvable »** alors que le store est là et plein. C'est un **zéro d'environnement** (CLAUDE-GLOBAL §9) : indistinguable d'un vrai « pas de sessions ». **Témoin qui tranche en 3 s** : `py -3.12 -c "import os;from pathlib import Path;print(Path(os.environ['APPDATA'],'Claude','claude-code-sessions').exists())"` → `True` alors que le script dit introuvable ⇒ c'est l'instrument, pas le store. *(Le piège jumeau est documenté côté export depuis le 2026-06-02 ; il manquait ICI, donc une session entrée par l'import ne le voyait jamais.)*

   > ⛔ **« Store introuvable » ⇒ on RÉPARE l'instrument, on ne se rabat JAMAIS sur un scan des `.jsonl` par titre.** Ce fallback figurait ici et il est **structurellement impossible** : **le titre de la sidebar n'existe PAS dans le `.jsonl`** — il vit uniquement dans le store (`local_*.json`, champ `.title`, relié au fichier par `.cliSessionId`). Un `.jsonl` ne porte que le 1er message. *(Prouvé 2026-07-25 : 1648 sessions listées depuis `~/.claude/projects/`, grep « quotas » ⇒ 2 hits de sous-agents sans rapport ; la vraie session s'appelait « 🗄️ supabase — Quotas ✔️ - EXPORTED », chaîne absente de tout `.jsonl`. Idem pour l'INDEX global : il titre au 1er message, pas au titre sidebar.)* Instrument réparé = la session sort en quelques secondes. Voie de secours si `-3.12` ne suffit pas : le **pont manifest** PowerShell (`/claude-sessions-export` § Pont manifest), jamais le scan par titre.

   > 🔑 **Le store sur DISQUE est PARTAGÉ entre comptes — c'est la sidebar AFFICHÉE qui est filtrée par compte.** C'est *pour ça* que cette méthode marche. Prouvé live le 2026-07-25 : la session quotas d'un **autre compte** est **absente** de `list_sessions` (vue du compte courant) et **présente** dans le store lu sur disque (1328 enregistrements). ⇒ **l'outil de recherche cross-comptes = la lecture du store** (`--sidebar`, qui lit `%APPDATA%\Claude\claude-code-sessions\**\local_*.json`) ; **`list_sessions` ne voit jamais les autres comptes** et son silence ne prouve rien. Tranche l'hypothèse (a) laissée ouverte dans `/claude-sessions-export` § Multi-comptes.

   - ⛔ **STOP dès que titre+`cwd`+id sont résolus.** Pas de lecture du `.jsonl` trouvé, pas de `parse_session()`/comptage messages/aperçu « pour vérifier avant de spawner » — zéro utilité, ça double juste la lecture que le chip fera lui-même (cf ⛔ Règle d'or point 4 en tête de skill).
3. Pour **TOUTES** les sessions trouvées, **d'un coup, même tour** (aucun rationnement — cf ⛔ Règle d'or point 1) : **si elle est déjà vivante** (fenêtre ouverte / trackée) → **`send_message` DEDANS** (via `/sessions`), pas de nouvelle session ; **sinon** → **spawner UN chip** (Mode B, cf § 🎰 chips) = **une session propre** (jamais un fork/doublon) qui **lit le `.jsonl` LOCAL** et reprend le fil :
   - `title` = le titre d'origine (celui de la capture).
   - `cwd` = le dossier du projet de la session.
   - `prompt` (self-contained) — **1re ligne visible en haut** = *« Reprends la session « <titre> » — ⏳ je charge le contexte, n'écris rien… »*, PUIS *charge depuis le `.jsonl` local (`~/.claude/projects/<cwd-encodé>/<id>.jsonl`, via `read_claude_session.py` ou lecture directe) → affiche « ✅ contexte chargé » + résume 3 lignes → reprends le fil → attends instructions.* **Chemins ABSOLUS.** (Repère de panne : si l'user voit `go`/autre chose à la place → 1er message coupé, à relancer.)
4. Tu **cliques** sur chaque chip → la session repart avec **tout son contexte**.

> ⚙️ **Base technique (pourquoi ça marche sans crédits)** : `~/.claude/projects/<cwd-encodé>/<id>.jsonl` = 1 fichier / session, **lié au compte Windows** (jamais au compte Claude). Même PC + même utilisateur Windows = **mêmes fichiers**, quel que soit le compte Claude connecté. La capture d'écran sert **uniquement** à dire à Claude **lesquelles** relancer. Le travail (retrouver + rouvrir) se fait **sur le compte cible**, qui, lui, a des crédits.
>
> 🔎 **Nuance multi-comptes (honnête)** : selon que le *store* de la sidebar est partagé ou rechargé par compte (question encore ouverte, cf `/claude-sessions-export` § Multi-comptes), l'étape 2 passe par le store **ou** par le scan direct des `.jsonl`. Les deux chemins sont ci-dessus → robuste dans les deux cas.

## 🎯 Objectif (ce que ça résout)

Reprendre des sessions Claude Code exportées ailleurs **sur ce PC**, sans dépendre du compte
connecté. Claude Code range chaque session ici :

```
~/.claude/projects/<cwd-encodé>/<sessionId>.jsonl
```

où `<cwd-encodé>` = le chemin de travail avec **chaque caractère non-alphanumérique remplacé
par `-`** (vérifié : `C:\Users\Utilisateur\PROJECTS\3- Wisper\speak-app-dev` →
`C--Users-Utilisateur-PROJECTS-3--Wisper-speak-app-dev`). **Le piège** : le nom d'utilisateur
change souvent d'un PC à l'autre → le dossier encodé change → une copie naïve atterrit au
mauvais endroit et `claude --resume` ne retrouve rien. Ce skill lit le `cwd` d'origine **dans
chaque .jsonl**, le **remappe**, l'encode, et dépose le fichier au bon endroit.

Outil : [`scripts/import_claude_sessions.py`](../../../scripts/import_claude_sessions.py) (fonction
`import_bundle()` réutilisable — aussi câblée au bouton Réglages « Transférer mes sessions »).

> 🔑 **Transport par clé USB (cas Florent migration de compte/PC).** L'export `/claude-sessions-export`
> sort un `.zip` (rangé `<année>/<projet>/<date>/<projet>_<date>.zip`) → copié sur la clé. Sur l'AUTRE PC,
> Florent dit simplement **« récupère les sessions »** / **« importe la dernière migration »** et Claude
> **trouve le `.zip` tout seul sur la clé** (la lettre du lecteur change d'un PC à l'autre — NE PAS présumer `D:`).
> Mode B par défaut : Claude lit le zip et reprend le fil (rien à réinjecter). Aucun token, aucun réseau, aucun compte requis.

**Trouver le zip d'export tout seul sur une clé USB** (lecteurs amovibles, lettre variable) :

```powershell
$sys = $env:SystemDrive   # lecteur systeme (C:) a exclure du scan
Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DeviceID -ne $sys -and $_.DriveType -in 2,3 } | ForEach-Object {
  Get-ChildItem ($_.DeviceID + "\") -Recurse -Depth 2 -Filter "*.zip" -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'sessions|speak-app-dev|sidebar|migration' }
} | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
```
→ Claude prend le **plus récent** et le passe à `read_claude_session.py` (Mode B, lecture+reprise) ou
`import_claude_sessions.py` (réinjection). Une clé USB peut apparaître en `DriveType=2` (amovible) **ou** `3`
(fixe, selon le contrôleur) → on scanne les deux, hors lecteur système. Rien trouvé (clé pas branchée /
éjectée) → demander le chemin à Florent. Vérifié 2026-06-20 : retourne vide quand la clé est éjectée (OK).

## 🅱️ Mode B — Claude LIT le fichier et reprend (mode ACTUEL, « pour commencer »)

Le `.zip` contient les conversations **en clair** → **pas besoin de réinjecter quoi que ce soit** :
Claude lit la session et **continue le travail** avec tout le contexte. Le plus simple, dispo tout
de suite, ne touche à rien sur le PC. C'est « le boulot de Claude ».

Sur l'autre PC, Florent dit *« reprends la session X (du zip) »* → Claude exécute :

```powershell
py scripts/read_claude_session.py "<chemin>\sessions-export.zip"               # liste (TES titres sidebar)
py scripts/read_claude_session.py "<chemin>\sessions-export.zip" "LGM-CHROME"  # lit le transcript complet
py scripts/read_claude_session.py "%USERPROFILE%\.claude\projects\<cwd-encodé>\<id>.jsonl"  # .jsonl LOCAL direct (même PC / capture d'écran) — PAS besoin de zip
```
→ recherche par **titre de sidebar** OU par id, accepte `.zip`, un dossier bundle, **ou un `.jsonl`
local direct** (le chemin canonique du chip Mode B « capture d'écran » — même PC, aucun zip à bâtir),
**aucune écriture**. Claude ingère le transcript et reprend le fil. (Outil : `scripts/read_claude_session.py`.)

> ⚠️ **Ne fait PAS « pop » la session dans la sidebar Claude Desktop** — c'est voulu : en Mode B
> c'est Claude qui porte la mémoire, pas la GUI. Pour un vrai pop natif → **Mode A (à venir)**.

## 🎰 Relancer EN SÉRIE via CHIPS (autonome — le mode pour plusieurs sessions)

Quand Florent veut relancer PLUSIEURS sessions (« relance mes sessions du zip », « les épinglées »,
ou il en nomme) : Claude **spawne un chip par session** → Florent **clique**, il ne tape rien, et
la session repart avec **tout son contexte**. C'est le « balance toutes les chips » de Florent.

> 🖐️ **On spawn TOUT d'un coup** (aucun rationnement côté Claude — cf ⛔ Règle d'or point 1), et **on
> termine la réponse par le RAPPEL VÉNÈRE à Florent : « clique-les 5 PAR 5 max, attends le `✅ contexte
> chargé` du paquet avant les 5 suivants ; une session pas partie → relance CE chip-là »**. Et **une
> session vivante ne se re-spawne pas** : si elle est déjà ouverte/trackée → **`send_message` dedans**
> (via `/sessions`), pas un nouveau chip. Un chip = **une session propre**, jamais un fork/doublon.

Procédure (Claude exécute) :
1. **Lister** les sessions du bundle/zip + leur `cwd` :
   `py scripts/read_claude_session.py "<zip>"` (titres SIDEBAR) ; le `cwd` par session se lit dans
   l'export (header de section `INDEX-SIDEBAR.md`, ou champ `cwd` du transcript).
   - ✅ Ce lookup = liste de titres + `cwd` + id, RIEN d'autre.
   - ❌ **N'insère PAS d'étape 1bis** « je vérifie le contenu / la taille / la date avant de spawner » —
     `parse_session()`, comptage messages, aperçu du 1er message = zéro utilité ici (titre + cwd
     suffisent au `spawn_task`), ça ne fait que payer une lecture pour rien (cf ⛔ Règle d'or point 4).
     Dès que titre+cwd+id sont connus pour une session → étape 2 direct, pas de détour.
2. Pour CHAQUE session retenue → `spawn_task` :
   - **title** = le **nom d'origine** (titre sidebar) — Florent y tient.
   - **cwd** = le **dossier du projet** de la session (§14 : rooté au bon endroit, sinon le travail
     reprend au mauvais endroit ; omis si = dépôt courant).
   - **prompt** (Mode B, self-contained §23.1). ⚠️ **Sa 1re ligne = le repère que l'user DOIT voir en haut
     de la session** — commence LITTÉRALEMENT par « **Reprends la session « <titre> »** — ⏳ je charge le
     contexte, n'écris rien… », PUIS charge :
     `py "<abs>\tools\read_claude_session.py" "<zip>" "<id8>"` → affiche **« ✅ contexte chargé »** + résume
     3 lignes → reprends le fil → attends instructions. **Chemins ABSOLUS** (le chip tourne dans un autre
     cwd / worktree). Si l'user voit `go`/un autre texte à la place de cette 1re ligne = 1er message coupé →
     import raté, à relancer.
3. Florent clique → session relancée, contexte préservé, chip consommé (sort de la liste).

> Chaque chip = sa session (worktree isolé) → relance de plusieurs en parallèle.
> Jurisprudence : 10 chips épinglés spawnés le 2026-06-20 (test live, rootés par projet).

## 🔁 Reprise native CLI (`claude --resume`) — copie des `.jsonl`

> Recopie les `.jsonl` au bon endroit → `claude --resume <id>` marche **depuis un terminal**, mais
> ne pop pas non plus dans la sidebar (voir Mode A). Surtout utile pour les transferts en masse.

```powershell
# Depuis un .zip exporté (le cas normal). Pointe direct sur le .zip, ça l'extrait tout seul.
py scripts/import_claude_sessions.py "<chemin>\sessions-export.zip"

# Aperçu sans rien écrire (montre les dossiers cibles + le remap auto vers CE PC)
py scripts/import_claude_sessions.py "<chemin>\sessions-export.zip" --dry-run

# Depuis un dossier bundle (non zippé)
py scripts/import_claude_sessions.py "<dossier-bundle>"

# Remap de chemin explicite (si le projet vit ailleurs sur le PC cible)
py scripts/import_claude_sessions.py "<zip>" --remap "Utilisateur=Administrateur"

# Écraser une session déjà présente (sinon elle est skippée = idempotent)
py scripts/import_claude_sessions.py "<zip>" --force
```

## 🧭 Le remap (le cœur du truc)

- **PC → PC, username différent** (cas normal) : **aucun flag**. `--auto-user` (ON par défaut)
  remappe le segment `\Users\<ancien>\` (ou `/Users/`, `/home/`) vers l'utilisateur courant.
  Ex : un export fait sous `Utilisateur` s'importe sous `Administrateur` automatiquement.
- **Même PC (relancer ici, ré-injection à l'identique)** : ajouter **`--no-auto-user`** pour un
  mapping EXACT (les sessions retombent sur leurs dossiers existants → toutes **skippées** =
  déjà là = resumables, zéro doublon). C'est ce qu'on a utilisé pour le test.
- **Cas spécial** (drive/chemin différent) : `--remap "ANCIEN=NOUVEAU"` (répétable).

## ▶️ Relancer une session après import

```powershell
cd "<dossier du projet>"
claude --resume <sessionId>
```

- `REPRISE-IMPORT.md` (écrit à côté du .zip) liste les commandes **déjà remappées**, par projet.
- ⚠️ Le **projet doit exister** au bon chemin sur ce PC (git clone / même arborescence) : le
  script ne pose que les `.jsonl`, il ne recrée pas les projets.

## 🔒 Garde-fous

- **Idempotent** : relancer ne duplique rien (session déjà présente = skip, sauf `--force`).
- **Aucune écriture en `--dry-run`** (juste l'aperçu).
- Session sans `cwd` lisible → ignorée (comptée `sans cwd`), jamais déposée au hasard.

## 🅰️ Mode A — pop natif dans la sidebar (À VENIR, pas encore construit)

Faire **apparaître (« pop »)** la session dans la sidebar Claude Desktop + reprise native. La
sidebar n'est PAS pilotée par les `.jsonl` mais par un store séparé
(`%APPDATA%\Claude\claude-code-sessions\<fenêtre>\local_*.json`). Donc Mode A devra, en plus de
copier le `.jsonl`, **recréer l'entrée `local_*.json`** (sessionId + cliSessionId + cwd remappé +
titre) — l'export capture déjà ces métadonnées (manifest sidebar). ⚠️ écrit dans le store de CD
pendant qu'il tourne → à tester live + probable redémarrage de CD pour rafraîchir la liste.
**Décision Florent 2026-06-20 : on fait Mode B d'abord, Mode A ensuite.**

## ✅ Validé

Round-trip Mode B prouvé sur données réelles (2026-06-20) : export 117 sessions → `.zip` (~157 Mo)
→ `read_claude_session.py` liste les 117 (titres sidebar) + ressort un transcript complet par
titre/id. Côté copie : import sur le `.zip` → 117 mappées vers les bons dossiers (13 projets).
🧪 Reste à confirmer sur un **2e PC réel** : Claude reprend bien le fil depuis le transcript lu
(Mode B) ; et plus tard le pop natif (Mode A).

**Cross-comptes, même PC — PROUVÉ live 2026-07-25.** Florent nomme une session ouverte sur un
**autre compte** (« la session quotas »), sans capture, sans export préalable : `--sidebar` (avec
`py -3.12`) la sort du store en quelques secondes → chip Mode B sur son `.jsonl` local. **Aucun
export n'avait été fait au préalable et ça marche quand même** — la nuance du § Multi-comptes de
`/claude-sessions-export` (« protocole export-avant OBLIGATOIRE ») vaut pour l'**affichage**, pas
pour la **retrouvabilité** : le disque garde tout, le store aussi.
🧪 À confirmer : que ça tienne quand le compte d'origine a été **résilié** (pas seulement quitté).

## Sources canoniques (routing)

- Compétence sœur (produit le .zip) : **`/claude-sessions-export`**
- Script : `scripts/import_claude_sessions.py` (`import_bundle()`)
- Bouton équivalent dans l'app : Réglages › Confidentialité › « Transférer mes sessions »
  (skill `/claude-sessions-export` § « Bouton SaaS dans l'app »)
- Encodage `cwd` + doctrine : `/claude-sessions-export` (§ Réinjecter / À NE PAS CONFONDRE DS-CONV-004)
