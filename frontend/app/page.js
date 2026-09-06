'use client';
import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Home() {
  const [jd, setJd] = useState('');
  const [job, setJob] = useState(null);
  const [cands, setCands] = useState([]);
  const [selected, setSelected] = useState([]);
  const [screenings, setScreenings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  async function createJob() {
    setLoading(true);
    setMessage('Analyzing JD with Astra...');
    try {
      const r = await fetch(API + '/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: jd })
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Job creation failed');
      setJob(d);
      localStorage.setItem('hiringJob', JSON.stringify(d));
      setMessage('Job created successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (e) {
      setMessage(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadCandidates() {
    const r = await fetch(API + `/api/jobs/${job.id}/candidates`);
    const d = await r.json();
    setCands(r.ok ? d : []);
    if (!r.ok) setMessage(d.detail || 'Could not load candidates.');
  }

  async function start() {
    setLoading(true);
    try {
      const r = await fetch(API + `/api/jobs/${job.id}/screenings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_ids: selected })
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Could not start screenings');
      const skipped = d.skipped?.length ? ` Skipped already screened: ${d.skipped.join(', ')}.` : '';
      setMessage(`Created ${d.created || 0} bulk screening call${d.created === 1 ? '' : 's'}.${skipped}`);
      setTimeout(() => setMessage(''), 5000);
      setSelected([]);
      await refresh();
    } catch (e) {
      setMessage(e.message);
    } finally {
      setLoading(false);
    }
  }

  function startNewJob() {
    localStorage.removeItem('hiringJob');
    setJob(null);
    setCands([]);
    setSelected([]);
    setScreenings([]);
    setMessage('');
  }

  async function refresh() {
    if (!job) return;
    const r = await fetch(API + `/api/jobs/${job.id}/screenings`);
    const d = await r.json();
    if (r.ok) setScreenings(d);
    else setMessage(d.detail || 'Could not load screening status.');
  }

  useEffect(() => {
    const saved = localStorage.getItem('hiringJob');
    if (saved) {
      try {
        setJob(JSON.parse(saved));
      } catch {
        localStorage.removeItem('hiringJob');
      }
    }
  }, []);

  useEffect(() => {
    if (job) {
      loadCandidates();
      refresh();
      const t = setInterval(refresh, 10000);
      return () => clearInterval(t);
    }
  }, [job]);

  function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
  }

  function formatValue(value) {
    if (Array.isArray(value)) return value.join(', ');
    if (value && typeof value === 'object') return JSON.stringify(value);
    return String(value ?? '—');
  }

  const getBadgeClass = (status) => {
    if (!status) return 'badge-neutral';
    const s = status.toLowerCase();
    if (s === 'completed' || s === 'passed' || s === 'success') return 'badge-success';
    if (s === 'failed' || s === 'error') return 'badge-error';
    return 'badge-warning';
  };

  return (
    <main className="container animate-fade-in">
      <header className="mb-6">
        <h1 className="header-title">AI Hiring Assistant</h1>
        <p className="header-subtitle">GPT-6 Astra + Hunar AI Recruitment Screening</p>
      </header>

      {message && (
        <div className="glass-card mb-6" style={{ borderColor: 'var(--primary)', padding: '1rem', textAlign: 'center' }}>
          <p>{message}</p>
        </div>
      )}

      {!job ? (
        <section className="glass-card animate-fade-in" style={{ maxWidth: '800px', margin: '0 auto' }}>
          <div className="flex-between mb-4">
            <h2>Create New Job</h2>
          </div>
          <textarea
            className="glass-input mb-6"
            value={jd}
            onChange={e => setJd(e.target.value)}
            placeholder="Paste the complete job description here to generate screening criteria..."
          />
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <button 
              className={`btn-primary ${!loading && jd.length >= 20 ? 'btn-glow' : ''}`} 
              onClick={createJob} 
              disabled={loading || jd.length < 20}
              style={{ padding: '1rem 3rem', fontSize: '1.1rem' }}
            >
              {loading ? <div className="loader"></div> : 'Analyze Job Description'}
            </button>
          </div>
        </section>
      ) : (
        <div className="animate-fade-in">
          <div className="flex-between mb-6">
            <h2 style={{ fontSize: '1.8rem' }}>{job.title}</h2>
            <button onClick={startNewJob} className="btn-secondary">Start New Job</button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '2rem', marginBottom: '2rem' }}>
            {/* Left Column: Job Details */}
            <section className="glass-card">
              <h3 className="mb-4" style={{ color: 'var(--primary)' }}>Role Requirements</h3>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1.5rem', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                  {JSON.stringify(job.requirements, null, 2)}
                </pre>
              </div>
              
              <h3 className="mb-4" style={{ color: 'var(--primary)' }}>Screening Questions</h3>
              <ol style={{ paddingLeft: '1.2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                {job.questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ol>
            </section>

            {/* Right Column: Candidates */}
            <section className="glass-card">
              <div className="flex-between mb-4">
                <h3>Matched Candidates <span style={{ color: 'var(--text-muted)' }}>({cands.length})</span></h3>
                <button 
                  onClick={start} 
                  disabled={!selected.length || loading} 
                  className="btn-primary"
                >
                  {loading ? <div className="loader"></div> : `Start Screening (${selected.length})`}
                </button>
              </div>
              
              <div className="candidate-list">
                {cands.length === 0 ? (
                  <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>No candidates found for this role.</p>
                ) : (
                  cands.map(c => (
                    <label 
                      key={c.id} 
                      className={`candidate-item ${selected.includes(c.id) ? 'selected' : ''}`}
                    >
                      <input 
                        type="checkbox" 
                        className="custom-checkbox"
                        checked={selected.includes(c.id)} 
                        onChange={e => setSelected(e.target.checked ? [...selected, c.id] : selected.filter(x => x !== c.id))}
                      />
                      <div className="candidate-info">
                        <h3>{c.name}</h3>
                        <p>{c.current_title} &bull; {c.experience_years} yrs &bull; {c.location}</p>
                        <div className="candidate-skills">
                          {c.skills.split(',').map((skill, i) => (
                            <span key={i} className="skill-tag">{skill.trim()}</span>
                          ))}
                        </div>
                      </div>
                    </label>
                  ))
                )}
              </div>
            </section>
          </div>

          {/* Bottom Section: Screenings */}
          <section className="glass-card mb-6">
            <h2 className="mb-6">Screenings Tracker <span style={{ color: 'var(--text-muted)', fontSize: '1.2rem' }}>({screenings.length})</span></h2>
            
            {!screenings.length && (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                No screening calls have been initiated yet. Select candidates above to start.
              </p>
            )}
            
            <div className="screening-grid">
              {screenings.map(s => (
                <div key={s.id} className="screening-card">
                  <div className="flex-between">
                    <h3 style={{ fontSize: '1.2rem' }}>{s.candidate?.name || 'Unknown'}</h3>
                    <span className={`badge ${getBadgeClass(s.lifecycle_status || s.status)}`}>
                      {s.lifecycle_status || s.status}
                    </span>
                  </div>
                  
                  {(s.error) && (
                    <p style={{ color: 'var(--error)', fontSize: '0.9rem' }}>Error: {s.error}</p>
                  )}
                  
                  {s.evaluation && (
                    <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', marginTop: '0.5rem' }}>
                      <div className="flex-between mb-2">
                        <strong style={{ color: 'var(--primary)' }}>{s.evaluation.recommendation}</strong>
                        <strong>{s.evaluation.overall_score}/10</strong>
                      </div>
                      <div className="score-bar-container mb-4">
                        <div className="score-bar" style={{ width: `${(s.evaluation.overall_score / 10) * 100}%` }}></div>
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                        {s.evaluation.summary}
                      </p>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        <span>Tech: {s.evaluation.technical_score}/10</span> &bull; 
                        <span>Comm: {s.evaluation.communication_score}/10</span> &bull; 
                        <span>Skills: {s.evaluation.skills_match_score}/10</span>
                      </div>
                    </div>
                  )}

                  {Object.keys(s.provider_result || {}).length > 0 && !s.evaluation && (
                    <div style={{ background: 'rgba(0,0,0,0.1)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.9rem' }}>
                      {Object.entries(s.provider_result).map(([key, value]) => (
                        <div key={key} className="flex-between mb-2">
                          <span style={{ color: 'var(--text-muted)' }}>{formatLabel(key)}</span>
                          <span>{formatValue(value)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="flex-between mt-auto pt-4" style={{ borderTop: '1px solid var(--surface-border)' }}>
                    {s.recording_url ? (
                      <a href={s.recording_url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        &#9658; Play Recording
                      </a>
                    ) : <span></span>}
                    
                    {s.transcript && (
                      <details style={{ fontSize: '0.9rem' }}>
                        <summary style={{ cursor: 'pointer', color: 'var(--text-muted)' }}>Transcript</summary>
                        <div style={{ marginTop: '0.5rem', background: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '6px', maxHeight: '150px', overflowY: 'auto' }}>
                          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '0.85rem' }}>{s.transcript}</pre>
                        </div>
                      </details>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
