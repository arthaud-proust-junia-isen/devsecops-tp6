# TP6 : monitoring d'une API FastAPI avec Prometheus et Grafana

Le rendu du TP (captures, analyse du dashboard, réponses aux questions) est dans [RAPPORT.md](RAPPORT.md).

## Lancer le projet

```bash
podman-compose up -d --build
```

| Service    | URL                                   |
| ---------- | ------------------------------------- |
| FastAPI    | http://localhost:8000                 |
| Prometheus | http://localhost:9090                 |
| Grafana    | http://localhost:3000 (admin / admin) |

Le dashboard « FastAPI Monitoring » est créé automatiquement au démarrage de Grafana.
