import { useState, useMemo } from 'react'
import type { GraphCommit } from '../api'

interface Props {
  commits: GraphCommit[]
  onChange: (visibleNodes: Set<string> | null) => void
}

export function TimelineSlider({ commits, onChange }: Props) {
  const [position, setPosition] = useState(-1) // -1 = latest (show all)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  // Commits come newest-first from git log; reverse for chronological
  const chronological = useMemo(() => [...commits].reverse(), [commits])

  // Build cumulative node sets for each commit position
  const cumulativeNodes = useMemo(() => {
    const result: Set<string>[] = []
    const cumulative = new Set<string>()
    for (const commit of chronological) {
      for (const f of commit.files_changed) {
        if (f.startsWith('nodes/') && f.endsWith('.md')) {
          cumulative.add(f.replace('nodes/', '').replace('.md', ''))
        }
      }
      result.push(new Set(cumulative))
    }
    return result
  }, [chronological])

  if (chronological.length < 2) return null

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value)
    setPosition(val)
    if (val >= chronological.length - 1) {
      onChange(null) // latest = show all
    } else {
      onChange(cumulativeNodes[val] || null)
    }
  }

  const displayIdx = hoveredIdx !== null
    ? hoveredIdx
    : (position === -1 ? chronological.length - 1 : position)
  const displayCommit = chronological[displayIdx]
  const currentPos = position === -1 ? chronological.length - 1 : position
  const pct = (currentPos / (chronological.length - 1)) * 100

  return (
    <div style={{
      padding: '8px 20px 12px',
      borderTop: '1px solid var(--border)',
      background: 'var(--surface)',
      flexShrink: 0,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4,
      }}>
        <span style={{
          fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em',
          color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontWeight: 600,
          flexShrink: 0,
        }}>
          Timeline
        </span>
        {displayCommit && (
          <span style={{
            fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
          }}>
            {displayCommit.timestamp.slice(0, 10)} — {displayCommit.message.slice(0, 80)}
          </span>
        )}
        {cumulativeNodes[displayIdx] && (
          <span style={{
            fontSize: 10, color: 'var(--accent)', fontFamily: 'var(--font-mono)',
            flexShrink: 0,
          }}>
            {cumulativeNodes[displayIdx].size} nodes
          </span>
        )}
      </div>
      <input
        type="range"
        min={0}
        max={chronological.length - 1}
        value={currentPos}
        onChange={handleChange}
        onMouseMove={e => {
          const rect = e.currentTarget.getBoundingClientRect()
          const p = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
          setHoveredIdx(Math.round(p * (chronological.length - 1)))
        }}
        onMouseLeave={() => setHoveredIdx(null)}
        style={{
          width: '100%', height: 4,
          appearance: 'none', WebkitAppearance: 'none',
          background: `linear-gradient(to right, var(--accent) ${pct}%, var(--surface-3) ${pct}%)`,
          borderRadius: 2, outline: 'none', cursor: 'pointer',
        }}
      />
    </div>
  )
}
