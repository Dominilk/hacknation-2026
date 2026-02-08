import { useState, useEffect } from 'react'
import Markdown from 'react-markdown'
import { api, type NodeDetail } from '../api'

interface Props {
  name: string
  onClose: () => void
  onNodeClick: (name: string) => void
}

// Convert [[wikilinks]] to markdown links before react-markdown parses them
// This way wikilinks work inside bold, lists, headers, etc.
function preprocessWikilinks(md: string): string {
  return md.replace(/\[\[([^\]]+)\]\]/g, '[$1](#node:$1)')
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

function stripFrontmatter(content: string): string {
  if (content.startsWith('---\n')) {
    const end = content.indexOf('\n---\n', 4)
    if (end !== -1) return content.slice(end + 5).trim()
  }
  return content
}

export function NodePanel({ name, onClose, onNodeClick }: Props) {
  const [node, setNode] = useState<NodeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [linksExpanded, setLinksExpanded] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.getNode(name)
      .then(data => setNode(data.error ? null : data))
      .catch(() => setNode(null))
      .finally(() => setLoading(false))
  }, [name])

  const isEvent = name.startsWith('event-')
  const displayName = name.replace(/-/g, ' ')
  const processedContent = node?.content
    ? preprocessWikilinks(stripFrontmatter(node.content))
    : ''
  const hasLinks = node && (node.outlinks.length > 0 || node.backlinks.length > 0)

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
        padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontFamily: 'var(--font-display)', fontSize: 18, fontWeight: 700,
            letterSpacing: '-0.02em', lineHeight: 1.3, marginBottom: 8,
            color: 'var(--text)',
          }}>
            {displayName}
          </div>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
            padding: '2px 8px', borderRadius: 4, letterSpacing: '0.04em',
            textTransform: 'uppercase',
            background: isEvent ? 'rgba(58,74,96,0.18)' : 'var(--accent-dim)',
            color: isEvent ? 'var(--text-muted)' : 'var(--accent)',
            border: `1px solid ${isEvent ? 'rgba(58,74,96,0.3)' : 'rgba(0,229,255,0.12)'}`,
          }}>
            {isEvent ? 'event' : 'knowledge'}
          </span>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: 'var(--text-dim)',
          cursor: 'pointer', fontSize: 20, lineHeight: 1, padding: '2px 6px',
          flexShrink: 0,
        }}>&times;</button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
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
            {/* Markdown content first — the main thing users want to read */}
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
                            color: 'var(--accent)', cursor: 'pointer',
                            borderBottom: '1px dashed rgba(0,229,255,0.25)',
                          }}
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
                  code: ({ children, className }) => {
                    const isBlock = className?.startsWith('language-') || String(children).includes('\n')
                    if (isBlock) {
                      return (
                        <pre style={{
                          background: 'var(--bg)', border: '1px solid var(--border)',
                          borderRadius: 8, padding: 14, marginBottom: 12,
                          overflow: 'auto', fontSize: 12, lineHeight: 1.6,
                          fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
                        }}>
                          <code>{children}</code>
                        </pre>
                      )
                    }
                    return (
                      <code style={{
                        background: 'rgba(0,229,255,0.06)', padding: '1px 5px',
                        borderRadius: 3, fontSize: '0.9em',
                        fontFamily: 'var(--font-mono)', color: 'var(--accent)',
                      }}>{children}</code>
                    )
                  },
                  pre: ({ children }) => <>{children}</>,
                }}
              >
                {processedContent}
              </Markdown>
            </div>

            {/* Links — collapsible, below content */}
            {hasLinks && (
              <div style={{ marginTop: 16 }}>
                <button
                  onClick={() => setLinksExpanded(!linksExpanded)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    background: 'none', border: 'none', cursor: 'pointer',
                    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                    letterSpacing: '0.06em', textTransform: 'uppercase',
                    color: 'var(--text-dim)', padding: 0, marginBottom: linksExpanded ? 8 : 0,
                    transition: 'color 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-dim)')}
                >
                  <span style={{
                    display: 'inline-block', transition: 'transform 0.2s',
                    transform: linksExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    fontSize: 8,
                  }}>&#9654;</span>
                  Links ({node.outlinks.length + node.backlinks.length})
                </button>
                {linksExpanded && (
                  <div style={{
                    padding: 12, borderRadius: 8,
                    background: 'var(--surface)', border: '1px solid var(--border)',
                  }}>
                    {node.outlinks.length > 0 && (
                      <div style={{ marginBottom: node.backlinks.length > 0 ? 10 : 0 }}>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                          letterSpacing: '0.06em', textTransform: 'uppercase',
                          color: 'var(--text-dim)', marginBottom: 6,
                        }}>Links to</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {node.outlinks.map(l => (
                            <LinkChip key={l} name={l} variant="out" onClick={() => onNodeClick(l)} />
                          ))}
                        </div>
                      </div>
                    )}
                    {node.backlinks.length > 0 && (
                      <div>
                        <div style={{
                          fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                          letterSpacing: '0.06em', textTransform: 'uppercase',
                          color: 'var(--text-dim)', marginBottom: 6,
                        }}>Referenced by</div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {node.backlinks.map(l => (
                            <LinkChip key={l} name={l} variant="back" onClick={() => onNodeClick(l)} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
