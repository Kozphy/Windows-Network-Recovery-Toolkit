import React, { useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [message, setMessage] = useState('Check proxy drift on this endpoint');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function askAgent() {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function approve(approved) {
    const actionId = result?.proposed_action?.id;
    if (!actionId) return;
    const response = await fetch(`${API}/api/actions/${actionId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved }),
    });
    if (!response.ok) throw new Error(`Approval failed: ${response.status}`);
    setResult({ ...result, proposed_action: { ...result.proposed_action, approved } });
  }

  return (
    <main style={{ maxWidth: 960, margin: '40px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1>AI Technology Risk & Recovery Platform</h1>
      <p>Grounded diagnosis → tool proposal → policy gate → human approval → audit.</p>
      <textarea
        rows={5}
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        style={{ width: '100%', padding: 12 }}
      />
      <button onClick={askAgent} disabled={loading} style={{ marginTop: 12, padding: '10px 16px' }}>
        {loading ? 'Analyzing…' : 'Ask Agent'}
      </button>
      {error && <p role="alert">{error}</p>}
      {result && (
        <section style={{ marginTop: 24 }}>
          <h2>Agent result</h2>
          <p>{result.answer}</p>
          <h3>Evidence</h3>
          <ul>{result.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
          {result.proposed_action && (
            <div>
              <h3>Proposed action</h3>
              <pre>{JSON.stringify(result.proposed_action, null, 2)}</pre>
              {result.proposed_action.requires_approval && result.proposed_action.approved == null && (
                <div>
                  <button onClick={() => approve(true)}>Approve</button>{' '}
                  <button onClick={() => approve(false)}>Reject</button>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </main>
  );
}
