# 🧠 Knowledge Hub AI

Knowledge Hub AI is a modern, premium, enterprise-ready multi-tenant AI Knowledge Management Platform where users can create secure folders/workspaces, upload rich documents, and chat with their isolated knowledge bases using a high-fidelity Retrieval-Augmented Generation (RAG) pipeline.

Built to run with low-latency and maximum resource efficiency, this application uses a lightweight **single-mode architecture**: SQLite for transactional state, local in-process ThreadPool workers for document chunking, and SentenceTransformers for fast embeddings.

---

## ✨ Features
* 📁 **Isolated Workspaces (Folders)**: Keep knowledge bases completely segmented. Each folder acts as its own secure collection.
* 🤖 **Precision Multi-Tenant RAG**: Retrieve text grounded ONLY in the current workspace's documents to prevent hallucination.
* ⚡ **Ultra-Fast Inferences**: Native support for Groq (default), OpenAI, Anthropic, and Hugging Face Hub inference endpoints.
* 💬 **Streaming Chat & Citation Memory**: Follow-up questions, persistent context, and precise character-matched citation mapping back to sources.
* 🔒 **Premium Authentication & Google OAuth**: Standard JWT credentials alongside secure Google single sign-on.
* 📊 **Lightweight Custom Observability & Evaluation**: Real-time DB metrics, timeline volume, latency tracking, and LLM-as-a-Judge RAG evaluation (Faithfulness, Precision, Relevancy).
* 🎨 **Breathtaking Design & UX/UI**: Immersive dark mode, custom violet glassmorphic panels, shimmering loading states, responsive dashboard charts, and elegant micro-animations.

---

## 🛠️ Technology Stack

### Frontend (SPA Client)
* **Framework**: React.js 18 + Vite (TypeScript)
* **Routing**: React Router v6
* **State Management**: Zustand
* **Styling**: Vanilla CSS (TailwindCSS framework classes, HSL custom palettes, Glassmorphic panels, animations)
* **Data Visualization**: Recharts (Interactive usage and system health metrics)

### Backend (Robust API)
* **Framework**: FastAPI (Asynchronous Python 3.10)
* **ORM / Database**: SQLAlchemy (Async queries with SQLite `aiosqlite` adapter)
* **Vector Store**: ChromaDB (Folder-isolated collections)
* **Embeddings**: SentenceTransformers `all-MiniLM-L6-v2` (Fast, standard size, optimized CPU footprint)
* **RAG Retrieval**: Hybrid retrieval (Dense Chroma Vector Retrieval + Sparse BM25 + Cross-Encoder reranking)
* **Security**: JWT tokens, bcrypt hash validation, CORS policies, client-IP rate-limiting.
* **Safety Guardrails**: Input injection detection & toxic content filtering.

---

## 🏗️ Folder Structure

```text
├── backend/
│   ├── app/
│   │   ├── api/                 # Endpoint routers (v1 auth, folders, docs, chat, analytics)
│   │   ├── core/                # Middleware, custom exceptions, JWT security
│   │   ├── db/                  # Base engines, models (user, folder, document, messages, evaluations)
│   │   ├── evaluation/          # LLM-as-a-Judge custom RAG metric evaluator
│   │   ├── guardrails/          # Safety guards (injection, toxicity filters)
│   │   ├── llm/                 # Standard LLM providers (Groq, OpenAI, Anthropic, HF)
│   │   ├── memory/              # Chat histories (SQLite transient backing)
│   │   ├── observability/       # Structured logs writer (JSON Lines tracing)
│   │   ├── rag/                 # Parser, chunker, embeddings, retriever, citation-extractor
│   │   ├── schemas/             # Pydantic schemas (Request/Response validation models)
│   │   ├── services/            # Main services orchestrators (RAG pipeline, auth, docs)
│   │   ├── workers/             # Local in-process tasks queues (ThreadPool tasks)
│   │   └── main.py              # FastAPI main entrypoint and static SPA hosting setup
│   └── requirements.txt         # Core Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/               # Views (Auth, Layout, Dashboard, FolderView, Analytics, Settings)
│   │   ├── stores/              # Zustand app state and auth storage
│   │   ├── App.tsx              # Application shell & routes setup
│   │   └── main.tsx             # Entry hook
│   ├── index.html               # SPA main skeleton
│   ├── vite.config.ts           # Compiles frontend directly into backend/static for production
│   └── package.json             # Node dependencies and build directives
├── Dockerfile                   # Multi-stage production container instructions
├── .env.example                 # Configured variables layout
└── README.md                    # This description file
```

---

## 🚀 Running Locally

### Step 1: Clone and setup Environment
1. Clone this repository.
2. In the root directory, create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and fill in your variables (Especially `GROQ_API_KEY` or `OPENAI_API_KEY`).

### Step 2: Start the Backend (Python)
1. Navigate to the backend directory and set up a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
2. Install Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
   ```

### Step 3: Start the Frontend (React.js)
1. Open a new terminal in the frontend directory:
   ```bash
   cd frontend
   npm install
   ```
2. Start the development server (runs with API proxy on `http://localhost:5173`):
   ```bash
   npm run dev
   ```

---

## 🐳 Running with Docker
You can spin up the entire pre-compiled unified React + FastAPI application in a single command using Docker:

```bash
docker build -t knowledge-hub-ai .
docker run -p 7860:7860 --env-file .env knowledge-hub-ai
```
Visit `http://localhost:7860` to access the full application!

---

## 🤗 Deploying to Hugging Face Spaces (FREE)

Because the app is built on local SQLite database stores and in-process ThreadPool pipelines, you can run this entire premium app inside a free single-container space:

1. Create a new Space on [Hugging Face](https://huggingface.co/spaces).
2. Choose **Docker** as the SDK/Template, and select the **Blank** template.
3. In your Space's **Settings**, add the following **Repository Secrets**:
   * `SECRET_KEY` (Any long random string)
   * `GROQ_API_KEY` (Your free Groq API key)
4. Upload all project files (including `Dockerfile`, `backend/`, and `frontend/`) into your Space repository.
5. Hugging Face will automatically detect the `Dockerfile`, build the React bundle, launch the Python server, and serve the application completely for free under a secure HTTPS URL!

---

## 📊 RAG Pipeline Architecture Details

1. **Document Ingestion**: Custom parsers (`parser.py`) handle PDF, DOCX, CSV, TXT, MD. Documents are segmented using hierarchical token recursive chunking (`chunker.py`) to preserve context.
2. **Dense Vector Store**: Embeddings are computed with Hugging Face's lightweight `SentenceTransformers(all-MiniLM-L6-v2)`. Vector indexes are persisted locally inside folder collections in ChromaDB.
3. **Sparse & Hybrid Reranking**: Queries undergo conversational rewrite (resolving pronoun co-references using LLM history), followed by hybrid retrieval (combining dense Chroma cosine scoring with sparse BM25 token frequencies) and finally re-scored via a lightweight cross-encoder model for optimal relevance.
4. **Citations Engine**: Character-matched exact mappings are extracted from source snippets during generation to display grounded source references side-by-side with chat lines.
