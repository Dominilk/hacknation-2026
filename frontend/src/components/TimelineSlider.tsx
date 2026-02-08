import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import type { GraphCommit } from '../api'

interface Props {
  commits: GraphCommit[]
  onChange: (visibleNodes: Set<string> | null) => void
}

export function TimelineSlider({ commits, onChange }: Props) {
  const [position, setPosition] = useState(-1) // -1 = latest (show all)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [playing, setPlaying] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

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

  const goTo = useCallback((val: number) => {
    setPosition(val)
    if (val >= chronological.length - 1) {
      onChange(null)
    } else {
      onChange(cumulativeNodes[val] || null)
    }
  }, [chronological.length, cumulativeNodes, onChange])

  // Autoplay: advance every 1.5s, stop at the end
  useEffect(() => {
    if (!playing) {
      if (intervalRef.current) clearInterval(intervalRef.current)
      intervalRef.current = null
      return
    }
    const startPos = position === -1 ? 0 : position
    if (startPos === 0 && position === -1) goTo(0)

    intervalRef.current = setInterval(() => {
      setPosition(prev => {
        const cur = prev === -1 ? 0 : prev
        const next = cur + 1
        if (next >= chronological.length) {
          setPlaying(false)
          return prev
        }
        if (next >= chronological.length - 1) {
          onChange(null)
        } else {
          onChange(cumulativeNodes[next] || null)
        }
        return next
      })
    }, 1500)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [playing, chronological.length, cumulativeNodes, onChange, goTo, position])

  if (chronological.length < 2) return null

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPlaying(false)
    goTo(parseInt(e.target.value))
  }

  const togglePlay = () => {
    if (playing) {
      setPlaying(false)
    } else {
      // If at the end, restart from beginning
      const cur = position === -1 ? chronological.length - 1 : position
      if (cur >= chronological.length - 1) goTo(0)
      setPlaying(true)
    }
  }

  const displayIdx = hoveredIdx !== null
    ? hoveredIdx
    : (position === -1 ? chronological.length - 1 : position)
  const displayCommit = chronological[displayIdx]
  const currentPos = position === -1 ? chronological.length - 1 : position
  const pct = (currentPos / (chronological.length - 1)) * 100

  // Full commit message has multiple lines
  const fullMessage = displayCommit?.message ?? ''
  const firstLine = fullMessage.split('\n')[0]
  const hasMoreLines = fullMessage.includes('\n') && fullMessage.trim() !== firstLine.trim()

  return (
    <div style={{
      padding: '8px 20px 12px',
      borderTop: '1px solid var(--border)',
      background: 'var(--surface)',
      flexShrink: 0,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4,
      }}>
        {/* Play/pause */}
        <button
          onClick={togglePlay}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: playing ? 'var(--accent)' : 'var(--text-dim)',
            fontSize: 12, padding: 0, flexShrink: 0,
            transition: 'color 0.15s', lineHeight: 1,
          }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')}
          onMouseLeave={e => (e.currentTarget.style.color = playing ? 'var(--accent)' : 'var(--text-dim)')}
          title={playing ? 'Pause' : 'Play timeline'}
        >
          {playing ? '\u275A\u275A' : '\u25B6'}
        </button>

        <span style={{
          fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em',
          color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontWeight: 600,
          flexShrink: 0,
        }}>
          Timeline
        </span>
        {displayCommit && (
          <span
            onClick={() => hasMoreLines && setExpanded(!expanded)}
            style={{
              fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
              cursor: hasMoreLines ? 'pointer' : 'default',
              display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            {displayCommit.timestamp.slice(0, 10)} — {firstLine.slice(0, 80)}
            {hasMoreLines && (
              <span style={{
                display: 'inline-block', fontSize: 8, flexShrink: 0,
                transition: 'transform 0.2s',
                transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
              }}>&#9654;</span>
            )}
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

      {/* Expanded commit message */}
      {expanded && hasMoreLines && (
        <div style={{
          fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)',
          lineHeight: 1.6, padding: '6px 0 6px 24px',
          whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto',
        }}>
          {fullMessage.split('\n').slice(1).join('\n').trim()}
        </div>
      )}

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
