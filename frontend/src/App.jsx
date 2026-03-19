import { useState, useRef, useCallback } from 'react'

const API_BASE = '/api'

// ─── API helpers ──────────────────────────────────────────────────────────────
async function uploadSOP(file) {
  const form = new FormData()
  form.append('file', file)
  const r = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form })
  if (!r.ok) {
    const isJson = r.headers.get('content-type')?.includes('application/json');
    const e = isJson ? await r.json() : { detail: 'Server error (Not JSON)' };
    throw new Error(e.detail || 'Upload failed');
  }
  return r.json()
}

async function processSOP(text, filename) {
  const r = await fetch(`${API_BASE}/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, filename }),
  })
  if (!r.ok) {
    const isJson = r.headers.get('content-type')?.includes('application/json');
    const e = isJson ? await r.json() : { detail: 'Server error (Not JSON)' };
    throw new Error(e.detail || 'Processing failed');
  }
  return r.json()
}

async function generatePresentation(summary, training, quiz, job_id, filename) {
  const r = await fetch(`${API_BASE}/presentation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ summary, training, quiz, job_id, filename }),
  })
  if (!r.ok) {
    const isJson = r.headers.get('content-type')?.includes('application/json');
    const e = isJson ? await r.json() : { detail: 'Server error (Not JSON)' };
    throw new Error(e.detail || 'Presentation failed');
  }
  return r.json()
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SummaryTab({ data }) {
  const s = data.summary
  return (
    <div className="animate-in">
      <div className="overview-card" style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <h2 style={{ fontFamily: 'Plus Jakarta Sans, sans-serif', fontSize: '1.3rem', fontWeight: 700 }}>
            📋 {s.title}
          </h2>
          {s.department && <span className="chip chip-green">📂 {s.department}</span>}
        </div>
        <p className="overview-text">{s.overview}</p>
      </div>

      <div className="card-grid-2" style={{ marginBottom: '1.25rem' }}>
        <div className="card">
          <div className="label label-accent">Purpose</div>
          <p style={{ fontSize: '0.88rem', lineHeight: 1.65 }}>{s.purpose}</p>
        </div>
        <div className="card">
          <div className="label label-accent">Scope</div>
          <p style={{ fontSize: '0.88rem', lineHeight: 1.65 }}>{s.scope}</p>
        </div>
      </div>

      {s.key_points?.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <div className="section-title">⚡ Key Points</div>
          <div className="key-points-grid">
            {s.key_points.map((pt, i) => (
              <div key={i} className="key-point-item animate-in">
                <div className="key-point-dot">{i + 1}</div>
                <span style={{ fontSize: '0.88rem' }}>{pt}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {s.sections?.length > 0 && (
        <div style={{ marginBottom: '1.25rem' }}>
          <div className="section-title">📄 Document Sections</div>
          {s.sections.map((sec, i) => (
            <div key={i} className="section-item animate-in">
              <div className="section-item-title">{sec.heading}</div>
              <div className="section-item-text">{sec.summary}</div>
            </div>
          ))}
        </div>
      )}

      {s.compliance_notes && (
        <div className="card" style={{ borderLeft: '3px solid var(--amber)' }}>
          <div className="label" style={{ color: 'var(--amber)' }}>⚠ Compliance Notes</div>
          <p style={{ fontSize: '0.88rem', lineHeight: 1.65 }}>{s.compliance_notes}</p>
        </div>
      )}
    </div>
  )
}

function TrainingTab({ data }) {
  const [expanded, setExpanded] = useState(0)
  const t = data.training
  return (
    <div className="animate-in">
      <div className="card" style={{ marginBottom: '1.25rem', background: 'linear-gradient(135deg, rgba(108,99,255,0.08), rgba(0,212,255,0.04))' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem' }}>
          <div>
            <div className="label">Training Title</div>
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{t.training_title}</div>
          </div>
          <div>
            <div className="label">Target Audience</div>
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{t.target_audience}</div>
          </div>
          <div>
            <div className="label">Duration</div>
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>⏱ {t.estimated_duration}</div>
          </div>
        </div>
        {t.learning_objectives?.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            <div className="label">Learning Objectives</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.4rem' }}>
              {t.learning_objectives.map((obj, i) => (
                <span key={i} className="chip" style={{ fontSize: '0.8rem' }}>✓ {obj}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="section-title">🎓 Training Modules</div>
      {t.modules?.map((mod, i) => (
        <div key={i} className={`module-card ${expanded === i ? 'expanded' : ''} animate-in`}>
          <div className="module-header" onClick={() => setExpanded(expanded === i ? -1 : i)}>
            <div className="module-header-left">
              <div className="module-num">{mod.module_number || i + 1}</div>
              <div>
                <div className="module-title">{mod.title}</div>
                <div className="module-objective">{mod.objective}</div>
              </div>
            </div>
            <span style={{ color: 'var(--text-secondary)', fontSize: '1.2rem' }}>
              {expanded === i ? '▲' : '▼'}
            </span>
          </div>

          {expanded === i && (
            <div className="module-body animate-in">
              <div className="divider" style={{ marginTop: 0 }} />
              <div className="label" style={{ marginBottom: '0.75rem' }}>Steps</div>
              {mod.steps?.map((step, j) => (
                <div key={j} className="step-item">
                  <div className="step-num">{step.step_number || j + 1}</div>
                  <div className="step-content">
                    <div className="step-action">{step.action}</div>
                    <div className="step-details">{step.details}</div>
                    {step.responsible && (
                      <div className="step-responsible">👤 {step.responsible}</div>
                    )}
                  </div>
                </div>
              ))}

              {mod.tips?.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <div className="label label-accent">💡 Tips</div>
                  <div className="tips-row">
                    {mod.tips.map((tip, k) => <span key={k} className="tip-chip">{tip}</span>)}
                  </div>
                </div>
              )}

              {mod.common_mistakes?.length > 0 && (
                <div style={{ marginTop: '0.75rem' }}>
                  <div className="label" style={{ color: 'var(--red)' }}>⚠ Common Mistakes</div>
                  <div className="tips-row">
                    {mod.common_mistakes.map((m, k) => <span key={k} className="mistake-chip">{m}</span>)}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {t.summary && (
        <div className="card" style={{ marginTop: '0.5rem', borderLeft: '3px solid var(--cyan)' }}>
          <div className="label label-accent">Training Summary</div>
          <p style={{ fontSize: '0.88rem', lineHeight: 1.65 }}>{t.summary}</p>
        </div>
      )}
    </div>
  )
}

function QuizTab({ data }) {
  const [answers, setAnswers] = useState({})
  const [revealed, setRevealed] = useState({})
  const q = data.quiz

  const selectAnswer = (qIdx, key) => {
    if (revealed[qIdx]) return
    setAnswers(a => ({ ...a, [qIdx]: key }))
    setRevealed(r => ({ ...r, [qIdx]: true }))
  }

  const score = q.questions?.filter((ques, i) => answers[i] === ques.correct_answer).length || 0
  const total = q.questions?.length || 0
  const allDone = Object.keys(revealed).length === total && total > 0

  return (
    <div className="animate-in">
      <div className="card" style={{ marginBottom: '1.25rem', background: 'linear-gradient(135deg, rgba(108,99,255,0.08), transparent)' }}>
        <div style={{ fontFamily: 'Plus Jakarta Sans, sans-serif', fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.5rem' }}>
          📝 {q.quiz_title}
        </div>
        <div className="quiz-meta">
          <div className="quiz-meta-chip">⏱ {q.time_limit}</div>
          <div className="quiz-meta-chip">✅ Pass: {q.passing_score}</div>
          <div className="quiz-meta-chip">❓ {total} Questions</div>
          {allDone && <div className="quiz-meta-chip" style={{ borderColor: score / total >= 0.8 ? 'var(--green)' : 'var(--red)', color: score / total >= 0.8 ? 'var(--green)' : 'var(--red)' }}>
            🏆 Score: {score}/{total}
          </div>}
        </div>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{q.instructions}</p>
      </div>

      {q.questions?.map((ques, i) => {
        const userAns = answers[i]
        const isRevealed = revealed[i]
        return (
          <div key={i} className="question-card animate-in">
            <div className="q-header">
              <div className="q-num">{ques.question_number || i + 1}</div>
              <div className="q-text">{ques.question}</div>
              <div className={`diff-badge diff-${ques.difficulty || 'medium'}`}>{ques.difficulty}</div>
            </div>
            <div className="options-grid">
              {Object.entries(ques.options || {}).map(([key, text]) => {
                let cls = 'option-btn'
                if (isRevealed) {
                  if (key === ques.correct_answer) cls += ' show-correct'
                  else if (key === userAns) cls += ' selected-wrong'
                } else if (key === userAns) cls += ' selected-correct'
                return (
                  <button key={key} className={cls} onClick={() => selectAnswer(i, key)}>
                    <span className="option-key">{key}</span>
                    {text}
                    {isRevealed && key === ques.correct_answer && ' ✓'}
                    {isRevealed && key === userAns && key !== ques.correct_answer && ' ✗'}
                  </button>
                )
              })}
            </div>
            {isRevealed && (
              <div className="explanation-box">
                <span className="explain-label">Explanation:</span>{ques.explanation}
              </div>
            )}
            {!isRevealed && (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                📌 Topic: {ques.topic}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function PresentationTab({ data, jobId, filename, onGenerate, pptxData, generating, pptxError }) {
  return (
    <div className="animate-in">
      <div className="pptx-panel">
        <div className="pptx-icon">📊</div>
        <div className="pptx-title">Download Presentation</div>
        <div className="pptx-sub">
          Generate a beautifully designed PowerPoint with your summary, training modules, and quiz — ready for presentations.
        </div>

        <div className="pptx-features">
          {[
            ['🎨', 'Dark Premium Theme'],
            ['📋', 'Summary Slides'],
            ['🎓', 'Module-per-Slide'],
            ['❓', 'Quiz Slides with Answers'],
            ['🏁', 'Thank You Slide'],
            ['📁', 'Downloadable .pptx'],
          ].map(([icon, label]) => (
            <div key={label} className="pptx-feature">
              <span style={{ fontSize: '1.1rem' }}>{icon}</span>
              <span style={{ fontSize: '0.85rem' }}>{label}</span>
            </div>
          ))}
        </div>

        {pptxError && <div className="error-box">⚠ {pptxError}</div>}

        {pptxData ? (
          <div className="pptx-success">
            <div className="pptx-success-text">
              <div className="title">✅ Presentation Ready!</div>
              <div className="sub">{pptxData.slide_count} slides generated</div>
            </div>
            <a
              href={`http://localhost:8003/download/${pptxData.job_id}`}
              target="_blank" rel="noopener noreferrer"
            >
              <button className="btn btn-download">
                ⬇ Download .pptx
              </button>
            </a>
          </div>
        ) : (
          <button
            className="btn btn-primary"
            onClick={onGenerate}
            disabled={generating}
          >
            {generating ? (
              <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Generating…</>
            ) : '🚀 Generate Presentation'}
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Main App ────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'summary', label: '📋 Summary' },
  { id: 'training', label: '🎓 Training' },
  { id: 'quiz', label: '❓ Quiz' },
  { id: 'presentation', label: '📊 Slides' },
]

export default function App() {
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState(null)
  const [status, setStatus] = useState('idle') // idle | uploading | processing | done | error
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')
  const [pptxData, setPptxData] = useState(null)
  const [pptxGen, setPptxGen] = useState(false)
  const [pptxError, setPptxError] = useState('')
  const fileInputRef = useRef()

  const handleFile = useCallback((f) => {
    if (!f) return
    const ext = f.name.split('.').pop().toLowerCase()
    if (!['pdf', 'txt'].includes(ext)) {
      setError('Only .pdf and .txt files are supported.')
      return
    }
    setFile(f)
    setError('')
    setResult(null)
    setPptxData(null)
  }, [])

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const onProcess = async () => {
    if (!file) return
    setError(''); setResult(null); setPptxData(null)
    try {
      setStatus('uploading')
      const uploaded = await uploadSOP(file)
      setStatus('processing')
      const processed = await processSOP(uploaded.text, uploaded.filename)
      setResult(processed)
      setActiveTab('summary')
      setStatus('done')
    } catch (e) {
      setError(e.message)
      setStatus('error')
    }
  }

  const onGenerate = async () => {
    if (!result) return
    setPptxGen(true); setPptxError('')
    try {
      const p = await generatePresentation(
        result.summary, result.training, result.quiz,
        result.job_id, result.filename || 'SOP_Training'
      )
      setPptxData(p)
    } catch (e) {
      setPptxError(e.message)
    } finally {
      setPptxGen(false)
    }
  }

  const isProcessing = status === 'uploading' || status === 'processing'

  return (
    <div className="app-wrapper">
      {/* ── Header ── */}
      <header className="header">
        <div className="logo">
          SOP Training AI
        </div>
        <span className="badge">AI Engine Powered by Gemini 2.5 Flash</span>
      </header>

      <main className="main">
        {/* ── Hero ── */}
        <section className="hero">
          <div className="hero-tag">✦ AI-Powered Training System</div>
          <h1 className="hero-title">
            Turn any SOP into a<br />
            <span className="gradient-text">Complete Training Program</span>
          </h1>
          <p className="hero-sub">
            Upload your Standard Operating Procedure and get an instant AI-generated
            summary, step-by-step training content, quiz questions, and a PowerPoint deck.
          </p>
        </section>

        {/* ── Upload ── */}
        <div
          className={`upload-card ${dragOver ? 'drag-over' : ''}`}
          onClick={() => !file && fileInputRef.current.click()}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <input
            type="file" ref={fileInputRef} style={{ display: 'none' }}
            accept=".pdf,.txt"
            onChange={e => handleFile(e.target.files[0])}
          />

          {file ? (
            <div className="upload-filename">
              📄 {file.name}
              <button
                className="btn btn-secondary"
                style={{ padding: '0.3rem 0.75rem', fontSize: '0.78rem', marginLeft: '0.5rem' }}
                onClick={e => { e.stopPropagation(); setFile(null); setResult(null); setStatus('idle') }}
              >✕ Remove</button>
            </div>
          ) : (
            <>
              <div className="upload-icon">☁️</div>
              <div className="upload-title">Drag & drop your SOP document here</div>
              <div className="upload-sub">or click to browse files</div>
              <div className="upload-formats">
                <span className="format-tag">PDF</span>
                <span className="format-tag">TXT</span>
              </div>
            </>
          )}
        </div>

        {error && <div className="error-box">⚠ {error}</div>}

        {isProcessing && (
          <div className="processing-banner">
            <div className="spinner" />
            <div className="processing-text">
              <div className="processing-title">
                {status === 'uploading' ? '📤 Uploading and extracting text…' : '🤖 AI is generating your training package…'}
              </div>
              <div className="processing-sub">
                {status === 'uploading' ? 'Parsing your SOP document' : 'Creating summary, training modules, and quiz questions with AI'}
              </div>
            </div>
          </div>
        )}

        <div className="btn-center">
          <button
            className="btn btn-primary"
            onClick={onProcess}
            disabled={!file || isProcessing}
          >
            {isProcessing
              ? <><span className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Processing…</>
              : '🚀 Process SOP'}
          </button>
        </div>

        {/* ── Results ── */}
        {result && (
          <div className="tabs-wrapper">
            <div className="tabs-header">
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === 'summary' && <SummaryTab data={result} />}
            {activeTab === 'training' && <TrainingTab data={result} />}
            {activeTab === 'quiz' && <QuizTab data={result} />}
            {activeTab === 'presentation' && (
              <PresentationTab
                data={result}
                jobId={result.job_id}
                filename={result.filename}
                onGenerate={onGenerate}
                pptxData={pptxData}
                generating={pptxGen}
                pptxError={pptxError}
              />
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        SOP Training AI System • Built with <span>FastAPI</span> + <span>React</span> + <span>Gemini</span>
      </footer>
    </div>
  )
}
