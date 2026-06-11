# CV Tailor

Application web pour adapter automatiquement un CV à une description de poste, en préservant la mise en page du document original.

## Fonctionnalités

- Upload CV **DOCX** (recommandé) ou **PDF**
- **Analyse sur demande** : score d'adéquation + mots-clés présents/absents + conseils
- Adaptation IA (**léger / fort / ATS**) via Groq, OpenAI ou Claude
- **Validation ligne par ligne** avec édition manuelle avant export
- **Relance IA** sur les lignes décochées
- Comparaison **avant / après** + export DOCX/PDF après validation
- **Kit candidature** (lettre, messages, checklist) basé sur le **CV adapté**
- Export lettre en **DOCX + PDF**
- Historique local des candidatures
- Interface **bilingue FR/EN** (locale mémorisée)

## Démarrage rapide (Windows)

```powershell
.\start.ps1
```

- Frontend : http://localhost:3000
- Backend : http://localhost:8001
- API docs : http://localhost:8001/docs

## Installation manuelle

### Backend (port **8001**)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

`.env` minimal :

```
GROQ_API_KEY=gsk_votre_cle
DEFAULT_LLM_PROVIDER=groq
```

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Le proxy `/api-backend` pointe vers `http://127.0.0.1:8001` (voir `next.config.js`).

## Docker

```bash
docker compose up --build
```

- Backend : http://localhost:8001
- Frontend : http://localhost:3000

## Déploiement Vercel (frontend)

Le frontend Next.js se déploie sur **Vercel** ; le backend FastAPI doit être hébergé à part (Render, Railway, Fly.io, VPS).

### 1. Backend (ex. Render)

```bash
# Blueprint Render à la racine du dépôt
render.yaml
```

1. Créer un **Web Service** Docker depuis `backend/Dockerfile` (ou importer `render.yaml`).
2. Variables d'environnement : `GROQ_API_KEY`, `DEFAULT_LLM_PROVIDER=groq`, etc.
3. **CORS** : `CORS_ORIGINS=https://votre-app.vercel.app` (virgule si plusieurs domaines).
4. Noter l'URL publique, ex. `https://cv-tailor-api.onrender.com`.

### 2. Frontend (Vercel)

1. Importer le dépôt GitHub sur [vercel.com](https://vercel.com).
2. **Root Directory** : `frontend`
3. Framework : Next.js (détecté automatiquement)
4. Variables d'environnement (voir `frontend/.env.vercel.example`) :

| Variable | Exemple | Rôle |
|----------|---------|------|
| `NEXT_PUBLIC_API_URL` | `https://cv-tailor-api.onrender.com` | Appels API directs (recommandé : uploads + longues requêtes IA) |
| `BACKEND_URL` | `https://cv-tailor-api.onrender.com` | Proxy `/api-backend` (fallback) |

5. Déployer. La version affichée (`v1.32`) provient du sujet du commit (`VERCEL_GIT_COMMIT_MESSAGE`).

### Architecture production

```
Navigateur → Vercel (Next.js)
              ├─ NEXT_PUBLIC_API_URL → Backend (Render)
              └─ /api-backend/*      → BACKEND_URL (rewrite)
```

## Flux utilisateur

1. Charger le CV + coller l'offre
2. **Analyser l'adéquation** (score + mots-clés)
3. Choisir intensité (léger / fort / ATS) → **Adapter mon CV**
4. Valider / éditer chaque ligne → **Générer le CV validé**
5. Télécharger DOCX/PDF — kit candidature utilise le CV adapté

## API principale

| Endpoint | Description |
|----------|-------------|
| `POST /api/preview` | Upload + extraction CV |
| `POST /api/analyze` | Score + mots-clés + conseils |
| `POST /api/tailor` | Propositions de modifications (sans fichier) |
| `POST /api/tailor/apply` | Génère DOCX/PDF validé |
| `POST /api/tailor/retry` | Relance les lignes rejetées |
| `POST /api/application/kit` | Kit candidature |
| `POST /api/application/cover-letter/docx` | Export lettre |

## Tests & CI

```bash
cd backend
pip install pytest
pytest tests/ -q

cd ../frontend
npm run build
```

GitHub Actions : `.github/workflows/ci.yml`

## Confidentialité & multi-utilisateur

- **Session isolée** : cookie HttpOnly `cv_tailor_sid` — chaque visiteur a son propre CV (`stored_cv/{session}/`) et ses exports (`outputs/{session}/`).
- **Téléchargements** : un utilisateur ne peut pas télécharger les fichiers d'un autre.
- **Prompts IA** : écriture désactivée en production (`ALLOW_PROMPT_WRITES=false`) ; admin via `X-Admin-Token`.
- **Rate limit** : par session + endpoint (60 req/min par défaut).
- Le CV et les offres sont envoyés au fournisseur IA configuré. Nettoyage auto des données de session après 48 h.

Test multi-utilisateur : `python backend/scripts/concurrency_probe.py` (backend démarré).

## Stack

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, FastAPI |
| Frontend | Next.js 15, TypeScript, Tailwind |
| IA | Groq (défaut), OpenAI, Claude |
| Documents | python-docx, PyMuPDF |
