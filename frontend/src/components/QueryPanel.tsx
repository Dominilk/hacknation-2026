import { useState, useRef } from 'react'
import Markdown from 'react-markdown'
import { api } from '../api'

const SCENARIOS = [
  {
    label: 'Executive Briefing',
    question: "I'm the CEO. Give me a complete status update — what are the critical issues, key decisions, and what needs my attention right now?",
  },
  {
    label: 'New Analyst Onboarding',
    question: "I just joined the government relations team. Bring me up to speed on everything — the California energy situation, key stakeholders, and what's happening.",
  },
  {
    label: 'Risk Assessment',
    question: 'What are the key risks, conflicts, and contradictions in our current operations? Flag anything that seems problematic.',
  },
  {
    label: 'Stakeholder Map',
    question: 'Who are the key people in the organization and how are they connected? What does each person focus on?',
  },
]

interface Props {
  onHighlightNodes: (nodes: string[]) => void
  onNodeClick: (name: string) => void
  onStatusChange: (msg: string) => void
}

function preprocessWikilinks(md: string): string {
  return md.replace(/\[\[([^\]]+)\]\]/g, '[$1](#node:$1)')
}

export function QueryPanel({ onHighlightNodes, onNodeClick, onStatusChange }: Props) {
  const [answer, setAnswer] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const submit = async (question: string) => {
    if (!question.trim() || loading) return
    setLoading(true)
    setAnswer(null)
    onHighlightNodes([])
    onStatusChange('Traversing the knowledge graph...')
    try {
      const res = await api.query(question)
      setAnswer(res.answer)
      const refs = [...res.answer.matchAll(/\[\[([^\]]+)\]\]/g)].map(m => m[1])
      onHighlightNodes(refs)
      onStatusChange(`Query complete — ${refs.length} nodes referenced`)
    } catch (err) {
      setAnswer(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`)
      onStatusChange('Query failed')
    } finally {
      setLoading(false)
    }
  }

  const runScenario = (question: string) => {
    if (inputRef.current) inputRef.current.value = question
    submit(question)
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 20, gap: 16 }}>
      <h3 style={{
        fontFamily: 'var(--font-display)', fontSize: 16, fontWeight: 500,
        color: 'var(--text)', flexShrink: 0,
      }}>Ask the knowledge graph</h3>

      <textarea
        ref={inputRef}
        placeholder="What are the key decisions? Who is involved in...?"
        style={{
          width: '100%', minHeight: 80, padding: '12px 14px',
          border: '1px solid var(--border)', borderRadius: 10,
          background: 'var(--bg)', color: 'var(--text)',
          fontFamily: 'var(--font-body)', fontSize: 14, lineHeight: 1.5,
          resize: 'vertical', outline: 'none', transition: 'border-color 0.2s',
          flexShrink: 0,
        }}
        onFocus={e => (e.target.style.borderColor = 'rgba(0,229,255,0.3)')}
        onBlur={e => (e.target.style.borderColor = '')}
        onKeyDown={e => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            submit(e.currentTarget.value)
          }
        }}
      />

      <button
        onClick={() => inputRef.current && submit(inputRef.current.value)}
        disabled={loading}
        style={{
          width: '100%', padding: 10, border: 'none', borderRadius: 8,
          background: 'linear-gradient(135deg, var(--accent), #0090a8)',
          color: 'var(--bg)', fontFamily: 'var(--font-body)',
          fontSize: 14, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s', letterSpacing: '0.01em',
          opacity: loading ? 0.5 : 1, flexShrink: 0,
        }}
      >
        {loading ? 'Thinking...' : 'Ask'}
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
          Traversing the knowledge graph...
        </div>
      )}

      {answer && (
        <div style={{
          flex: 1, overflow: 'auto', padding: 18,
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10,
        }}>
          <div className="md-content">
            <Markdown
              components={{
                a: ({ href, children }) => {
                  if (href?.startsWith('#node:')) {
                    const nodeName = href.slice(6)
                    return (
                      <span
                        onClick={() => onNodeClick(nodeName)}
                        style={{
                          fontFamily: 'var(--font-mono)', fontSize: 12,
                          padding: '1px 6px', borderRadius: 3,
                          background: 'var(--accent-dim)', color: 'var(--accent)',
                          cursor: 'pointer', transition: 'background 0.15s',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,229,255,0.2)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'var(--accent-dim)')}
                      >
                        {children}
                      </span>
                    )
                  }
                  return (
                    <a href={href} target="_blank" rel="noopener noreferrer" style={{
                      color: 'var(--accent)', textDecoration: 'none',
                      borderBottom: '1px solid rgba(0,229,255,0.25)',
                    }}>{children}</a>
                  )
                },
              }}
            >
              {preprocessWikilinks(answer)}
            </Markdown>
          </div>
        </div>
      )}

      {/* Demo scenarios — hidden when answer is showing to give it full space */}
      {!answer && !loading && (
        <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border)', flexShrink: 0 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
            letterSpacing: '0.06em', textTransform: 'uppercase',
            color: 'var(--text-dim)', marginBottom: 8,
          }}>Demo scenarios</div>
          {SCENARIOS.map(s => (
            <button
              key={s.label}
              onClick={() => runScenario(s.question)}
              style={{
                display: 'block', width: '100%', padding: '8px 12px', marginBottom: 6,
                border: '1px solid var(--border)', borderRadius: 8,
                background: 'var(--surface)', color: 'var(--text-muted)',
                fontFamily: 'var(--font-body)', fontSize: 13, textAlign: 'left',
                cursor: 'pointer', transition: 'all 0.15s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'var(--surface-2)'
                e.currentTarget.style.borderColor = 'var(--border-strong)'
                e.currentTarget.style.color = 'var(--text)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'var(--surface)'
                e.currentTarget.style.borderColor = ''
                e.currentTarget.style.color = 'var(--text-muted)'
              }}
            >
              <strong style={{ color: 'var(--accent)', fontWeight: 600, fontSize: 12 }}>{s.label}</strong>
              <span style={{ display: 'block', marginTop: 2, fontSize: 12, lineHeight: 1.4 }}>
                {s.question.slice(0, 70)}...
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
