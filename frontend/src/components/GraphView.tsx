import { useRef, useEffect, useImperativeHandle, forwardRef, useCallback } from 'react'
import * as d3 from 'd3'
import type { GraphData } from '../api'

const COLORS = [
  '#00e5ff', '#ff6b9d', '#c084fc', '#fb923c', '#4ade80',
  '#fbbf24', '#818cf8', '#f43f5e', '#14b8a6', '#22d3ee',
]
const EVENT_COLOR = '#3a4a60'

function communityColor(c: number) { return COLORS[c % COLORS.length] }
function nodeRadius(d: SimNode) {
  if (d.isEvent) return 6
  return Math.max(8, Math.min(24, 8 + d.pagerank * 5000))
}
function formatLabel(id: string) {
  if (id.startsWith('event-')) return ''
  return id.replace(/-/g, ' ').slice(0, 24)
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string
  pagerank: number
  community: number
  isEvent: boolean
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {}

interface D3State {
  nodes: SimNode[]
  links: SimLink[]
  nodeEls: d3.Selection<SVGCircleElement, SimNode, SVGGElement, unknown>
  linkEls: d3.Selection<SVGLineElement, SimLink, SVGGElement, unknown>
  labelEls: d3.Selection<SVGTextElement, SimNode, SVGGElement, unknown>
  haloEls: d3.Selection<SVGCircleElement, SimNode, SVGGElement, unknown>
}

export interface GraphViewHandle {
  refresh: () => void
}

interface Props {
  data: GraphData | null
  onNodeSelect: (name: string | null) => void
  selectedNode: string | null
  highlightedNodes: string[]
}

export const GraphView = forwardRef<GraphViewHandle, Props>(
  ({ data, onNodeSelect, selectedNode, highlightedNodes }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const svgRef = useRef<SVGSVGElement | null>(null)
    const simRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null)
    const d3Ref = useRef<D3State | null>(null)
    const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
    const tooltipRef = useRef<HTMLDivElement>(null)

    const renderGraph = useCallback((graphData: GraphData) => {
      if (!containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const width = rect.width
      const height = rect.height
      if (width === 0 || height === 0) return

      // Tear down previous
      if (simRef.current) simRef.current.stop()
      if (svgRef.current) d3.select(svgRef.current).remove()

      const svg = d3.select(containerRef.current)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('display', 'block')
      svgRef.current = svg.node()

      // Glow filters
      const defs = svg.append('defs')
      COLORS.forEach((color, i) => {
        const f = defs.append('filter')
          .attr('id', `glow-${i}`)
          .attr('x', '-50%').attr('y', '-50%')
          .attr('width', '200%').attr('height', '200%')
        f.append('feGaussianBlur').attr('stdDeviation', 5).attr('result', 'blur')
        f.append('feFlood').attr('flood-color', color).attr('flood-opacity', 0.45)
        f.append('feComposite').attr('in2', 'blur').attr('operator', 'in')
        const m = f.append('feMerge')
        m.append('feMergeNode')
        m.append('feMergeNode').attr('in', 'SourceGraphic')
      })

      const g = svg.append('g')

      // Zoom
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.15, 4])
        .on('zoom', (e) => g.attr('transform', e.transform))
      svg.call(zoom)
      svg.call(zoom.transform,
        d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8).translate(-width / 2, -height / 2))
      zoomRef.current = zoom

      // Transform data
      const nodes: SimNode[] = graphData.nodes.map(n => ({
        id: n.name,
        pagerank: n.pagerank,
        community: n.community,
        isEvent: n.name.startsWith('event-'),
      }))
      const nodeSet = new Set(nodes.map(n => n.id))
      const links: SimLink[] = graphData.edges
        .filter(e => nodeSet.has(e.source) && nodeSet.has(e.target))
        .map(e => ({ source: e.source, target: e.target }))

      // Simulation
      const sim = d3.forceSimulation(nodes)
        .force('link', d3.forceLink<SimNode, SimLink>(links).id(d => d.id).distance(100).strength(0.35))
        .force('charge', d3.forceManyBody().strength(-400))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide<SimNode>().radius(d => nodeRadius(d) + 10))
      simRef.current = sim

      // Edges
      const linkEls = g.append('g')
        .selectAll<SVGLineElement, SimLink>('line')
        .data(links)
        .join('line')
        .attr('stroke', '#0d1a30')
        .attr('stroke-width', 1.2)
        .attr('opacity', 0)

      // Halos (glow circles behind knowledge nodes)
      const haloEls = g.append('g')
        .selectAll<SVGCircleElement, SimNode>('circle')
        .data(nodes.filter(n => !n.isEvent))
        .join('circle')
        .attr('r', d => nodeRadius(d) + 8)
        .attr('fill', d => communityColor(d.community))
        .attr('opacity', 0)

      // Nodes
      const nodeEls = g.append('g')
        .selectAll<SVGCircleElement, SimNode>('circle')
        .data(nodes)
        .join('circle')
        .attr('r', 0)
        .attr('fill', d => d.isEvent ? EVENT_COLOR : communityColor(d.community))
        .attr('stroke', d => d.isEvent ? EVENT_COLOR : communityColor(d.community))
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.25)
        .attr('filter', d => d.isEvent ? null : `url(#glow-${d.community % COLORS.length})`)
        .attr('opacity', 0)
        .style('cursor', 'pointer')
        .on('click', (e, d) => { e.stopPropagation(); onNodeSelect(d.id) })
        .on('mouseover', function (event, d) {
          if (tooltipRef.current) {
            tooltipRef.current.textContent = d.id.replace(/-/g, ' ')
            tooltipRef.current.style.opacity = '1'
            tooltipRef.current.style.left = event.pageX + 14 + 'px'
            tooltipRef.current.style.top = event.pageY - 14 + 'px'
          }
        })
        .on('mousemove', function (event) {
          if (tooltipRef.current) {
            tooltipRef.current.style.left = event.pageX + 14 + 'px'
            tooltipRef.current.style.top = event.pageY - 14 + 'px'
          }
        })
        .on('mouseout', function () {
          if (tooltipRef.current) tooltipRef.current.style.opacity = '0'
        })
        .call(d3.drag<SVGCircleElement, SimNode>()
          .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
          .on('end', (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
        )

      // Labels
      const labelEls = g.append('g')
        .selectAll<SVGTextElement, SimNode>('text')
        .data(nodes)
        .join('text')
        .text(d => formatLabel(d.id))
        .attr('font-family', 'Outfit, sans-serif')
        .attr('font-size', 11)
        .attr('font-weight', 500)
        .attr('fill', '#5a6880')
        .attr('dx', d => nodeRadius(d) + 6)
        .attr('dy', 4)
        .style('pointer-events', 'none')
        .attr('opacity', 0)

      // Entry animation
      nodeEls.transition()
        .delay((_, i) => i * 20)
        .duration(500)
        .ease(d3.easeBackOut.overshoot(1.2))
        .attr('r', d => nodeRadius(d))
        .attr('opacity', 1)
      linkEls.transition().delay(300).duration(600).attr('opacity', 0.2)
      labelEls.transition().delay(500).duration(400).attr('opacity', 0.8)

      // Tick
      sim.on('tick', () => {
        linkEls
          .attr('x1', d => ((d.source as SimNode).x ?? 0))
          .attr('y1', d => ((d.source as SimNode).y ?? 0))
          .attr('x2', d => ((d.target as SimNode).x ?? 0))
          .attr('y2', d => ((d.target as SimNode).y ?? 0))
        nodeEls.attr('cx', d => d.x ?? 0).attr('cy', d => d.y ?? 0)
        haloEls.attr('cx', d => d.x ?? 0).attr('cy', d => d.y ?? 0)
        labelEls.attr('x', d => d.x ?? 0).attr('y', d => d.y ?? 0)
      })

      // Click background to deselect
      svg.on('click', () => onNodeSelect(null))

      d3Ref.current = { nodes, links, nodeEls, linkEls, labelEls, haloEls }
    }, [onNodeSelect])

    // Render on data change
    useEffect(() => {
      if (!data || data.nodes.length === 0) {
        d3Ref.current = null
        return
      }
      renderGraph(data)
      return () => { if (simRef.current) simRef.current.stop() }
    }, [data, renderGraph])

    // Highlight selection / query citations
    useEffect(() => {
      const s = d3Ref.current
      if (!s) return

      if (selectedNode) {
        const connected = new Set([selectedNode])
        s.links.forEach(l => {
          const src = (l.source as SimNode).id
          const tgt = (l.target as SimNode).id
          if (src === selectedNode) connected.add(tgt)
          if (tgt === selectedNode) connected.add(src)
        })
        s.nodeEls.transition().duration(150)
          .attr('opacity', d => connected.has(d.id) ? 1 : 0.08)
        s.labelEls.transition().duration(150)
          .attr('opacity', d => connected.has(d.id) ? 1 : 0.03)
        s.linkEls.transition().duration(150)
          .attr('opacity', l => {
            const src = (l.source as SimNode).id
            const tgt = (l.target as SimNode).id
            return (src === selectedNode || tgt === selectedNode) ? 0.7 : 0.02
          })
          .attr('stroke', l => {
            const src = (l.source as SimNode).id
            const tgt = (l.target as SimNode).id
            if (src === selectedNode || tgt === selectedNode) {
              const node = s.nodes.find(n => n.id === selectedNode)
              return node ? communityColor(node.community) : '#00e5ff'
            }
            return '#0d1a30'
          })
          .attr('stroke-width', l => {
            const src = (l.source as SimNode).id
            const tgt = (l.target as SimNode).id
            return (src === selectedNode || tgt === selectedNode) ? 2 : 1.2
          })
      } else if (highlightedNodes.length > 0) {
        const hl = new Set(highlightedNodes)
        s.nodeEls.transition().duration(200)
          .attr('opacity', d => hl.has(d.id) ? 1 : 0.1)
          .attr('stroke-width', d => hl.has(d.id) ? 3 : 1.5)
          .attr('stroke-opacity', d => hl.has(d.id) ? 0.7 : 0.25)
        s.labelEls.transition().duration(200)
          .attr('opacity', d => hl.has(d.id) ? 1 : 0.05)
      } else {
        s.nodeEls.transition().duration(200).attr('opacity', 1).attr('stroke-width', 1.5).attr('stroke-opacity', 0.25)
        s.labelEls.transition().duration(200).attr('opacity', 0.8)
        s.linkEls.transition().duration(200).attr('opacity', 0.2).attr('stroke', '#0d1a30').attr('stroke-width', 1.2)
      }
    }, [selectedNode, highlightedNodes])

    useImperativeHandle(ref, () => ({
      refresh() { if (data) renderGraph(data) },
    }), [data, renderGraph])

    const zoomIn = () => {
      if (svgRef.current && zoomRef.current)
        d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 1.3)
    }
    const zoomOut = () => {
      if (svgRef.current && zoomRef.current)
        d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, 0.7)
    }
    const resetZoom = () => {
      if (!svgRef.current || !zoomRef.current || !containerRef.current) return
      const r = containerRef.current.getBoundingClientRect()
      d3.select(svgRef.current).transition().duration(500)
        .call(zoomRef.current.transform,
          d3.zoomIdentity.translate(r.width / 2, r.height / 2).scale(0.8).translate(-r.width / 2, -r.height / 2))
    }

    const isEmpty = !data || data.nodes.length === 0

    return (
      <div style={{ width: '100%', height: '100%', position: 'relative' }}>
        <div
          ref={containerRef}
          style={{
            width: '100%', height: '100%',
            background: 'radial-gradient(ellipse at 40% 50%, rgba(0,229,255,0.03) 0%, transparent 60%), radial-gradient(ellipse at 70% 30%, rgba(129,140,248,0.02) 0%, transparent 50%), var(--bg)',
          }}
        />

        {/* Tooltip */}
        <div ref={tooltipRef} style={{
          position: 'fixed', pointerEvents: 'none',
          padding: '5px 10px', background: 'rgba(10,16,32,0.95)',
          border: '1px solid rgba(0,229,255,0.15)', borderRadius: 6,
          fontSize: 12, fontWeight: 500, color: '#d0d8e8',
          opacity: 0, transition: 'opacity 0.12s', zIndex: 1000,
          backdropFilter: 'blur(8px)', fontFamily: 'var(--font-body)',
        }} />

        {/* Legend */}
        {!isEmpty && (
          <div style={{
            position: 'absolute', top: 12, left: 12,
            display: 'flex', gap: 12, flexWrap: 'wrap',
            padding: '8px 12px', background: 'rgba(10,16,32,0.85)',
            backdropFilter: 'blur(12px)', border: '1px solid var(--border)',
            borderRadius: 8, fontSize: 11, color: 'var(--text-muted)', fontWeight: 500,
          }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#00e5ff', boxShadow: '0 0 6px rgba(0,229,255,0.6)' }} />
              knowledge
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: EVENT_COLOR }} />
              event
            </span>
            <span style={{ color: 'var(--text-dim)' }}>size = importance</span>
          </div>
        )}

        {/* Zoom controls */}
        {!isEmpty && (
          <div style={{
            position: 'absolute', bottom: 16, left: 16,
            display: 'flex', flexDirection: 'column', gap: 2,
          }}>
            {[{ label: '+', fn: zoomIn }, { label: '\u2212', fn: zoomOut }, { label: '\u21BA', fn: resetZoom }].map(b => (
              <button key={b.label} onClick={b.fn} style={{
                width: 32, height: 32, border: '1px solid var(--border)',
                background: 'rgba(10,16,32,0.9)', backdropFilter: 'blur(8px)',
                color: 'var(--text-muted)', borderRadius: 6, cursor: 'pointer',
                fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>{b.label}</button>
            ))}
          </div>
        )}

        {/* Stats */}
        {!isEmpty && data && (
          <div style={{
            position: 'absolute', bottom: 16, right: 16,
            fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-dim)',
          }}>
            {data.nodes.length} nodes &middot; {data.edges.length} edges
          </div>
        )}

        {/* Empty / loading states */}
        {isEmpty && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 12, fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-dim)',
            pointerEvents: 'none',
          }}>
            <span>no nodes yet — ingest some data</span>
          </div>
        )}
      </div>
    )
  }
)
