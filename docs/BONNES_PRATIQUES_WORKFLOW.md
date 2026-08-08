# Bonnes pratiques workflows OpenFox — Drafter & rédaction longue

Issues des corrections appliquées à Drafter4 (juillet 2026).

---

## 1. Agents et outils d'écriture

**L'`agentId` détermine les outils disponibles.** Tous les agents n'ont pas les mêmes capacités.

- `agentId: "planner"` → **ne peut pas écrire** de fichiers. Utile pour définir des critères dans `session_metadata` uniquement.
- `agentId: "builder"` → **peut écrire** des fichiers. Utiliser pour toutes les étapes qui créent/modifient des fichiers `.md`.

**Règle** : si une étape doit écrire sur le disque, utiliser `"agentId": "builder"`.

---

## 2. Cache MCP (Zotero, SearXNG, etc.)

OpenFox découvre les outils des serveurs MCP au démarrage et les stocke dans `cachedTools`.

**Problème** : la découverte est parfois incomplète. Exemple : zotero-mcp expose ~15 outils mais seulement 3 étaient dans le cache.

**Solution** :
1. Vider `cachedTools: []` dans `config.json` pour le serveur concerné
2. Redémarrer OpenFox → les outils sont redécouverts intégralement

**Vérification** : vérifier que `cachedTools` contient bien tous les outils attendus après redémarrage.

---

## 3. Saturation du contexte

Quand un workflow boucle (s3 → s3b → s3), le contexte du sous-agent s'accumule à chaque itération. Après 3-4 sections, le modèle atteint ses limites et crashe (LLM stream error vide).

### Solution : mémoire externe (fichiers)

Remplacer la mémoire de conversation par des fichiers lus à chaque appel :

| Fichier | Rôle | Créé par | Mis à jour par |
|---------|------|----------|----------------|
| `_progress.md` | État d'avancement (sections [ ] / [x]) | s1 (Planner) | s3 (Builder) |
| `GLOSSAIRE.md` | Termes techniques partagés | s1 (Planner) | s3 (Builder) |
| `PLAN.md` | Structure complète | s1 (Planner) | — |
| `BIBLIOGRAPHIE.md` | Sources Citeproc | s2b (Bibliographe) | — |

**Principe** : à chaque appel, le Builder lit `_progress.md`, trouve la première section `[ ]`, l'écrit, et met à jour le fichier. Le contexte de conversation peut être ignoré — la source de vérité est sur le disque.

**Bénéfices** :
- Pas de saturation (contexte frais à chaque itération)
- Reprise après crash (le fichier `_progress.md` dit exactement où reprendre)
- Pas de dérive (le modèle ne peut pas oublier ce qui a été fait)

---

## 4. Anti-dérive code

Les modèles (en particulier qwen3.6) ont tendance à écrire des scripts Python pour générer du texte quand la tâche semble trop longue. C'est inefficace et in vérifiable.

### Ce qu'il faut dans le prompt

```
=== INTERDICTION ABSOLUE DE CODE ===
- NE JAMAIS ecrire de Python, JavaScript, batch, PowerShell
- NE JAMAIS appeler bash, cmd, subprocess, exec
- NE JAMAIS creer de fichier .py, .js, .sh, .bat, .ps1, .tmp
- ECRIS LE TEXTE DIRECTEMENT en Markdown

POURQUOI LE PYTHON EST INTERDIT :
- Inefficace : les tokens du code devraient être du texte
- Inverifiable : le Verificateur ne peut pas exécuter de script
- Qualité inférieure : un script génère du texte répétitif
```

### Point critique : donner une alternative

Ne pas juste interdire — proposer un mécanisme de contournement légitime :

```
SI LA TACHE EST TROP LONGUE :
- Ecris le début, step_done(), la suite sera reprise
- C'est le mécanisme normal du workflow
```

---

## 5. Taille des sections (anti-crash)

Le modèle qwen3.6 (36B MoE, Q4) crashe sur des générations longues (>3000 mots).

**Règle empirique** : ne pas dépasser **5-10 paragraphes** (800-1500 mots) par génération.

Structure recommandée :
- 1 section de PLAN.md par appel du Builder
- Si une section est trop longue : plusieurs appels (le modèle écrit la moitié, `step_done()`, continue au prochain passage)
- Ne jamais exiger "5000 mots par chapitre" comme contrainte de sortie — c'est la somme des sections, pas une génération unique

---

## 6. Cohérence des noms de fichiers

Le modèle peut générer des noms de fichiers différents de ceux attendus par le workflow.

| Attendu (workflow) | Généré par le modèle | Problème |
|---|---|---|
| `chapitre_01.md` | `Chapitre_1.md` | Casse + padding zéro |
| `chapitre_01.md` | `chapitre1.md` | Pas de séparateur |
| `_research_notes.md` | `_research_notes.md` | OK |

**Solution** : spécifier le format exact dans le prompt (ex: `chapitre_01.md` avec zéro padding). Le vérificateur doit normaliser les noms avant de décider qu'un fichier manque.

---

## 7. Alignement Builder ↔ Verifier

Le vérificateur (s3b) et le Builder (s3) doivent utiliser la **même source de vérité**.

**Mauvais** : le Verifier dit "30 paragraphes minimum" pendant que le Builder écrit section par section (5-10 paragraphes). Ils ne parlent pas du même objet.

**Bon** : les deux lisent `_progress.md`. Le Verifier vérifie juste si toutes les sections sont `[x]`. Le Builder écrit une section à la fois.

---

## 8. Séquence de démarrage recommandée

1. Vider `cachedTools` des serveurs MCP dans `config.json`
2. Redémarrer OpenFox
3. Lancer le workflow
4. Vérifier que la première étape (s1) écrit bien `PLAN.md` + `_progress.md` + `GLOSSAIRE.md`
5. Surveiller les logs : si `LLM stream error {}` → modèle crashe → réduire la taille des sections ou changer de modèle

---

## 9. Modèles recommandés pour la rédaction

| Modèle | Taille | VRAM | Usage |
|--------|--------|------|-------|
| qwen3.6:latest | 36B MoE Q4 | ~16GB | Bon mais crashe sur longues générations |
| mistral-small3.2:latest | 24B Q4 | ~10GB | Plus stable, outils OK, 131K ctx |
| gemma4:12b | 12B Q4 | ~7GB | Léger, rapide, bons outils |

Pour la rédaction de chapitres, `mistral-small3.2` est un bon compromis : assez puissant pour du texte académique, assez stable pour des générations de 1500 mots.

---

*Document généré le 22 juillet 2026 — tiré des corrections appliquées à Drafter4.*
