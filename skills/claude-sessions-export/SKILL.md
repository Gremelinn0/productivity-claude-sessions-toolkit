---
name: claude-sessions-export
description: >
  SORT les sessions Claude Code locales (`~/.claude/projects/*.jsonl`) hors de la machine ou les INVENTORIE — sans compte actif ni tokens. Trois jobs : (1) filet de sauvegarde avant de changer de compte, (2) index Markdown de toutes les sessions, (3) bundle `.zip` pour un AUTRE PC. ⚠️ N'EST PAS le skill pour RETROUVER ou RELANCER une session sur CE PC (même depuis un autre compte) — ça, aucun export n'est requis, c'est **/claude-sessions-import**. N'est pas non plus réservé au PC-à-PC : la migration entre COMPTES se fait sur le MÊME PC (cf § Règle l'utilisateur). Pour transport via git (petits dépôts), voir /claude-sessions-sync.
  Invoquer pour : sauvegarder avant bascule de compte, transporter vers un autre PC, archiver, ou lister les sessions actives sans wrapup coûteux.
  Triggers : "/claude-sessions-export", "exporter mes sessions", "sauvegarde mes sessions avant de changer de compte", "mes sessions actives", "migration compte Claude", "sauvegarder mes sessions Claude Code", "emmener mes sessions sur l'autre PC", "export sessions JSONL", "sessions en pagaille", "index de toutes mes sessions".
---

# Export / Migration des sessions Claude Code

## 🎯 Objectif (le problème que ça résout)

L'utilisateur a des centaines de sessions Claude Code. Les archiver une par une (wrapup / migration / Notion)
**coûte des tokens** et exige un **abonnement actif**. Or **toutes ses sessions sont déjà en local** :

```
~/.claude/projects/<projet-encodé>/<sessionId>.jsonl   (1 fichier = 1 session)
```

Point clé **non négociable à rappeler** : ces fichiers **ne dépendent PAS du compte Claude connecté**.
Changer de compte sur le même PC = mêmes fichiers accessibles. Donc **les exporter / indexer =
lecture de fichiers locaux, ZÉRO token consommé, pas besoin d'abonnement actif**. C'est l'inverse du
wrapup. Ne jamais proposer un wrapup payant juste pour « retrouver / archiver » des sessions : utiliser
ce skill.

Outil : [`scripts/export_claude_sessions.py`](../../../scripts/export_claude_sessions.py) (autonome, relançable
sur n'importe quel PC après `git pull`, aucun appel réseau).

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
→ **`/claude-sessions-import`**, tout de suite, § 📸 Méthode capture d'écran.
**Aucun export n'est nécessaire — ni maintenant, ni rétroactivement.** Les fichiers de session sont
sur le disque, liés au compte **Windows** et non au compte Claude, et le store des titres est
**partagé entre les comptes**. C'est le cas qu'on rate le plus souvent, en croyant à tort qu'il
faut d'abord avoir exporté.

**B — Elle est sur un AUTRE PC.**
Là, il faut réellement transporter un fichier. Trois gestes, dans l'ordre :
1. **Sur le PC d'origine** → **CE skill** (`/claude-sessions-export`) : il produit un `.zip`.
2. **Copier ce `.zip`** sur une clé USB (ou tout autre transport : dossier partagé, cloud, ou `/claude-sessions-sync` pour les petits dépôts git).
3. **Sur le PC d'arrivée** → `/claude-sessions-import` en pointant le `.zip`.

   La clé USB est **parfaitement légitime ici** — c'est exactement le cas pour lequel elle existe.

**C — Je pars, je veux juste une sauvegarde.**
Bascule de compte, réinstallation, prudence.
→ **CE skill** (`/claude-sessions-export`) seul, § ⚡ Recettes recette 0 ou 1. Zéro token, aucun
abonnement actif requis.
Nuance à dire pour éviter la fausse inquiétude : sur le **même PC**, cet export est une **assurance**,
pas un péage — le cas A fonctionnera de toute façon sans lui. Il devient vraiment indispensable dès
qu'on quitte la machine (cas B) ou qu'on risque de perdre le disque.

> Le principe commun aux trois : **Claude lit la session et reprend le fil.** L'utilisateur ne tape
> aucune commande, aucun identifiant — il dit où il en est, et on s'occupe du reste.

## 🖥️ Règle d'usage — migration entre COMPTES = MÊME PC, jamais de navette USB inter-PC (gravé 2026-07-09)

Cas d'usage réel quand l'utilisateur **change de compte Claude** (abo résilié → nouveau compte) : il **migre
ses sessions d'un compte à l'autre TOUJOURS sur le MÊME PC**. Sur un même PC les `.jsonl` sont sur le
disque, **liés au compte Windows, PAS au compte Claude** → changer de compte = **simple re-login, les
fichiers restent**. **Rien à transférer.**

**Ne JAMAIS lui imposer un transfert `.zip` par clé USB entre ses 2 PC.** L'utilisateur a **accès simultané à
ses 2 PC en bureau à distance** → il ne branche pas de clé sur un PC distant, il fait le switch de compte
**localement sur chaque PC**. Pour du léger (un doc, un prompt), la **navette Ctrl+C / Ctrl+V** entre les
2 bureaux remote suffit — pas de paranoïa, pas d'exports lourds.

**⚠️ TRANCHÉ (vécu réel 2026-07-09) : changer de compte Claude = tu ne REVOIS pas tes sessions.**
La sidebar Claude Desktop se recharge **PAR COMPTE** → le nouveau compte affiche une sidebar **VIDE** des
anciennes sessions. **NE JAMAIS dire « ça s'affichera après login » : c'est faux, la sidebar sort vide.**

> 🔧 **AFFICHAGE ≠ RETROUVABILITÉ — correction du 2026-07-25 (ce bloc sur-promettait).** L'ancienne
> rédaction disait « tu NE retrouves PAS tes sessions » et « le protocole export/revive **n'est PAS
> optionnel** ». **Faux, prouvé live** : l'utilisateur a nommé une session ouverte sur un **autre compte**,
> **aucun export n'avait été fait**, et elle est ressortie en quelques secondes → chip → contexte
> complet rechargé. **Ce qui est vide, c'est la VUE ; le disque, lui, garde tout** — et le **store
> `local_*.json` est PARTAGÉ entre comptes** (la session de l'autre compte y était ; `list_sessions`,
> filtré par compte, ne la voyait pas). ⇒ tranche l'hypothèse **(a)** du § Multi-comptes plus bas.
> **Donc** : l'export d'avant-bascule reste une **assurance recommandée** (si le store se corrompt, si
> on change de PC, si un compte est résilié), **pas** un prérequis à la retrouvabilité. Pour
> **retrouver/relancer** une session sur ce PC — export ou pas — la compétence est
> **`/claude-sessions-import`** (§ capture d'écran), jamais celle-ci.

**Protocole migration inter-COMPTES (même PC), NE PLUS redemander :**
1. **AVANT de changer de compte — export filet, en assurance** (`--flat --zip` vers Downloads, ou
   `--active` depuis le harness). Zéro token, pas besoin d'abo actif. Pas un prérequis à la
   retrouvabilité (cf § PORTE D'ENTRÉE cas A : le disque et le store des titres survivent au
   changement de compte tout seuls) — mais une vraie assurance si le store se corrompt ou si un
   compte est un jour résilié.
2. **Login nouveau compte** → sidebar **vide** (attendu, normal).
3. **Revive** : relancer les sessions en **chips depuis le disque / le bundle** (`read_claude_session.py`
   lit les `.jsonl` déjà locaux → chaque chip recharge son contexte). C'est **LE geste normal**, pas l'exception.
4. **Clé USB / transfert inter-PC = seulement PC↔PC réellement séparés**, jamais pour un changement de
   compte sur la même machine (là tout est déjà sur le disque).

## 🧹 Ménage à CHAQUE export — REMPLACER l'ancien, jamais toucher au reste (règle d'usage gravée 2026-06-22)

À chaque export vers une **destination de transfert** (clé USB, dossier de migration) : faire le ménage
**dans la même passe**. On ne garde qu'**UN** export courant à cet endroit, pas une pile d'anciens.

1. **Lister la destination AVANT** d'écrire/supprimer (inventaire).
2. **Copier** le nouveau zip + le **renommer avec le préfixe `migration-` OBLIGATOIRE** :
   `migration-<scope>_<date>.zip` (ex `migration-mon-projet_2026-06-22.zip`).
   ⚠️ **Sans `migration-` en tête, l'utilisateur NE retrouve PAS ses migrations** — tout export/migration de
   sessions DOIT commencer par `migration-` (verbatim 2026-06-22, NON négociable).
3. **Supprimer UNIQUEMENT l'ancien export** : les artefacts produits par CE skill —
   `migration-*.zip`, `mon-projet_*.zip`, `claude-sessions*.zip`, `REPRISE*.md`, `INDEX-SIDEBAR.md`, `LISEZ-MOI.md`.
   Delete **fichier-par-fichier** (`[System.IO.File]::Delete`), **jamais** `-Recurse`.

> 🛑 **Garde-fou NON négociable** : ne JAMAIS toucher aux autres fichiers/dossiers de la destination.
> La destination contient très probablement des dossiers personnels sans rapport — **intouchables**.
> On supprime le SEUL ancien export identifié par son nom, rien d'autre. C'est une autorisation explicite
> de suppression **strictement limitée aux artefacts de ce skill** (ça lève le défaut archive-first §11
> global UNIQUEMENT pour ce cas précis, sur demande explicite de l'utilisateur).

Formulé par l'utilisateur à l'origine de la règle : *« nettoie bien l'ancien fichier sans supprimer les
bons fichiers, juste l'ancien export, on renomme bien le nouvel export… il faut faire le ménage à chaque
fois… j'ai d'autres dossiers là-dedans, n'y touche pas. »*

## ⚡ Recettes (commandes prêtes)

```powershell
# 0) ⭐⭐ MIGRATION SIMPLE (PC→PC, l'usage courant) : UN seul .zip, dans les TÉLÉCHARGEMENTS.
#    Toujours au même endroit, facile à retrouver. Le script imprime le chemin exact.
py scripts/export_claude_sessions.py --sidebar --flat --zip --out "$env:USERPROFILE\Downloads\claude-sessions"
#    -> %USERPROFILE%\Downloads\claude-sessions.zip   (réinjection sur l'autre PC : /claude-sessions-import)

# 1) ⭐ SIDEBAR (mode recommandé) : RANGEMENT AUTO + .zip propre PAR DÉFAUT.
#    Sort UN dossier par export :  <out>/<année>/<projet>/<date_nom>/<projet>_<date>.zip
#    (le .zip contient jsonl/ bruts + md/ lisibles + INDEX-SIDEBAR.md + REPRISE.md ; bundle temp auto-nettoyé)
py scripts/export_claude_sessions.py --sidebar --out "$env:USERPROFILE\Documents\Migration compte Claude"
py scripts/export_claude_sessions.py --sidebar --project mon-projet --out "<dossier>"      # 1 SEUL dépôt (dossier = son nom)
py scripts/export_claude_sessions.py --sidebar --export-name sidebar-active --out "<dossier>" # suffixe lisible du dossier d'export
py scripts/export_claude_sessions.py --sidebar --dry-run                                      # voir la liste sans rien écrire
py scripts/export_claude_sessions.py --sidebar --include-archived --out "<dossier>"           # inclure les archivées
py scripts/export_claude_sessions.py --sidebar --days 3 --out "<dossier>"                     # actives (focus) des 3 derniers jours
py scripts/export_claude_sessions.py --sidebar --flat --out "<dossier>"                       # ANCIEN comportement : fichiers en vrac dans <dossier> (+ --zip pour zipper)
#    NB : `non-archivé` = sessions ACTIVES/OUVERTES (Claude Desktop auto-archive les vieilles).
#    Tri = `lastFocusedAt` (dernière OUVERTURE dans l'UI = ordre sidebar réel), PAS `lastActivityAt` (faussé par l'auto-sync git).
#    Le .zip se réinjecte sur l'autre PC avec la compétence sœur : /claude-sessions-import

# 1bis) ⭐ SIDEBAR EXACTE (la capture au mot près) : sélection par TITRE/ID via manifest.
#    Le store NE contient PAS le flag épinglé ni l'ordre visible (cf § Multi-comptes) -> le seul moyen
#    100% fidèle à un SCREENSHOT = filtrer les sessionId/cliSessionId voulus dans le manifest, puis :
#    PowerShell : ne garder que les enregistrements dont .cli est dans ta liste -> tools\.sidebar-manifest-sel.json
py scripts/export_claude_sessions.py --sidebar --manifest "tools\.sidebar-manifest-sel.json" --export-name sidebar-active --out "<dossier>"

# 2) INDEX global de TOUTES les sessions (vue d'ensemble tous projets)
py scripts/export_claude_sessions.py
#    -> ~/.claude/sessions-export/INDEX.md

# 3) MIGRATION par récence (FALLBACK si pas de Claude Desktop) — titres = 1er message, pas custom
py scripts/export_claude_sessions.py --active --days 10 --per-project 15 --out "<dossier>"

# 4) Export complet LISIBLE d'un projet (relire sans Claude Code)
py scripts/export_claude_sessions.py --full --project mon-projet
```

### Le mode `--sidebar` (la source de vérité)

C'est LE bon mode : il lit directement le store de la sidebar Claude Desktop
(`%APPDATA%/Claude/claude-code-sessions/<fenêtre>/local_<id>.json`, un fichier par session) qui
contient le **titre exact** (`.title`), le projet (`.cwd`), l'état (`.isArchived`), et surtout le
**lien vers le vrai fichier JSONL via `.cliSessionId`** (= le nom du `.jsonl` dans `~/.claude/projects/`).
Résultat = ta sidebar au mot près, pas une approximation par récence.

> 🔧 **Pont manifest (cas particulier)** : si le process qui lance le script ne peut pas lire `%APPDATA%`
> (ex : Claude Code dans le harness, qui voit `~/.claude` mais pas `~/AppData`), passer par un manifest :
> PowerShell extrait le store → JSON, puis `py ... --sidebar --manifest tools/.sidebar-manifest.json`.
> Le snippet PowerShell d'extraction est dans la section « Pont manifest » plus bas. En usage normal
> (dans ton propre terminal), `--sidebar` seul suffit, pas besoin de manifest.

> ⚠️ **Piège `py` → Python Store** (vu le 2026-06-02) : si `--sidebar` répond « Store introuvable »
> alors que Claude Desktop EST installé, c'est souvent que le lanceur `py` a résolu le shebang vers un
> **Python Microsoft Store** (virtualisé, aveugle à `%APPDATA%`). Le store est bien là (PowerShell le voit),
> ce Python-là non. Fix : forcer un vrai Python —
> `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" scripts/export_claude_sessions.py --sidebar`
> — ou `--manifest`. Le message d'erreur du script le rappelle désormais.

> ℹ️ `--active` reste un **fallback** par récence (dernière activité réelle via `ts_end`, pas le `mtime`
> faussé par l'auto-sync). À n'utiliser que si Claude Desktop n'est pas sur le PC.

## 📂 Ce que produit le mode `--sidebar`

**Par défaut (RANGÉ)** — 1 dossier par export, 1 seul `.zip` propre (rien en vrac) :

```
<dossier de sortie>/
  <année>/<projet>/<date>_<nom>/<projet>_<date>.zip      ex: 2026/mon-projet/2026-06-20_1754_sidebar-active/mon-projet_2026-06-20_1754.zip
```

Le `.zip` contient le bundle complet (le `--export-name` ajoute le suffixe `_<nom>` au dossier daté) :

```
  INDEX-SIDEBAR.md        récap (par projet) = ta sidebar
  REPRISE.md              comment relancer chaque session (commandes prêtes)
  jsonl/<projet>/<id>.jsonl    copies brutes (pour reprendre / cross-PC)
  md/<projet>/<date>_<titre>_<id8>.md   versions lisibles, titre = titre sidebar (Utilisateur ↔ Claude)
```

**Avec `--flat`** — ancien comportement : `INDEX-SIDEBAR.md` + `REPRISE.md` + `jsonl/` + `md/` écrits
directement dans `<dossier de sortie>` (+ `--zip` pour un `<dossier>.zip` frère). À éviter dans un dossier
déjà peuplé (il zipperait le contenu voisin).

## ▶️ Reprendre / relancer une session proprement

Une session se reprend **en local, sans dépendre du compte** :

```powershell
cd "<dossier du projet>"          # ex: cd "C:\Users\<toi>\Projets\mon-projet"
claude --resume <sessionCLI>
```

- Le `sessionCLI` (= `cliSessionId`, le nom du fichier `.jsonl`) est dans `INDEX-SIDEBAR.md` / `REPRISE.md`.
- **Cross-PC** : ne plus copier les `.jsonl` à la main → utiliser le **script d'import** ci-dessous
  (`scripts/import_claude_sessions.py`), qui place chaque session au bon endroit en remappant le chemin.
- `REPRISE.md` liste tout ça, groupé par projet, prêt à copier-coller.

> 🆘 **Débloquer une session MORTE (« contexte plein », plus accessible) — même PC** (vécu 2026-06-21, session « 📖 chat_reader CD — kARAOKE », 9 Mo / 2751 lignes). Le `.jsonl` reste **intact** → le travail n'est PAS perdu. **La voie qui marche, en 30 s = chip Mode B via `/claude-sessions-import`** : spawn UN chip rooté dans le bon dossier (`cwd`), qui **recharge tout le contexte** via `scripts/read_claude_session.py` et reprend le fil. **Zéro terminal, zéro login, zéro `/resume`.** C'est la 1re (et seule) chose à faire pour une session morte sur CE PC.
>
> ⛔ **Pièges PROUVÉS 2026-06-21 — NE PAS y retourner** (j'ai brûlé 1 h dessus) : (1) **`/resume` natif n'est PAS dispo dans Claude Desktop** (réponse « pas disponible ici / erreur ») — il ne marche qu'en CLI terminal pur. (2) **Terminal externe = cul-de-sac auth** : ce `claude.exe` (`%APPDATA%\Claude\claude-code\<v>\`) est **managé par Claude Desktop** (`CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH=1`, vrai jeton frais dans `%APPDATA%\Claude\buddy-tokens.json`). Le `~/.claude/.credentials.json` standalone est **expiré** et les logins terminal **ne le réparent pas** → « autorisation invalide » en boucle, quel que soit le compte. → pour une session morte, **toujours le chip Mode B `/claude-sessions-import`**, jamais le terminal ni `/resume`. Doc humaine miroir : page Notion « 🔁 Relancer mes sessions » § Session plantée.

## ♻️ Réinjecter / réimporter → compétence sœur `/claude-sessions-import`

L'import (réinjecter un `.zip` ou un bundle → `claude --resume` sur ce PC ou un autre, avec remap
auto du username) vit dans sa **propre compétence** : **`/claude-sessions-import`**. En une ligne :

```powershell
py scripts/import_claude_sessions.py "<chemin>\sessions-export.zip"        # PC→PC : remap auto
py scripts/import_claude_sessions.py "<zip>" --no-auto-user                # même PC : mapping exact
```

Détails (remap, dry-run, force, REPRISE) = skill `/claude-sessions-import`.

## 🔧 Pont manifest (si `%APPDATA%` inaccessible au process)

Snippet PowerShell qui extrait le store sidebar → JSON, à utiliser avec `--sidebar --manifest` :

```powershell
$dir = "$env:APPDATA\Claude\claude-code-sessions"
$byId = @{}
foreach ($f in (Get-ChildItem $dir -Recurse -Filter "local_*.json")) {
  try { $j = Get-Content $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json } catch { continue }
  if (-not $j.sessionId) { continue }
  $foc = 0; if ($j.lastFocusedAt)  { $foc  = $j.lastFocusedAt }    # ordre sidebar réel
  $act = 0; if ($j.lastActivityAt) { $act  = $j.lastActivityAt }   # faussé par auto-sync
  $rec = [ordered]@{ sessionId=$j.sessionId; cli=$j.cliSessionId; cwd=$j.cwd; title=$j.title; archived=[bool]$j.isArchived; exempt=[bool]$j.autoArchiveExempt; focused=$foc; last=$act }
  $score = $foc; if ($score -eq 0) { $score = $act }
  $prev = $byId[$j.sessionId]; $pScore = 0; if ($prev) { $pScore = $prev.focused; if ($pScore -eq 0) { $pScore = $prev.last } }
  if (-not $prev -or $score -gt $pScore) { $byId[$j.sessionId] = $rec }
}
$abs = (Join-Path $PWD.Path "tools\.sidebar-manifest.json")
[System.IO.File]::WriteAllText($abs, (@($byId.Values) | ConvertTo-Json -Depth 4), (New-Object System.Text.UTF8Encoding($false)))
py scripts/export_claude_sessions.py --sidebar --manifest "tools\.sidebar-manifest.json" --out "<dossier>"
```

> Pour la **SIDEBAR EXACTE d'un screenshot** (recette 1bis) : après avoir construit `tools\.sidebar-manifest.json`,
> garder seulement les sessions voulues (par titre ou `cli`) dans `tools\.sidebar-manifest-sel.json`, puis exporter
> avec `--manifest "tools\.sidebar-manifest-sel.json"`. C'est la seule méthode 100% fidèle (le store n'a ni flag
> épinglé ni ordre visible, cf § Multi-comptes).

## 🧹 Mieux organiser des sessions « en pagaille »

- `INDEX.md` global = vue d'ensemble (tous projets, triés par récence) → repérer les doublons (mêmes
  chantiers relancés N fois), les sessions mortes, ce qui reste à finir.
- Plusieurs sessions au même titre = reprises successives → garder la plus récente (`ts_end`).
- Les 744 sessions `subagents/` + `wf_*` sont du bruit interne (exclues par défaut) — ne pas les
  exporter sauf besoin de debug.
- Pour archiver un chantier fini : son `.md` lisible + son `.jsonl` suffisent (pas de wrapup payant).

## 🔍 Multi-comptes — TRANCHÉ côté vécu (le comportement pratique)

> ✅ **TRANCHÉ (vécu réel 2026-07-09) : changer de compte = sidebar VIDE, sessions PAS retrouvées.**
> En pratique c'est le comportement de l'hypothèse **(b)** : sous un autre compte on **ne revoit pas** ses
> sessions → le protocole **export-avant / revive-après est OBLIGATOIRE** (cf § Règle migration ci-dessus).
> Le détail technique ci-dessous (fichiers locaux, empreinte de store) reste à confirmer, mais **ne change
> RIEN à la conduite : on ne compte JAMAIS sur l'affichage auto après un changement de compte.**

> ⚠️ **Question ouverte non tranchée.** Avec plusieurs comptes Claude sur la même machine : la sidebar
> d'un projet (mode Code) peut afficher ~15 sessions alors que l'export `--sidebar` en sort beaucoup
> plus (ex 48 non-archivées sur un seul dépôt). **Deux explications possibles, pas encore départagées :**
> (a) les sessions « en trop » sont juste **plus anciennes** (hors de la vue du haut de sa sidebar),
> (b) elles viennent de **ses autres comptes** (le store local mélangerait les comptes).

**Constats techniques établis :**

1. **Pas de flag `isPinned` ni d'ordre de sidebar dans les fichiers** (`local_*.json`). Re-vérifié 2026-06-20 :
   **0/923** occurrence de `isPinned`. Donc `--sidebar` exporte **toutes les non-archivées** (un sur-ensemble sûr),
   pas exactement les ~15 affichées. **Seul moyen 100% fidèle à un screenshot = recette 1bis (manifest filtré
   par titre/`cli`).**
   - ✅ **NOUVEAU 2026-06-20 — `lastFocusedAt` existe** (+ `lastFocusedAt`, `autoArchiveExempt`, `titleSource`
     dans le store). C'est la **dernière OUVERTURE dans l'UI** = bien plus proche de l'ordre sidebar que
     `lastActivityAt` (que l'auto-sync git gonfle). **Le tri par défaut utilise désormais `lastFocusedAt`**
     (`_recency()` dans le script). Ça **ne reproduit pas exactement** la vue (le simple fait de cliquer/scroller
     la sidebar bump `lastFocusedAt`), mais l'ordre est juste.
   - **Penche vers l'explication (a)** : triées par `lastFocusedAt`, les sessions du screenshot remontent en tête
     et les « en trop » ont un focus plus ancien = ce sont surtout des sessions **plus vieilles hors-vue**, pas
     d'autres comptes (à confirmer par le protocole d'empreinte ci-dessous). `autoArchiveExempt` est quasi
     toujours absent (1 cas) → inutilisable comme sélecteur.
2. **Pas de champ « compte » dans les fichiers** (ni `local_*.json`, ni JSONL). Impossible d'étiqueter
   « cette session = compte X » par lecture de fichiers. Piste feature future : lire le compte **affiché
   dans Claude Desktop** (« F · Pro » en bas) via UIA, comme on lit le compte dans Chrome.
3. **« Tout est en local »** = vrai au niveau fichiers (`~/.claude/projects/`, lié au **compte Windows**).
   Mais c'est **ce PC uniquement** — une session faite sur un autre PC n'est ici que si synchronisée (git).

**Protocole de vérification (à dérouler à la prochaine session depuis un autre compte) :**

```powershell
# 1) Sur le compte ACTUEL (produit une empreinte dans account-snapshots/)
py scripts/export_claude_sessions.py --status --label "compte-1" --out "<dossier>"
# 2) Se déconnecter, se reconnecter sur un AUTRE compte Claude dans Claude Desktop, puis :
py scripts/export_claude_sessions.py --status --label "compte-2" --out "<dossier>"
# 3) Comparer les EMPREINTES (champ fingerprint des 2 JSON dans account-snapshots/) :
#    - MEME empreinte  -> le store est PARTAGE (1 seul store local, tous comptes mélangés)
#                         => les sessions « en trop » sont juste plus anciennes (explication a).
#    - empreinte DIFFERENTE -> le store est RECHARGE par compte
#                         => chaque compte a ses sessions (explication b), et --sidebar par compte = correct.
```

Chaque `--status` dépose son empreinte dans `account-snapshots/`. Au prochain run depuis un autre compte
→ refaire `--status`, comparer les deux empreintes, et **trancher (a) ou (b)**.

## 🔧 Paramètres du script

| Flag | Effet |
|------|-------|
| `--sidebar` | ⭐ Lit le store Claude Desktop (titres custom + lien JSONL). Sort **toutes les non-archivées** (sur-ensemble de la sidebar visible — le flag « épinglé » n'est pas dans les fichiers, cf § Multi-comptes) |
| `--include-archived` | Avec `--sidebar` : inclut aussi les sessions archivées |
| `--manifest PATH` | Avec `--sidebar`/`--status` : lit la liste depuis ce JSON au lieu du store `%APPDATA%` (cf Pont manifest) |
| `--status` | Capture une **empreinte** du store (`account-snapshots/`) pour comparer entre comptes Claude (cf § Multi-comptes) |
| `--label TEXTE` | Avec `--status` : étiquette du compte au moment de la capture (ex `compte-F-pro`) |
| (aucun) | Index global `INDEX.md` de toutes les vraies sessions |
| `--active` | Fallback par récence (si pas de Claude Desktop) : jsonl + md + INDEX-ACTIVE + REPRISE |
| `--days N` | Fenêtre de récence. `--sidebar` : par `lastFocusedAt` (ordre sidebar). `--active` : par `ts_end`, défaut 7 |
| `--per-project N` | Garde les N sessions les plus récentes de chaque projet |
| `--limit N` | Cap global des N sessions les plus récentes (marche aussi avec `--sidebar`) |
| `--export-name TXT` | `--sidebar`/`--active` rangés : suffixe lisible du dossier d'export daté (ex `sidebar-active`) |
| `--flat` | `--sidebar`/`--active` : **désactive** le rangement auto → écrit en vrac dans `--out` (ancien comportement). Combine avec `--zip` |
| `--zip` | Avec `--flat` : compresse en `<out>.zip`. **Sans `--flat`, inutile** (le rangement auto zippe déjà) |
| `--dry-run` | Compte + liste sans rien écrire (calibrage) |
| `--full` | Génère un `.md` lisible par session |
| `--project TEXTE` | Ne traite que les projets dont le chemin contient ce texte |
| `--include-subagents` | Inclut les sessions internes subagents/workflows |
| `--out CHEMIN` | Sortie. Par défaut = **racine du rangement** `<out>/<année>/<projet>/<export>/` (sauf `--flat`). Défaut `~/.claude/sessions-export/` |

## Sources canoniques (routing)

- Script export : `scripts/export_claude_sessions.py`
- Script import / réinjection : `scripts/import_claude_sessions.py` (testé : remap, dédoublonnage, `--force`, auto-user, encodage worktree)
- Retrouver / relancer une session sur CE PC (aucun export requis) : `/claude-sessions-import`
