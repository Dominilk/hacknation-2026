import { useState, useEffect } from 'react'
import { api, type NodeDetail } from '../api'

interface Props {
  name: string
  onClose: () => void
  onNodeClick: (name: string) => void
}

function renderContent(text: string, onNodeClick: (name: string) => void) {
  const parts = text.split(/(\[\[[^\]]+\]\])/)
  return parts.map((part, i) => {
    const match = part.match(/^\[\[([^\]]+)\]\]$/)
    if (match) {
      return (
        <span
          key={i}
          onClick={() => onNodeClick(match[1])}
          style={{
            color: 'var(--accent)', cursor: 'pointer',
            borderBottom: '1px dashed rgba(0,229,255,0.25)',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.borderBottomStyle = 'solid')}
          onMouseLeave={e => (e.currentTarget.style.borderBottomStyle = 'dashed')}
        >
          {match[1]}
        </span>
      )
    }
    return <span key={i}>{part}</span>
  })
}

function LinkChip({ name, variant, onClick }: { name: string; variant: 'out' | 'back'; onClick: () => void }) {
  const isOut = variant === 'out'
  return (
    <span
      onClick={onClick}
      style={{
        fontSize: 12, fontWeight: 500, padding: '3px 10px', borderRadius: 6,
        cursor: 'pointer', transition: 'all 0.15s',
        background: isOut ? 'var(--accent-dim)' : 'rgba(90,104,128,0.12)',
        color: isOut ? 'var(--accent)' : 'var(--text-muted)',
        border: `1px solid ${isOut ? 'rgba(0,229,255,0.1)' : 'rgba(90,104,128,0.1)'}`,
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = isOut ? 'rgba(0,229,255,0.18)' : 'rgba(90,104,128,0.2)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = isOut ? 'var(--accent-dim)' : 'rgba(90,104,128,0.12)'
      }}
    >
      {name}
    </span>
  )
}

export function NodePanel({ name, onClose, onNodeClick }: Props) {
  const [node, setNode] = useState<NodeDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.getNode(name)
      .then(setNode)
      .catch(() => setNode(null))
      .finally(() => setLoading(false))
  }, [name])

  const isEvent = name.startsWith('event-')
  const displayName = name.replace(/-/g, ' ')

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
            letterSpacing: '-0.02em', lineHeight: 1.2, marginBottom: 6,
            color: 'var(--text)',
          }}>
            {displayName}
          </div>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
            padding: '3px 10px', borderRadius: 5, letterSpacing: '0.02em',
            background: isEvent ? 'rgba(58,74,96,0.18)' : 'var(--accent-dim)',
            color: isEvent ? 'var(--text-muted)' : 'var(--accent)',
            border: `1px solid ${isEvent ? 'rgba(58,74,96,0.3)' : 'rgba(0,229,255,0.12)'}`,
          }}>
            {isEvent ? 'event' : 'knowledge'}
          </span>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: 'var(--text-dim)',
          cursor: 'pointer', fontSize: 18, lineHeight: 1, padding: '4px 8px',
        }}>&times;</button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-dim)', fontSize: 13 }}>
            <div style={{
              width: 16, height: 16, border: '2px solid rgba(0,229,255,0.2)',
              borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite',
            }} />
            Loading...
          </div>
        )}

        {!loading && !node && (
          <div style={{ color: 'var(--danger)', fontSize: 13 }}>Node not found</div>
        )}

        {!loading && node && (
          <>
            {/* Links */}
            {node.outlinks.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                  letterSpacing: '0.06em', textTransform: 'uppercase',
                  color: 'var(--text-dim)', marginBottom: 8,
                }}>Links to</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                  {node.outlinks.map(l => (
                    <LinkChip key={l} name={l} variant="out" onClick={() => onNodeClick(l)} />
                  ))}
                </div>
              </div>
            )}
            {node.backlinks.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                  letterSpacing: '0.06em', textTransform: 'uppercase',
                  color: 'var(--text-dim)', marginBottom: 8,
                }}>Referenced by</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                  {node.backlinks.map(l => (
                    <LinkChip key={l} name={l} variant="back" onClick={() => onNodeClick(l)} />
                  ))}
                </div>
              </div>
            )}

            {/* Content */}
            <div style={{
              paddingTop: (node.outlinks.length > 0 || node.backlinks.length > 0) ? 16 : 0,
              borderTop: (node.outlinks.length > 0 || node.backlinks.length > 0) ? '1px solid var(--border)' : 'none',
            }}>
              <pre style={{
                fontFamily: 'var(--font-body)', fontSize: 14, lineHeight: 1.75,
                color: 'var(--text-muted)', whiteSpace: 'pre-wrap', wordWrap: 'break-word',
              }}>
                {renderContent(node.content, onNodeClick)}
              </pre>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
