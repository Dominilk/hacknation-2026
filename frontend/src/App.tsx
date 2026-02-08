import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { GraphView, type GraphViewHandle } from './components/GraphView'
import { NodePanel } from './components/NodePanel'
import { QueryPanel } from './components/QueryPanel'
import { IngestPanel } from './components/IngestPanel'
import { TimelineSlider } from './components/TimelineSlider'
import { api, type GraphData, type GraphCommit } from './api'

type Tab = 'explore' | 'ask' | 'ingest'

export default function App() {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [commits, setCommits] = useState<GraphCommit[]>([])
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('ask')
  const [timelineFilter, setTimelineFilter] = useState<Set<string> | null>(null)
  const [highlightedNodes, setHighlightedNodes] = useState<string[]>([])
  const [status, setStatus] = useState('Ready')
  const graphRef = useRef<GraphViewHandle>(null)

  // Filter graph data by timeline position
  const filteredData = useMemo(() => {
    if (!graphData || !timelineFilter) return graphData
    const visible = timelineFilter
    const nodes = graphData.nodes.filter(n => visible.has(n.name))
    const nodeSet = new Set(nodes.map(n => n.name))
    const edges = graphData.edges.filter(e => nodeSet.has(e.source) && nodeSet.has(e.target))
    return { nodes, edges }
  }, [graphData, timelineFilter])

  const refreshGraph = useCallback(async () => {
    try {
      const [data, commitData] = await Promise.all([api.getGraph(), api.getCommits()])
      setGraphData(data)
      setCommits(commitData)
      setStatus(`Knowledge graph loaded — ${data.nodes.length} nodes`)
    } catch {
      setStatus('Failed to connect to backend')
    }
  }, [])

  useEffect(() => { refreshGraph() }, [refreshGraph])

  const handleNodeSelect = useCallback((name: string | null) => {
    setSelectedNode(name)
    if (name) {
      setActiveTab('explore')
      setHighlightedNodes([])
    }
  }, [])

  const handleNodeClick = useCallback((name: string) => {
    setSelectedNode(name)
    setActiveTab('explore')
  }, [])

  const handleIngestComplete = useCallback(() => {
    refreshGraph()
  }, [refreshGraph])

  const nodeCount = graphData?.nodes.length ?? 0
  const edgeCount = graphData?.edges.length ?? 0

  return (
    <div style={{
      display: 'grid',
      gridTemplateRows: '52px 1fr 40px',
      gridTemplateColumns: '1fr 420px',
      height: '100vh',
    }}>
      {/* ── Top Bar ── */}
      <header style={{
        gridColumn: '1 / -1',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px',
        background: 'linear-gradient(180deg, rgba(10,16,32,0.98), rgba(10,16,32,0.85))',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border)',
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'linear-gradient(135deg, var(--accent), #0090a8)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700, color: 'var(--bg)',
              boxShadow: '0 0 20px rgba(0,229,255,0.3)',
            }}>AI</div>
            <div style={{
              fontFamily: 'var(--font-display)', fontSize: 17, fontWeight: 500,
              letterSpacing: '-0.01em', color: 'var(--text)',
            }}>
              Chief of <em style={{ fontStyle: 'italic', color: 'var(--accent)', fontWeight: 300 }}>Staff</em>
            </div>
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: 'var(--accent)', padding: '3px 10px', borderRadius: 4,
            background: 'var(--accent-dim)', border: '1px solid rgba(0,229,255,0.12)',
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: 'var(--accent)', animation: 'pulse-dot 2s ease-in-out infinite',
            }} />
            Live
          </div>
        </div>
        <div style={{
          display: 'flex', gap: 24,
          fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)',
        }}>
          <div><strong style={{ color: 'var(--text)', fontWeight: 600 }}>{nodeCount}</strong> nodes</div>
          <div><strong style={{ color: 'var(--text)', fontWeight: 600 }}>{edgeCount}</strong> edges</div>
        </div>
      </header>

      {/* ── Graph Area ── */}
      <div style={{ position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <GraphView
            ref={graphRef}
            data={filteredData}
            onNodeSelect={handleNodeSelect}
            selectedNode={selectedNode}
            highlightedNodes={highlightedNodes}
          />
        </div>
        <TimelineSlider commits={commits} onChange={setTimelineFilter} />
      </div>

      {/* ── Sidebar ── */}
      <aside style={{
        display: 'flex', flexDirection: 'column',
        background: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        overflow: 'hidden',
      }}>
        {/* Tabs */}
        <nav style={{
          display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0,
        }}>
          {(['explore', 'ask', 'ingest'] as Tab[]).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                flex: 1, padding: '12px 0',
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
                letterSpacing: '0.04em', textTransform: 'uppercase', textAlign: 'center',
                color: activeTab === tab ? 'var(--accent)' : 'var(--text-muted)',
                background: 'none', border: 'none', cursor: 'pointer',
                transition: 'color 0.2s', position: 'relative',
              }}
            >
              {tab}
              {activeTab === tab && (
                <span style={{
                  position: 'absolute', bottom: 0, left: '20%', right: '20%',
                  height: 2, background: 'var(--accent)', borderRadius: 1,
                }} />
              )}
            </button>
          ))}
        </nav>

        {/* Tab content */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {activeTab === 'explore' && (
            selectedNode ? (
              <NodePanel
                name={selectedNode}
                onClose={() => setSelectedNode(null)}
                onNodeClick={handleNodeClick}
              />
            ) : (
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', height: '100%', gap: 12, padding: 40, textAlign: 'center',
              }}>
                <div style={{ fontSize: 36, opacity: 0.3 }}>&#9673;</div>
                <p style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  Click a node on the graph to explore its knowledge, connections, and context.
                </p>
              </div>
            )
          )}
          {activeTab === 'ask' && (
            <div style={{ height: '100%', overflow: 'auto' }}>
              <QueryPanel
                onHighlightNodes={setHighlightedNodes}
                onNodeClick={handleNodeClick}
                onStatusChange={setStatus}
              />
            </div>
          )}
          {activeTab === 'ingest' && (
            <div style={{ height: '100%', overflow: 'auto' }}>
              <IngestPanel
                onIngestComplete={handleIngestComplete}
                onStatusChange={setStatus}
              />
            </div>
          )}
        </div>
      </aside>

      {/* ── Status Bar ── */}
      <footer style={{
        gridColumn: '1 / -1',
        display: 'flex', alignItems: 'center', padding: '0 16px', gap: 16,
        background: 'var(--surface)',
        borderTop: '1px solid var(--border)',
        fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)',
      }}>
        <div style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {status}
        </div>
        <div>Enron Dataset &middot; Jun–Nov 2001</div>
      </footer>
    </div>
  )
}
