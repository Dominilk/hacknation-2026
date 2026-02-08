import { useState, useEffect, useRef, useCallback } from 'react'
import type { TraceStep } from '../api'

const ACTION_STYLES: Record<string, { color: string; label: string }> = {
  search: { color: '#00e5ff', label: 'SEARCH' },
  read: { color: '#818cf8', label: 'READ' },
  list_links: { color: '#818cf8', label: 'LINKS' },
  create: { color: '#4ade80', label: 'CREATE' },
  update: { color: '#fb923c', label: 'UPDATE' },
  recent_changes: { color: '#fbbf24', label: 'HISTORY' },
}
const FALLBACK = { color: '#5a6880', label: '?' }
const STEP_MS = 1200

interface Props {
  trace: TraceStep[]
  onHighlightNodes: (nodes: string[]) => void
  onClose: () => void
}

export function TraceAnimation({ trace, onHighlightNodes, onClose }: Props) {
  const [step, setStep] = useState(-1)
  const [playing, setPlaying] = useState(true)
  const listRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null)
  const total = trace.length

  const go = useCallback((i: number) => {
    const c = Math.max(-1, Math.min(i, total - 1))
    setStep(c)
    onHighlightNodes(c >= 0 ? trace[c].nodes : [])
  }, [trace, total, onHighlightNodes])

  // Auto-play
  useEffect(() => {
    if (!playing) return
    if (step >= total - 1) { setPlaying(false); return }
    timerRef.current = setTimeout(() => go(step + 1), step === -1 ? 400 : STEP_MS)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [playing, step, total, go])

  // Auto-scroll to current step
  useEffect(() => {
    if (step < 0 || !listRef.current) return
    const el = listRef.current.children[step] as HTMLElement | undefined
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [step])

  // Clear highlights on unmount
  useEffect(() => () => onHighlightNodes([]), [onHighlightNodes])

  const toggle = () => {
    if (step >= total - 1) { go(-1); setPlaying(true) }
    else setPlaying(p => !p)
  }

  const pct = total > 0 ? Math.max(0, ((step + 1) / total) * 100) : 0

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      background: 'var(--bg)', border: '1px solid var(--border)',
      borderRadius: 10, overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px',
        background: 'linear-gradient(135deg, rgba(0,229,255,0.06), rgba(129,140,248,0.04))',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--accent)', padding: '2px 7px', borderRadius: 4,
            background: 'var(--accent-dim)', border: '1px solid rgba(0,229,255,0.15)',
          }}>Agent Trace</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)',
          }}>{step >= 0 ? step + 1 : 0} / {total}</span>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-dim)', fontSize: 16, lineHeight: 1, padding: '2px 4px',
        }}>&times;</button>
      </div>

      {/* Progress bar */}
      <div style={{ height: 2, background: 'var(--surface-2)' }}>
        <div style={{
          height: '100%', width: `${pct}%`,
          background: 'linear-gradient(90deg, var(--accent), #818cf8)',
          transition: 'width 0.3s ease',
        }} />
      </div>

      {/* Controls */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 4, padding: '8px 14px', borderBottom: '1px solid var(--border)',
      }}>
        <CtrlBtn label="⏮" onClick={() => { setPlaying(false); go(0) }} disabled={total === 0} />
        <CtrlBtn label="◀" onClick={() => { setPlaying(false); go(step - 1) }} disabled={step <= 0} />
        <CtrlBtn
          label={playing ? '⏸' : (step >= total - 1 ? '↻' : '▶')}
          onClick={toggle} disabled={total === 0} primary
        />
        <CtrlBtn label="▶" onClick={() => { setPlaying(false); go(step + 1) }} disabled={step >= total - 1} />
        <CtrlBtn label="⏭" onClick={() => { setPlaying(false); go(total - 1) }} disabled={total === 0} />
      </div>

      {/* Step list */}
      <div ref={listRef} style={{ maxHeight: 280, overflowY: 'auto', padding: '6px 0' }}>
        {trace.map((s, i) => {
          const st = ACTION_STYLES[s.action] ?? FALLBACK
          const active = i === step
          const past = i < step
          const future = i > step
          return (
            <div
              key={i}
              onClick={() => { setPlaying(false); go(i) }}
              style={{
                display: 'flex', gap: 10, padding: '8px 14px', cursor: 'pointer',
                background: active ? 'rgba(0,229,255,0.06)' : 'transparent',
                borderLeft: active ? `2px solid ${st.color}` : '2px solid transparent',
                opacity: future ? 0.35 : 1,
                transition: 'all 0.2s',
              }}
            >
              <div style={{
                flexShrink: 0, width: 26, height: 26, borderRadius: 6,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)',
                color: active || past ? st.color : 'var(--text-dim)',
                background: active ? `${st.color}18` : 'transparent',
                border: `1px solid ${active ? `${st.color}40` : past ? `${st.color}20` : 'var(--border)'}`,
              }}>{st.label.slice(0, 2)}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                    color: active || past ? st.color : 'var(--text-dim)',
                    textTransform: 'uppercase',
                  }}>{s.action}</span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)',
                  }}>{s.ts.toFixed(1)}s</span>
                </div>
                {s.nodes.length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 3 }}>
                    {s.nodes.slice(0, 3).map(n => (
                      <span key={n} style={{
                        fontFamily: 'var(--font-mono)', fontSize: 10,
                        padding: '1px 6px', borderRadius: 4,
                        background: active ? `${st.color}15` : 'var(--surface-2)',
                        color: active ? st.color : 'var(--text-muted)',
                        border: `1px solid ${active ? `${st.color}25` : 'var(--border)'}`,
                        maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>{n.replace(/-/g, ' ')}</span>
                    ))}
                    {s.nodes.length > 3 && (
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-dim)' }}>
                        +{s.nodes.length - 3}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CtrlBtn({ label, onClick, disabled, primary }: {
  label: string; onClick: () => void; disabled?: boolean; primary?: boolean
}) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      width: primary ? 36 : 30, height: primary ? 36 : 30,
      borderRadius: primary ? 10 : 6,
      border: primary ? '1px solid rgba(0,229,255,0.2)' : '1px solid var(--border)',
      background: primary ? 'var(--accent-dim)' : 'transparent',
      color: disabled ? 'var(--text-dim)' : primary ? 'var(--accent)' : 'var(--text-muted)',
      cursor: disabled ? 'default' : 'pointer',
      fontSize: primary ? 16 : 13,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      opacity: disabled ? 0.4 : 1,
    }}>{label}</button>
  )
}
