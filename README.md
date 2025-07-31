## QNA RAG Application

A modern Question & Answer system built with Retrieval-Augmented Generation (RAG) technology. Users can securely upload documents, engage in contextual chat-based Q\&A, and leverage robust infrastructure to ensure performance, reliability, and extensibility.

---

## ✨ Key Features

* **Document Upload & Processing**: Seamless PDF ingestion with intelligent text extraction (via PyMuPDF), dynamic chunking, and embedding generation.
* **Contextual Q\&A**: Real-time conversational interface powered by Groq LLM inference and vector similarity search.
* **Secure Authentication**: JWT-based user registration, login, and session management with bcrypt-hashed passwords.
* **High-Performance Search**: Ultra-fast semantic search using Milvus vector database and sentence-transformer embeddings.
* **Resilience & Disaster Recovery**: Persistent backup of vector data in MongoDB to enable rapid restoration in case of Milvus data loss.
* **Rate Limiting & Error Handling**: Global request throttling and centralized middleware for graceful error reporting and monitoring.
* **Role-Based Access**: Multi-tenant isolation with admin controls for user and system management.

---

## 🛠️ Technology & Design Choices

### Backend Framework

* **FastAPI**: Chosen for its asynchronous performance, built-in data validation, and automatic OpenAPI documentation.

### Data Storage

* **PostgreSQL**: Stores all user-related entities (profiles, credentials, metadata). PostgreSQL’s strong ACID guarantees ensure transactional integrity for authentication flows and account settings.
* **MongoDB**: Houses raw document contents, chat transcripts, and vector backup copies. Its schema-less design is ideal for heterogeneous document structures and rapidly evolving message schemas.

  * **Disaster Recovery**: A mirror of Milvus vectors in Mongo allows administrators to restore embeddings if Milvus data is corrupted or deleted, ensuring business continuity.
* **Milvus**: Chosen over alternatives like FAISS, Pinecone, or Weaviate due to its production-readiness, horizontal scalability, and support for billions of vectors. Milvus uses advanced indexing techniques (IVF, HNSW) and offers native distributed deployments, making it suitable for high-throughput, low-latency vector searches.

### Embeddings & AI

* **Sentence-Transformers (all-MiniLM-L6-v2)**: This model offers a strong trade-off between performance and efficiency. It produces compact 384-dimensional embeddings that are sufficiently expressive for semantic search without overloading memory, unlike larger transformer models.
* **Groq API**: Along with Groq's meta-llama/llama-4-maverick-17b-128e-instruct ultra-fast responses, round-robin key management enables horizontal scaling of LLM inference without overloading a single API key provider.
* **PyMuPDF**: Lightweight, high-performance library for extracting text and metadata from PDFs, ensuring reliable chunk boundaries and minimal OCR overhead.

### API Robustness

* **Pydantic Models**: Enforce strict request/response schemas, enabling early validation and reducing runtime errors.
* **Error Handling Middleware**: Centralized exception capture returns consistent HTTP status codes and payloads, simplifying client-side error processing.
* **Rate Limiting**: Global and per-endpoint throttling to guard against abuse, protect AI quota, and maintain quality of service.

### Frontend

* **React 18 + TypeScript**: Strong typing prevents common runtime errors and improves developer experience.
* **Vite**: Ultra-fast bundling and hot module replacement accelerate development cycles.
* **TailwindCSS + shadcn/ui**: Utility-first styling coupled with a component library promotes design consistency and rapid UI iteration.
* **React Context**: Lightweight state management for authentication and theme settings without external dependencies.
* **Axios**: Promise-based HTTP client simplifies API interaction with built-in retry/backoff support.

### Deployment & DevOps

* **Render (Backend)**: Containerized deployment with free-tier simplicity. Downsides include container sleep after inactivity (cold starts) and a 512 MB memory cap—currently limiting on-the-fly loading of large embedding models.
* **Vercel (Frontend)**: Optimized for static site hosting with global CDN, automatic SSL, and seamless Git integration.
* **GitHub Actions**: CI/CD pipeline automates linting, testing, and deployment to Render/Vercel on main-branch merges.
* **Docker**: Ensures consistent environments for local development and production.

---

## 📁 Project Structure

```bash
QNA_RAG/
├── frontend/                 # React app
│   ├── src/
│   └── package.json
├── server/                  # FastAPI service
│   ├── app/
│   │   ├── controllers/     # Route handlers
│   │   ├── services/        # Business logic
│   │   ├── models/          # Pydantic & ORM models
│   │   ├── db/              # PostgreSQL, Mongo, Milvus connectors
│   │   ├── middlewares/     # Error handling, rate limiting
│   │   └── utils/           # Helpers (PDF parsing, chunking)
│   ├── tests/               # Pytest suite
│   └── Dockerfile
└── .github/workflows/       # CI/CD configs
```

---

## 🎯 Getting Started

1. **Clone & Setup**

   ```bash
   git clone <repo-url>
   cd QNA_RAG/server
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   npm install --prefix ../frontend
   ```

2. **Environment Configuration**

   * Populate credentials for PostgreSQL, MongoDB, Milvus, Groq, and JWT settings.

3. **Local Services**

   * Start PostgreSQL, MongoDB, and Milvus (or use Zilliz Cloud).

4. **Run Services**

   * Backend: `uvicorn app.main:app --reload --port 8000`
   * Frontend: `npm run dev --prefix ../frontend`

   The application will be available at:

   * **Frontend**: [http://localhost:5173](http://localhost:5173)
   * **Backend API**: [http://localhost:8000](http://localhost:8000)
   * **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔐 Environment Variables

```env
# FastAPI Core
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
ENVIRONMENT=development
DEBUG=true

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=e5000862
POSTGRES_DB=rag

# MongoDB Configuration
MONGO_HOST=learningmongo.cr2lsf3.mongodb.net
MONGO_USER=root
MONGO_PASSWORD=root
MONGO_DB=rag

# JWT Auth
SECRET_KEY=fc9Ffaxu7PBUblKtHizSijlfiLBYeS2N
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Embedding Settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
CHUNK_SIZE=300
CHUNK_OVERLAP=50

# Milvus Configuration
MILVUS_HOST=https://in03-864c32257795e7c.serverless.aws-eu-central-1.cloud.zilliz.com
MILVUS_PORT=19530
MILVUS_TOKEN=a4d4d8a3fee50837b11afc80a4bd3dd5bc9b4dead1ab9ba1a4563cf8de880ee0ab640b892553d0468848c895ff717fb249f9fa8f
MILVUS_COLLECTION_NAME=insurance_chunks
MILVUS_INDEX_TYPE=IVF_FLAT
MILVUS_METRIC_TYPE=COSINE
MILVUS_NLIST=128

# Groq API Keys (Round Robin)
GROQ_API_KEY_1=...
GROQ_API_KEY_2=...
GROQ_API_KEY_3=...
GROQ_API_KEY_4=...
GROQ_API_KEY_5=...
GROQ_API_KEY_6=...

# Groq Model & Throttling
GROQ_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct
GROQ_BASE_URL=https://api.groq.com
GROQ_MAX_TOKENS=8192
GROQ_RATE_LIMIT_RPM=30
GROQ_RATE_LIMIT_TPM=6000

# Feature Toggles
ENABLE_TENANT_LLM_CONFIG=true
ENABLE_TENANT_API_KEYS=true
```

---

## 🔍 Testing & Quality

* **Backend**: `pytest --cov=app`
* **Frontend**: `npm test --prefix frontend`

---

## 🔮 Scope For Improvements

1. **Test Coverage**: Expand unit and integration tests, including edge-case scenarios for PDF parsing and concurrency.
2. **LLM Provider Configurability**: Extend frontend settings to allow tenant-specific LLM provider selection (e.g., OpenAI, Groq).
3. **Memory Optimization**: Offload large embedding models to remote inference (e.g., Hugging Face Spaces) or increase server memory.
4. **UI/UX Enhancements**: Improve chat interface with conversation threading, syntax highlighting, and document annotation tools.

---
