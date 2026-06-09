# CV Tailor

Application web pour adapter automatiquement un CV à une description de poste, en préservant la mise en page du document original.

## Fonctionnalités

- Upload CV en **DOCX** (recommandé) ou **PDF**
- Adaptation intelligente via **OpenAI**, **Groq** ou **Claude** selon la job description
- **Choix du provider LLM** et du modèle depuis l'interface
- **Préservation de la structure** DOCX (styles, paragraphes, formatage des runs)
- Interface **bilingue FR/EN**
- **Configuration visible du prompt** IA (system + user prompt)
- Sauvegarde et réinitialisation des prompts
- Téléchargement du CV adapté en DOCX

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.12, FastAPI |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| IA | OpenAI, Groq ou Claude (Anthropic) |
| Documents | python-docx, PyMuPDF |

## Prérequis

- Python 3.12+
- Node.js 20+
- Clé API pour au moins un provider : OpenAI, Groq et/ou Claude

## Installation rapide

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Éditez `.env` et ajoutez vos clés API :

```
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_LLM_PROVIDER=openai
```

Seule la clé du provider que vous utilisez est requise.

Lancez le serveur :

```bash
uvicorn app.main:app --reload --port 8000
```

API docs : http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Application : http://localhost:3000

## Docker

```bash
# Créez un fichier .env à la racine avec OPENAI_API_KEY
echo OPENAI_API_KEY=sk-votre-cle > .env

docker compose up --build
```

## Configuration du prompt

Les prompts par défaut sont dans `backend/prompts/default_prompts.json`.

Variables disponibles :
- `{job_description}` — description du poste saisie par l'utilisateur
- `{cv_paragraphs}` — contenu structuré du CV (par paragraphe avec ID)
- `{output_language}` — langue de sortie (French / English)

L'utilisateur peut modifier les prompts depuis l'interface web. Les modifications sont persistées dans `default_prompts.json`. Le fichier `default_prompts.template.json` sert de modèle pour la réinitialisation.

## Préservation de la structure CV

### DOCX (recommandé)
L'application modifie le texte **paragraphe par paragraphe** en conservant :
- Les styles de paragraphe (titres, corps de texte)
- Le formatage des runs (gras, italique, police)
- L'ordre et la structure des sections

Seuls les paragraphes identifiés par l'IA comme modifiables sont mis à jour.

### PDF
Le PDF est lu pour en extraire le texte. Le résultat est exporté en DOCX avec une mise en page simplifiée. **Pour une préservation optimale, utilisez DOCX.**

## Structure du projet

```
cv-tailor/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # Endpoints REST
│   │   ├── services/
│   │   │   ├── docx_processor.py  # Extraction/modification DOCX
│   │   │   ├── pdf_processor.py   # Extraction PDF
│   │   │   ├── llm_service.py     # Appels OpenAI
│   │   │   ├── cv_tailor.py       # Orchestration
│   │   │   └── prompt_service.py  # Gestion des prompts
│   │   └── main.py
│   └── prompts/
│       ├── default_prompts.json
│       └── default_prompts.template.json
├── frontend/
│   └── src/
│       ├── app/page.tsx           # Page principale
│       ├── components/            # Upload, PromptEditor, Result
│       └── i18n/                  # Traductions FR/EN
└── docker-compose.yml
```

## API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/health` | Statut du service |
| GET | `/api/prompts` | Lire les prompts |
| PUT | `/api/prompts` | Sauvegarder les prompts |
| POST | `/api/prompts/reset` | Réinitialiser aux prompts par défaut |
| GET | `/api/llm/providers` | Liste des providers LLM disponibles |
| POST | `/api/tailor` | Adapter un CV (multipart: file, job_description, output_language, llm_provider, llm_model) |
| GET | `/api/download/{filename}` | Télécharger le CV adapté |

## Licence

MIT
