# TP6 : monitoring d'une API FastAPI avec Prometheus et Grafana

Une petite API CRUD en FastAPI expose ses métriques sur `/metrics`. Prometheus les récupère toutes les 15 secondes et Grafana les affiche dans un dashboard.

```
Utilisateur → FastAPI → /metrics → Prometheus → Grafana
```

## Lancer la stack

```bash
docker compose up -d --build
```

| Service    | URL                           |
| ---------- | ----------------------------- |
| FastAPI    | http://localhost:8000         |
| Métriques  | http://localhost:8000/metrics |
| Prometheus | http://localhost:9090         |
| Grafana    | http://localhost:3000 (admin / admin) |

La datasource Prometheus et le dashboard « FastAPI Monitoring » sont provisionnés au démarrage de Grafana (dossier `grafana/provisioning`), il n'y a rien à configurer à la main.

## Endpoints

| Méthode | Endpoint      |
| ------- | ------------- |
| GET     | `/`           |
| POST    | `/items`      |
| GET     | `/items/{id}` |
| PUT     | `/items/{id}` |
| DELETE  | `/items/{id}` |
| GET     | `/metrics`    |

La collection Postman `fastapi-collection.json` contient une requête pour chacun.

## Générer du trafic

Le dashboard reste vide tant que personne n'appelle l'API. Une boucle curl suffit :

```bash
for i in $(seq 1 200); do
  curl -s -X POST localhost:8000/items -H "Content-Type: application/json" -d '{"name":"Test Item"}' >/dev/null
  curl -s localhost:8000/items/$i >/dev/null
  curl -s localhost:8000/items/99999 >/dev/null  # 404
done
```

Pour vérifier que Prometheus scrape bien l'API, taper `http_requests_total` dans http://localhost:9090. Des séries doivent apparaître avec les labels `method`, `path` et `status`.

## Dashboard

| Panel                  | Requête PromQL |
| ---------------------- | -------------- |
| Request rate           | `sum(rate(http_requests_total[1m])) by (method, path)` |
| Temps de réponse moyen | `rate(http_request_duration_seconds_sum[1m]) / rate(http_request_duration_seconds_count[1m])` |
| Latence P95            | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` |
| Mémoire                | `process_resident_memory_bytes{job="fastapi-app"}` |
| CPU                    | `rate(process_cpu_seconds_total{job="fastapi-app"}[1m]) * 100` |
| Taux d'erreurs 5xx     | `sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))` |

Mémoire et CPU sont filtrés sur `job="fastapi-app"` parce que Prometheus expose lui aussi des métriques `process_*`. Sans filtre, les deux courbes se superposent.

L'API ne renvoie aucune 5xx en fonctionnement normal, donc le taux d'erreurs reste à 0. Les 404 de la boucle ci-dessus sont des erreurs client et ne comptent pas.

## Écarts avec les consignes

- Le code fourni normalisait les chemins avec `match.name == "match"`. Starlette renvoie `Match.FULL`, la condition n'était donc jamais vraie et chaque id créait son propre label (`/items/1`, `/items/2`…). C'est corrigé en comparant à `"FULL"`.
- `GET /items/{id}` renvoie une vraie 404 au lieu d'un 200 avec `{"error": ...}`, sinon les métriques comptent un succès.
- Le compose build l'API depuis le Dockerfile du dépôt au lieu de tirer l'image `rhosrow/fastapi:latest`.

## Questions de réflexion

**1. Pourquoi utiliser `rate()` pour les counters ?**

Un counter ne fait que monter depuis le démarrage du process. Sa valeur brute dit combien de requêtes ont été servies depuis le lancement, ce qui n'aide pas à savoir ce qui se passe maintenant. `rate()` calcule la vitesse d'augmentation par seconde sur la fenêtre choisie, et gère les remises à zéro quand le conteneur redémarre.

**2. Quelle est la différence entre moyenne et P95 ?**

La moyenne additionne toutes les durées et divise par le nombre de requêtes. Le P95 est la durée sous laquelle se trouvent 95 % des requêtes. Avec 95 requêtes à 10 ms et 5 à 2 s, la moyenne tombe à environ 110 ms, alors que 5 % des utilisateurs attendent 2 secondes.

**3. Pourquoi le P95 est-il plus important en production ?**

La moyenne lisse les requêtes lentes et peut rester correcte pendant qu'une partie des utilisateurs subit des temps de réponse mauvais. Le P95 montre ce que vivent les cas lents, c'est donc lui qu'on surveille et sur lequel on fixe les SLO et les alertes. Sur un service très sollicité, 5 % représente beaucoup de monde.

**4. Pourquoi diviser `_sum` par `_count` pour la moyenne ?**

L'histogramme expose `_sum`, le total des durées observées, et `_count`, le nombre d'observations. Le total divisé par le nombre donne la durée moyenne. On applique `rate()` aux deux avant de diviser pour obtenir la moyenne sur la dernière minute plutôt que depuis le démarrage.
