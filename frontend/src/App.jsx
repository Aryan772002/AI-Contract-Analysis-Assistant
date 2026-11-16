import { useRef, useState } from 'react'
import './summary.css'
import './classification.css'
import './qa.css'
import './risk.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function displayError(error, fallback) {
  if (error?.message === 'Failed to fetch') {
    return 'Could not connect to the API. Keep the backend terminal open and confirm it is running at http://localhost:8000.'
  }
  return error?.message || fallback
}

export default function App() {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [summaryBusy, setSummaryBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [summary, setSummary] = useState(null)
  const [summaryError, setSummaryError] = useState('')
  const [question, setQuestion] = useState('')
  const [qaBusy, setQaBusy] = useState(false)
  const [qaError, setQaError] = useState('')
  const [qaResult, setQaResult] = useState(null)
  const [riskBusy, setRiskBusy] = useState(false)
  const [riskError, setRiskError] = useState('')
  const [riskResult, setRiskResult] = useState(null)

  function chooseFile(nextFile) {
    setError('')
    setResult(null)
    setSummary(null)
    setSummaryError('')
    setQuestion('')
    setQaError('')
    setQaResult(null)
    setRiskError('')
    setRiskResult(null)
    if (!nextFile) return
    if (nextFile.type !== 'application/pdf' && !nextFile.name.toLowerCase().endsWith('.pdf')) {
      setFile(null)
      setError('Please select a PDF document.')
      return
    }
    if (nextFile.size > 15 * 1024 * 1024) {
      setFile(null)
      setError('This file is over 15 MB. Please choose a smaller PDF.')
      return
    }
    setFile(nextFile)
  }

  async function upload() {
    if (!file) return
    setBusy(true)
    setError('')
    setResult(null)
    const body = new FormData()
    body.append('file', file)
    try {
      const response = await fetch(`${API_URL}/api/documents/upload`, { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Upload failed. Please try again.')
      setResult(payload)
    } catch (err) {
      setError(displayError(err, 'Could not upload this PDF. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  async function generateSummary() {
    if (!file) return
    setSummaryBusy(true)
    setSummaryError('')
    setSummary(null)
    const body = new FormData()
    body.append('file', file)
    try {
      const response = await fetch(API_URL + '/api/documents/summarize', { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Could not generate a summary.')
      setSummary(payload)
    } catch (err) {
      setSummaryError(displayError(err, 'Could not reach the summary service.'))
    } finally {
      setSummaryBusy(false)
    }
  }

  async function askQuestion() {
    if (!file || !question.trim()) return
    setQaBusy(true)
    setQaError('')
    setQaResult(null)
    const body = new FormData()
    body.append('file', file)
    body.append('question', question.trim())
    try {
      const response = await fetch(API_URL + '/api/documents/ask', { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Could not answer that question.')
      setQaResult(payload)
    } catch (err) {
      setQaError(displayError(err, 'Could not reach the question-answering service.'))
    } finally {
      setQaBusy(false)
    }
  }

  async function analyzeRisks() {
    if (!file) return
    setRiskBusy(true)
    setRiskError('')
    setRiskResult(null)
    const body = new FormData()
    body.append('file', file)
    try {
      const response = await fetch(API_URL + '/api/documents/risks', { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail || 'Could not analyze contract risks.')
      setRiskResult(payload)
    } catch (err) {
      setRiskError(displayError(err, 'Could not reach the risk-analysis service.'))
    } finally {
      setRiskBusy(false)
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="#home" aria-label="Clausewise home"><span className="brand-icon">C</span><span>clausewise</span></a>
        <span className="top-note"><span className="status-dot" /> Private document workspace</span>
      </header>

      <section className="hero" id="home">
        <div className="eyebrow"><span className="eyebrow-line" /> CONTRACT INTELLIGENCE</div>
        <h1>Make sense of<br /><em>the fine print.</em></h1>
        <p className="intro">Start by adding a contract. Clausewise will prepare it for careful, source-grounded analysis.</p>

        <section className="upload-card" aria-label="Upload a contract">
          <div className={`dropzone ${dragging ? 'dragging' : ''}`} onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]) }}>
            <input ref={inputRef} type="file" accept="application/pdf,.pdf" hidden onChange={(event) => chooseFile(event.target.files[0])} />
            <div className="file-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3.75h6.5L19 9.3v10.95H7a2 2 0 0 1-2-2V5.75a2 2 0 0 1 2-2Z"/><path d="M13 4v5h5M8.5 14h7M8.5 17h5"/></svg></div>
            <strong>{file ? file.name : 'Drop your contract here'}</strong>
            <span>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · PDF` : 'or click to browse your files'}</span>
            <small>PDF format · Up to 15 MB</small>
          </div>

          {error && <div className="notice error" role="alert">{error}</div>}
          {result && <div className="notice success" role="status"><strong>{result.filename}</strong><span>{result.message}</span><span className="result-stats">{result.page_count} pages · {result.pages_with_text} with text · {result.chunk_count} text sections prepared</span></div>}

          <button className="upload-button" onClick={upload} disabled={!file || busy}>
            {busy ? <><span className="spinner" /> Uploading and reading…</> : <>Upload document <span aria-hidden="true">→</span></>}
          </button>
          {result && <button className="summary-button" onClick={generateSummary} disabled={summaryBusy}>
            {summaryBusy ? <><span className="spinner dark" /> Generating summary…</> : <>Generate AI summary <span aria-hidden="true">✳</span></>}
          </button>}
          {result && <button className="risk-button" onClick={analyzeRisks} disabled={riskBusy}>
            {riskBusy ? <><span className="spinner dark" /> Reviewing clauses…</> : <>Analyze contract risks <span aria-hidden="true">⌕</span></>}
          </button>}
          {summaryError && <div className="notice error" role="alert">{summaryError}</div>}
          {riskError && <div className="notice error" role="alert">{riskError}</div>}
          <p className="privacy"><svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="1.5"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"/></svg> The PDF is not saved. Summaries send extracted text; Q&amp;A and risk checks send matching excerpts to Groq.</p>
        </section>

        {result && <section className="qa-card">
          <div className="qa-header"><div><div className="eyebrow summary-eyebrow">RETRIEVAL-AUGMENTED Q&amp;A</div><h2>Ask this contract</h2></div></div>
          <label htmlFor="contract-question">What would you like to know?</label>
          <textarea id="contract-question" value={question} maxLength={1000} onChange={(event) => setQuestion(event.target.value)} placeholder="For example: When is payment due?" rows={3} />
          <button className="qa-button" onClick={askQuestion} disabled={!question.trim() || qaBusy}>
            {qaBusy ? <><span className="spinner dark" /> Finding an answer…</> : <>Ask question <span aria-hidden="true">→</span></>}
          </button>
          {qaError && <div className="notice error" role="alert">{qaError}</div>}
          {qaResult && <div className="qa-result" aria-live="polite">
            <p className="retrieval-note">Retrieval: {qaResult.retrieval_method === 'faiss' ? 'semantic embeddings · FAISS' : 'keyword similarity · compatibility fallback'}</p>
            <p className="qa-answer">{qaResult.answer}</p>
            {qaResult.sources?.length > 0 && <div className="qa-sources"><h3>Retrieved sources</h3>{qaResult.sources.map((source) => <article className="qa-source" key={source.chunk_id}><div><b>Page {source.page_number}</b><span>Chunk {source.chunk_id} · relevance {source.relevance}</span></div><p>{source.excerpt}</p></article>)}</div>}
            <p className="summary-caveat">AI-generated answer. Check the cited page in the original document.</p>
          </div>}
        </section>}

        {riskResult && <section className="risk-dashboard" aria-live="polite">
          <div className="risk-heading"><div><div className="eyebrow summary-eyebrow">PRELIMINARY CLAUSE REVIEW</div><h2>Risk analysis</h2></div><span className="model-tag">{riskResult.model || 'Local scan'}</span></div>
          <p className="risk-intro">{riskResult.message}</p>
          <div className="risk-counts">
            {['High', 'Medium', 'Low'].map((level) => <div className={'risk-count ' + level.toLowerCase()} key={level}><span>{level}</span><strong>{riskResult.findings.filter((finding) => finding.risk_level === level).length}</strong></div>)}
          </div>
          {riskResult.findings.length === 0 ? <p className="risk-empty">No potentially risky clauses were surfaced by this scan.</p> :
            <div className="risk-findings">{riskResult.findings.map((finding, index) => <article className="risk-finding" key={finding.source_id + '-' + index}>
              <header><span className={'risk-pill ' + finding.risk_level.toLowerCase()}>{finding.risk_level} risk</span><span className="risk-category">{finding.category}</span><b>{finding.title}</b><span className="risk-page">Page {finding.page_number}</span></header>
              <p>{finding.reason}</p>
              {finding.potential_impact && <p><b>Potential impact:</b> {finding.potential_impact}</p>}
              <blockquote>{finding.excerpt}</blockquote>
            </article>)}</div>}
          <p className="summary-caveat">Automated review signals can miss context or be wrong. Verify each excerpt and consult a qualified lawyer for legal advice.</p>
        </section>}

        {summary && <section className="summary-card" aria-live="polite">
          <div className="summary-heading"><div><div className="eyebrow summary-eyebrow">AI-GENERATED OVERVIEW</div><h2>Contract summary</h2></div><span className="model-tag">{summary.model}</span></div>
          {!summary.is_contract && <div className="document-warning">This file doesn’t appear to be a contract.</div>}
          <p className="summary-text">{summary.summary}</p>
          {summary.input_truncated && <p className="truncation-note">Only the first {summary.characters_analyzed.toLocaleString()} characters were analyzed. Review the full contract for omitted details.</p>}
          <div className="summary-grid">
            <SummaryList title="Parties" items={summary.parties} fields={['name', 'role']} empty="No parties identified." />
            <SummaryList title="Important dates" items={summary.important_dates} fields={['date', 'event']} empty="No dates identified." />
            <SummaryList title="Payment terms" items={summary.payment_terms} fields={['description', 'amount', 'due']} empty="No payment terms identified." />
          </div>
          <p className="summary-caveat">AI-generated summary. Verify all details against the original contract; this is not legal advice.</p>
        </section>}

        <div className="next-step"><span className="step-number">04</span><span><b>Ask with source context</b><br />Answers use relevant page excerpts from your document.</span><span className="step-arrow">✳</span></div>
      </section>
      <footer><span>CLAUSEWISE <span className="footer-sep">/</span> DOCUMENT WORKSPACE</span><span>Built for clarity, one clause at a time.</span></footer>
    </main>
  )
}

function SummaryList({ title, items, fields, empty }) {
  return <div className="summary-list"><h3>{title}</h3>{items.length ? <ul>{items.map((item, index) => <li key={index}>{fields.map((field) => item[field]).filter(Boolean).join(' · ')}</li>)}</ul> : <p>{empty}</p>}</div>
}
