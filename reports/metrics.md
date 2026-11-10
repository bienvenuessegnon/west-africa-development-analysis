# Résultats de modélisation — cible : espérance de vie à la naissance (années)

Variables : log(PIB par habitant), Accès à l'électricité, Eau potable de base, Fécondité, Population urbaine, Internet.
391 observations pays-année complètes (16 pays, 2000–2024).

## 0. Sélection sur validation (apprentissage 2000–2012, validation 2013–2016)

| modele | MAE | RMSE | R2 |
| --- | --- | --- | --- |
| Référence : dernière valeur connue | 0.931 | 1.136 | 0.948 |
| Référence : tendance par pays | 0.650 | 0.819 | 0.973 |
| Régression ridge | 3.274 | 4.279 | 0.263 |
| Forêt aléatoire | 2.248 | 3.080 | 0.618 |
| Tendance par pays + correction ridge | 0.626 | 0.797 | 0.974 |

## 1. Split temporel : apprentissage 2000–2016 (263 lignes), test 2017–2024 (128 lignes)

| modele | MAE | RMSE | R2 |
| --- | --- | --- | --- |
| Référence : dernière valeur connue | 1.367 | 1.697 | 0.872 |
| Référence : tendance par pays | 1.043 | 1.398 | 0.913 |
| Régression ridge | 3.700 | 4.394 | 0.140 |
| Forêt aléatoire | 2.565 | 3.421 | 0.479 |
| Tendance par pays + correction ridge | 0.993 | 1.342 | 0.920 |

## 2. Pays jamais vu : leave-one-country-out (16 plis)

| modele | MAE | RMSE | R2 |
| --- | --- | --- | --- |
| Référence : moyenne des autres pays (même année) | 4.192 | 5.489 | 0.123 |
| Régression ridge | 4.220 | 5.432 | 0.142 |
| Forêt aléatoire | 4.572 | 6.245 | -0.135 |

## Diagnostic du modèle hybride (appris sur 2000–2016, permutation sur le test 2017–2024)

| variable | coef_correction_standardise | importance_permutation_mae |
| --- | --- | --- |
| Internet | -0.033 | 0.014 |
| Accès à l'électricité | -0.016 | 0.002 |
| Fécondité | 0.012 | -0.000 |
| Population urbaine | -0.009 | -0.001 |
| Eau potable de base | 0.024 | -0.002 |
| log(PIB par habitant) | 0.040 | -0.002 |

MAE/RMSE en années d'espérance de vie (plus bas = mieux). Corrélation ≠ causalité.
