# BidWise - Recommendation des appels d'offres publics

Last updated: 2026-06-21

## Objectif

Le module `CALLS_FOR_TENDER` priorise les appels d'offres publics pour un utilisateur qui cherche des marches par region et categorie officielle.

Contrairement aux offres d'emploi, un appel d'offres public ne se traite pas comme une candidature CV. L'utilisateur ne postule pas directement dans BidWise: il consulte le dossier, les lots, les cautions, la deadline et le lien officiel MarchesPublics.

Le systeme produit donc une veille intelligente:

- filtrer les appels d'offres actifs;
- exclure les deadlines passees;
- comparer les preferences utilisateur avec les donnees structurees du marche;
- classer les resultats par priorite explicable.

## Donnees utilisees

Le profil tender utilise uniquement des champs controles:

- regions preferees: champ existant `preferred_locations`;
- categorie et sous-categorie: `profil.tender_preferences.categories`;
- budget maximum de caution: `profil.tender_preferences.max_budget`.

Exemple de profil:

```json
{
  "opportunity_types": ["CALLS_FOR_TENDER"],
  "preferred_locations": ["Tunis"],
  "tender_preferences": {
    "categories": [
      { "category": "Biens", "subcategory": "Materiels roulants" }
    ],
    "max_budget": null
  }
}
```

Le choix categorie/sous-categorie est ferme. L'utilisateur ne saisit pas de texte libre, ce qui reduit les erreurs et rend le scoring stable.

## Filtre d'eligibilite

Avant tout scoring, le moteur ne garde que les appels d'offres encore actionnables:

```python
type_opportunite = "PROJET"
statut = "ACTIVE"
date_limite >= timezone.localdate()
```

La deadline n'est pas un bonus de pertinence. Elle sert a exclure les appels d'offres expires.

## Choix du modele d'embedding

Pour les appels d'offres, BidWise utilise les embeddings deja calcules dans PostgreSQL/pgvector avec:

```text
paraphrase-multilingual-MiniLM-L12-v2
```

Justification:

- les appels d'offres MarchesPublics melangent francais et arabe;
- le modele est multilingue;
- il est plus leger que des grands LLM temps reel;
- il permet une recherche semantique rapide via pgvector;
- les embeddings sont reutilises, donc pas de recalcul lourd a chaque affichage.

Le texte de requete utilisateur est construit automatiquement a partir de la categorie choisie et de synonymes controles par BidWise, par exemple:

```text
Biens Goods Materiels roulants Vehicles vehicules engins camions transport
```

Il n'y a pas de prompt libre utilisateur dans ce moteur.

## Formule de score

Le score final est hybride:

```python
score = 0.45 * semantic_similarity
      + 0.30 * category_match
      + 0.20 * region_match
      + 0.05 * budget_fit
```

### Semantic similarity - 45%

Compare le sens global entre les preferences tender et l'appel d'offres.

### Category match - 30%

Signal metier le plus deterministe:

| Cas | Score |
| --- | ---: |
| Sous-categorie exacte | 1.00 |
| Meme categorie principale seulement | 0.35 |
| Categorie absente cote offre | 0.30 |
| Categorie differente connue | 0.00 |

La valeur `0.35` pour "meme categorie principale" evite de surclasser des offres trop generales. Exemple: `Biens / Materiels informatiques` et `Biens / Materiels roulants` appartiennent toutes les deux a `Biens`, mais ce ne sont pas le meme besoin.

### Region match - 20%

La region est un signal fort pour les marches publics. Le moteur privilegie la region d'execution quand elle existe, puis utilise la ville comme fallback.

### Budget fit - 5%

La caution/budget est un signal faible car il n'est pas toujours renseigne. Il ne doit pas dominer le classement.

## Niveaux de priorite

| Niveau | Seuil |
| --- | ---: |
| Strong priority | score >= 0.60 |
| Watch closely | 0.40 <= score < 0.60 |
| Low priority | score < 0.40 |

Ces seuils ne representent pas une probabilite de gagner le marche. Ils indiquent la priorite de veille selon les preferences declarees.

## Cas de test soutenance - Materiels roulants a Tunis

Profil:

- type: appels d'offres;
- categorie: `Biens`;
- sous-categorie: `Materiels roulants`;
- region: `Tunis`.

Resultat observe:

| Rang | Offre | Acheteur | Score | Justification |
| ---: | --- | --- | ---: | --- |
| 1 | Materiel roulant | Ministere de la Sante Publique | 64% | Sous-categorie exacte + Tunis |
| 2 | Acquisition des moyens de transport | Agence Nationale des Frequences | 62% | Sous-categorie exacte + Tunis |
| 3 | achat voiture de service | Universite de Jendouba | 61% | Sous-categorie exacte + Tunis |
| 4 | Acquisition voitures de service | CPSCL | 61% | Sous-categorie exacte + Tunis |

Detail du premier cas:

- type commande: `Biens / Materiels roulants`;
- region: Tunis;
- procedure: appel d'offres ouvert;
- lots: camions, voitures de service, transport equipe de collecte de sang;
- action: consultation du lien officiel MarchesPublics.

Ce cas est solide pour la demonstration car le lien entre le profil et les resultats est lisible: l'utilisateur cherche du materiel roulant, le moteur remonte des appels d'offres de vehicules et moyens de transport.

## Explication orale courte

> Pour les appels d'offres publics, BidWise ne fait pas un matching CV comme pour les emplois. Le moteur construit une veille intelligente a partir de donnees controlees: region, categorie officielle du marche, sous-categorie et similarite semantique multilingue. Les marches expires sont exclus. Les resultats sont ensuite classes par priorite, avec des raisons explicites comme "Exact tender subcategory aligned" et "Region aligned: Tunis".

## Fichiers principaux

- `backend/ai/tender_recommendation_service.py`
- `backend/ai/tender_categories.py`
- `backend/tests/test_tender_recommendation.py`
- `frontend/src/features/onboarding/steps/StepTenderPreferences.jsx`
- `frontend/src/features/profile/ProfilePage.jsx`
- `frontend/src/features/opportunities/hooks/useOpportunityRecommendations.js`
- `frontend/src/features/opportunities/components/recommendations/ForYouFeed.jsx`

## Limites documentees

- Le moteur ne gere pas le depot de dossier dans BidWise: la soumission reste sur le portail officiel.
- La qualite depend des champs extraits depuis la source MarchesPublics.
- La similarite semantique aide au ranking, mais la categorie officielle reste le signal le plus defendable.
- Les appels d'offres avec categorie manquante restent en revue, mais ne doivent pas etre surclasses sans preuve.

### Garde-fou anti faux-positif

Quand la categorie est absente cote offre ET que la similarite
semantique est faible (< 0.30), le signal region seul ne doit pas
suffire a faire remonter une offre hors sujet. Dans ce cas precis,
le poids de la region est reduit a 30% de sa valeur normale.