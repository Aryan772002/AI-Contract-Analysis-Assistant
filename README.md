# AI Contract Analysis Assistant

Portfolio project built step by step. It provides a React PDF upload page connected to FastAPI, PyMuPDF text extraction and page-aware chunks, Groq summaries, key-field extraction, source-cited Q&A, and preliminary clause risk signals. Q&A uses dense sentence embeddings and a FAISS cosine-similarity index when the optional packages are installed; otherwise it clearly reports and uses the lightweight TF-IDF fallback. Uploaded PDFs and their FAISS index are processed in memory and are not saved by this demo.

## Run locally on Windows

For first-time setup, use Command Prompt from the project folder. Copy the example env file once, only if your env file does not exist yet. Do not overwrite it after saving your API key.

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
notepad .env
python -m uvicorn backend.main:app --reload
```

Start the React frontend in a second terminal. With PowerShell and fnm, initialize fnm for that window, then use `npm.cmd`:

```powershell
fnm env --use-on-cd --shell powershell | Out-String | Invoke-Expression
cd "frontend"
npm.cmd install
npm.cmd run dev
```

In the local `.env` file, add your Groq API key from [Groq Console](https://console.groq.com/keys). Never paste the key into chat or commit `.env`; it is ignored by Git. The project calls Groq's HTTP API with Python's standard library, so the Groq SDK and dotenv package are not required. The model is configurable through `GROQ_MODEL`. Current Groq documentation lists the earlier Llama 3.1/3.3 IDs as deprecated for developer-tier access, so the default uses Groq's documented replacement `openai/gpt-oss-20b`; set a Llama model ID only if your account still has access. See [Groq model availability](https://console.groq.com/docs/models) and [deprecation details](https://console.groq.com/docs/deprecations).

### Optional FAISS semantic search

The current Python 3.15 setup can run the app using TF-IDF retrieval. To enable embedding vectors and FAISS on Windows, install Python 3.14 x64, create a separate environment with it, then install the optional requirements:

```bat
py -3.14 -m venv .venv-faiss
.venv-faiss\Scripts\activate.bat
python -m pip install -r requirements-faiss.txt
python -m uvicorn backend.main:app --reload
```

On its first Q&A request, Sentence Transformers downloads `sentence-transformers/all-MiniLM-L6-v2`; internet access is required. The in-memory FAISS index is rebuilt for each question because uploads are intentionally not persisted. The UI shows which retrieval method answered each question. See the [official FAISS install guide](https://github.com/facebookresearch/faiss/blob/main/INSTALL.md).

## Deploy a public demo

Deploy the FastAPI backend as a Render Web Service and the React app as a Vercel project, both connected to this GitHub repository.

### Backend on Render

Use the repository root as the service root directory, `pip install -r requirements.txt` as the build command, and `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` as the start command. Add `GROQ_API_KEY` and `GROQ_MODEL` in the Render service environment. After deploying the frontend, set `CORS_ORIGINS` in Render to its full `https://...vercel.app` origin and redeploy.

### Frontend on Vercel

Import the repository, set the root directory to `frontend`, and add the environment variable `VITE_API_URL` with the Render backend URL (for example, `https://your-service.onrender.com`). Deploy, then copy the Vercel URL to share the demo. Keep the Groq key only in Render; never add it to a `VITE_` variable or commit it.

Render's free web services can sleep after inactivity and may take about a minute to wake up. They have an ephemeral filesystem; this demo processes uploaded PDFs in memory and does not save them. This is a public demo without sign-in, so anyone with the link can make requests to the backend and use its configured Groq API key.

Open the local URL printed by Vite (normally `http://localhost:5173`). The API docs are available at `http://localhost:8000/docs`. The ingestion functions are in `src/contract_assistant/ingest.py`; retrieval is in `src/contract_assistant/retrieval.py`; upload, summary, and question endpoints are in `backend/main.py`. This stage handles text-based PDFs. Image-only scanned documents need OCR, which can be added later. Summaries and questions send extracted contract text or retrieved excerpts to Groq. Do not use confidential documents with the hosted API.

For a safe demo document, run `python scripts/create_sample_contract.py` from the project root. It creates `data/sample_contract.pdf` with fictional names and terms.
