# ParkCheaper 🚗💨

Outil d'optimisation tarifaire et d'achat automatique séquentiel de stationnement sur **PayByPhone**.

---

## Deux modes d'utilisation : CLI ou Interface Graphique

Le projet peut être utilisé soit **en ligne de commande (CLI)**, soit via l'**interface graphique (React / Tauri)**.

---

## 1. Utilisation en CLI (`cli.py`)

Toutes les fonctionnalités sont accessibles directement depuis votre terminal :

### Vérifier l'état du compte et la session active
```powershell
python cli.py status --zone 94802
```

### Calculer la combinaison optimale
```powershell
# Par plage horaire
python cli.py optimize --zone 94802 --start 14:00 --end 17:30

# Ou par durée totale en minutes
python cli.py optimize --zone 94802 --duration 210
```

### Acheter un ticket unique immédiatement
```powershell
python cli.py buy --zone 94802 --duration 15
```

### Lancer l'ordonnanceur automatique en console
```powershell
python cli.py schedule --zone 94802 --tickets 30,90,90
```
*(Interruption propre possible à tout moment avec `Ctrl+C`)*.

---

## 2. Utilisation avec l'Interface Graphique (React)

Une interface moderne, sobre et fonctionnelle (conçue sans code visuel générique d'IA, dans le style des outils comme Linear/Raycast).

### Lancer en un clic (PowerShell)
```powershell
.\start.ps1
```

### Ou dans deux terminaux séparés
**Terminal 1 (Backend FastAPI) :**
```powershell
python -m uvicorn server.app:app --port 8000 --reload
```
*Documentation Swagger disponible sur [http://localhost:8000/docs](http://localhost:8000/docs)*

**Terminal 2 (Frontend React) :**
```powershell
cd frontend
npm run dev
```
*Application accessible sur [http://localhost:5173](http://localhost:5173)*

---

## Structure du projet

- `cli.py` : Outil autonome en ligne de commande (compatible Tauri sidecar).
- `internal/` : Moteur métier (authentification, calculs de devis, programmation dynamique, checkout 3DS).
- `server/` : Backend API REST & WebSocket avec **FastAPI**.
  - `server/scheduler.py` : Ordonnanceur non bloquant en arrière-plan.
  - `server/app.py` : Application FastAPI avec client partagé en mémoire (`lifespan`).
- `frontend/` : Application Web **React** sobre (Vite + Tailwind CSS v4).
