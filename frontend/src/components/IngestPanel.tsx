import { useState, useRef } from 'react'
import { api, type TraceStep } from '../api'
import { TraceAnimation } from './TraceAnimation'

const SAMPLES: Record<string, string> = {
  meeting: `Engineering All-Hands Meeting — Q2 Planning
Subject: Q2 Priorities and Resource Allocation
From: john.lavorato@enron.com
To: all-engineering@enron.com

Discussed key priorities for Q2:
1. West Coast trading desk needs additional risk analysts — Tim Belden to lead hiring
2. California regulatory situation worsening — Jeff Dasovich to coordinate government relations response
3. New quantitative models for energy derivatives — Vince Kaminski's team to deliver by end of April
4. Authentication system migration to new platform — targeting June rollout

Key decision: Prioritize California response over new trading platform features.
Action items assigned to respective leads.`,

  decision: `Decision: Restructure West Coast Operations
From: jeff.skilling@enron.com
To: john.lavorato@enron.com, tim.belden@enron.com

After reviewing Q1 performance and the changing regulatory landscape in California, I've decided to restructure the West Coast trading operations:

- Tim Belden will take over as head of West Coast Trading
- Consolidate Portland and San Francisco desks
- Increase risk limits for California power markets by 40%
- New weekly reporting cadence to executive committee

This takes effect immediately. Tim, please prepare a transition plan by Friday.`,

  incident: `URGENT: California Grid Emergency
From: tim.belden@enron.com
To: john.lavorato@enron.com, jeff.skilling@enron.com

California ISO declared Stage 2 emergency today. Rolling blackouts expected in Southern California.

Our exposure:
- Long 2,400 MW in SP15
- Short 800 MW in NP15
- Net positive position if prices spike

Recommendation: Hold current positions. Expected price movement favorable.
Risk: Political backlash if we're seen profiting from crisis.

Need executive sign-off on holding strategy by end of day.`,
}

interface Props {
  onIngestComplete: () => void
  onStatusChange: (msg: string) => void
  onHighlightNodes: (nodes: string[]) => void
}

export function IngestPanel({ onIngestComplete, onStatusChange, onHighlightNodes }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ created: string[]; updated: string[]; message: string } | null>(null)
  const [trace, setTrace] = useState<TraceStep[] | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const submit = async () => {
    const content = inputRef.current?.value.trim()
    if (!content || loading) return
    setLoading(true)
    setResult(null)
    setTrace(null)
    onStatusChange('AI is analyzing and updating the graph...')
    try {
      const res = await api.ingest(content)
      setResult({
        created: res.nodes_created,
        updated: res.nodes_updated,
        message: res.commit_message,
      })
      if (res.trace?.length > 0) setTrace(res.trace)
      onStatusChange(`Ingested — ${res.nodes_created.length} created, ${res.nodes_updated.length} updated`)
      if (inputRef.current) inputRef.current.value = ''
      onIngestComplete()
    } catch (err) {
      setResult({ created: [], updated: [], message: `Error: ${err instanceof Error ? err.message : 'Unknown'}` })
      onStatusChange('Ingestion failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 20, gap: 12 }}>
      <h3 style={{
        fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 500,
        color: 'var(--text)', flexShrink: 0,
      }}>Feed a new event</h3>

      <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5, flexShrink: 0 }}>
        Paste an email, meeting note, decision, or any organizational event.
        The AI will extract knowledge and update the graph.
      </p>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', flexShrink: 0 }}>
        {Object.keys(SAMPLES).map(key => (
          <button
            key={key}
            onClick={() => { if (inputRef.current) inputRef.current.value = SAMPLES[key] }}
            style={{
              fontSize: 12, padding: '5px 12px', borderRadius: 6,
              border: '1px dashed var(--border-strong)', background: 'transparent',
              color: 'var(--text-muted)', cursor: 'pointer',
              fontFamily: 'var(--font-body)', transition: 'all 0.15s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.borderStyle = 'solid'
              e.currentTarget.style.background = 'var(--accent-dim)'
              e.currentTarget.style.color = 'var(--accent)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderStyle = 'dashed'
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = 'var(--text-muted)'
            }}
          >
            Sample: {key}
          </button>
        ))}
      </div>

      <textarea
        ref={inputRef}
        placeholder="Paste an event here..."
        style={{
          width: '100%', minHeight: 160, flex: 1, padding: '12px 14px',
          border: '1px solid var(--border)', borderRadius: 10,
          background: 'var(--bg)', color: 'var(--text)',
          fontFamily: 'var(--font-body)', fontSize: 14, lineHeight: 1.5,
          resize: 'none', outline: 'none', transition: 'border-color 0.2s',
        }}
        onFocus={e => (e.target.style.borderColor = 'rgba(0,229,255,0.3)')}
        onBlur={e => (e.target.style.borderColor = '')}
      />

      <button
        onClick={submit}
        disabled={loading}
        style={{
          width: '100%', padding: 10, border: 'none', borderRadius: 8,
          background: 'linear-gradient(135deg, var(--accent), #0090a8)',
          color: 'var(--bg)', fontFamily: 'var(--font-body)',
          fontSize: 14, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s', opacity: loading ? 0.5 : 1, flexShrink: 0,
        }}
      >
        {loading ? 'Processing...' : 'Ingest Event'}
      </button>

      {loading && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: 12,
          borderRadius: 8, background: 'var(--accent-dim)',
          border: '1px solid rgba(0,229,255,0.1)', fontSize: 13, color: 'var(--accent)',
          flexShrink: 0,
        }}>
          <div style={{
            width: 16, height: 16, border: '2px solid rgba(0,229,255,0.2)',
            borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite',
          }} />
          AI is analyzing and updating the graph...
        </div>
      )}

      {result && (
        <div style={{
          padding: 12, background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 8, fontSize: 13, lineHeight: 1.6, color: 'var(--text-muted)',
          flexShrink: 0,
        }}>
          {result.created.length > 0 && (
            <div><span style={{ color: '#4ade80', fontWeight: 600 }}>Created:</span> {result.created.join(', ')}</div>
          )}
          {result.updated.length > 0 && (
            <div><span style={{ color: '#fb923c', fontWeight: 600 }}>Updated:</span> {result.updated.join(', ')}</div>
          )}
          <div style={{ marginTop: 8, fontStyle: 'italic' }}>{result.message}</div>
        </div>
      )}

      {trace && (
        <TraceAnimation
          trace={trace}
          onHighlightNodes={onHighlightNodes}
          onClose={() => { setTrace(null); onHighlightNodes([]) }}
        />
      )}
    </div>
  )
}
