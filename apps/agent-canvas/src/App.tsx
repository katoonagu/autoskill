import { useEffect, useMemo, useState } from "react"
import ReactMarkdown from "react-markdown"
import {
  Background,
  Controls,
  Handle,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
  Position,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import { dirUrl, fileUrl, getActions, getActionRuns, getDomain, getNodeDetail, getOverview, runAction } from "./api"
import type { ActionRun, GraphNode, GraphView, LaunchAction, NodeDetail, NodeStatus } from "./types"

type CanvasNodeData = {
  node: GraphNode
  selectedNodeId: string | null
}

type FlowCanvasNode = Node<CanvasNodeData, "canvasNode">

const STATUS_META: Record<NodeStatus, { tone: string; badge: string }> = {
  idle: { tone: "var(--status-idle)", badge: "Idle" },
  queued: { tone: "var(--status-queued)", badge: "Queued" },
  running: { tone: "var(--status-running)", badge: "Running" },
  completed: { tone: "var(--status-completed)", badge: "Completed" },
  partial: { tone: "var(--status-partial)", badge: "Partial" },
  waiting_review: { tone: "var(--status-review)", badge: "Review" },
  waiting_approval: { tone: "var(--status-approval)", badge: "Approval" },
  blocked: { tone: "var(--status-blocked)", badge: "Blocked" },
  failed: { tone: "var(--status-failed)", badge: "Failed" },
}

const DOMAIN_ACTION_GROUPS: Record<string, string> = {
  control_plane: "control_plane",
  company_contacts_enrichment: "company_contacts_enrichment",
  outreach_execution: "outreach_execution",
  browser_runtime: "browser_runtime",
  knowledge_reports: "knowledge_reports",
}

function prettyTime(value: string): string {
  if (!value) {
    return "n/a"
  }
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function countChips(counts: Record<string, number>): string[] {
  return Object.entries(counts)
    .filter(([, value]) => value > 0)
    .slice(0, 3)
    .map(([key, value]) => `${value} ${key.replace(/_/g, " ")}`)
}

function extractRecentItems(detail: NodeDetail | null): string[] {
  const raw = detail?.metadata?.recent_items
  if (!Array.isArray(raw)) {
    return []
  }
  return raw.filter((item): item is string => typeof item === "string").slice(0, 6)
}

function CanvasNode({ data }: NodeProps<FlowCanvasNode>) {
  const node = data.node
  const meta = STATUS_META[node.status] ?? STATUS_META.idle
  const isDomain = node.kind === "domain"
  const isSelected = data.selectedNodeId === node.id
  const chips = countChips(node.counts)

  return (
    <div
      className={`canvas-node ${isDomain ? "is-domain" : ""} ${isSelected ? "is-selected" : ""}`}
      style={{ ["--node-accent" as string]: meta.tone }}
    >
      <Handle type="target" position={Position.Left} className="canvas-handle" />
      <div className={`canvas-node__core status-${node.status}`}>
        <div className="canvas-node__glyph">{isDomain ? "◈" : "•"}</div>
      </div>
      <div className="canvas-node__meta">
        <span className="canvas-node__step">{meta.badge}</span>
        <strong>{node.label}</strong>
        <span>{node.subtitle}</span>
        {chips.length > 0 ? (
          <div className="canvas-node__chips">
            {chips.map((chip) => (
              <span key={chip}>{chip}</span>
            ))}
          </div>
        ) : null}
      </div>
      <Handle type="source" position={Position.Right} className="canvas-handle" />
    </div>
  )
}

export default function App() {
  const [overview, setOverview] = useState<GraphView | null>(null)
  const [activeView, setActiveView] = useState<GraphView | null>(null)
  const [currentDomain, setCurrentDomain] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedDetail, setSelectedDetail] = useState<NodeDetail | null>(null)
  const [actions, setActions] = useState<LaunchAction[]>([])
  const [runs, setRuns] = useState<ActionRun[]>([])
  const [error, setError] = useState<string>("")
  const [lastRefreshAt, setLastRefreshAt] = useState<string>("")

  useEffect(() => {
    let cancelled = false

    async function refresh() {
      try {
        const [overviewPayload, actionsPayload, runsPayload, activePayload] = await Promise.all([
          getOverview(),
          getActions(),
          getActionRuns(),
          currentDomain ? getDomain(currentDomain) : getOverview(),
        ])
        if (cancelled) {
          return
        }
        setOverview(overviewPayload)
        setActiveView(activePayload)
        setActions(actionsPayload)
        setRuns(runsPayload)
        setLastRefreshAt(new Date().toISOString())
        setError("")
      } catch (refreshError) {
        if (!cancelled) {
          setError(refreshError instanceof Error ? refreshError.message : "Unknown dashboard error")
        }
      }
    }

    void refresh()
    const timer = window.setInterval(() => {
      void refresh()
    }, 3000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [currentDomain])

  useEffect(() => {
    let cancelled = false
    async function loadNode() {
      if (!selectedNodeId) {
        setSelectedDetail(null)
        return
      }
      try {
        const payload = await getNodeDetail(selectedNodeId)
        if (!cancelled) {
          setSelectedDetail(payload)
        }
      } catch (detailError) {
        if (!cancelled) {
          setError(detailError instanceof Error ? detailError.message : "Failed to load node detail")
        }
      }
    }
    void loadNode()
    return () => {
      cancelled = true
    }
  }, [selectedNodeId])

  const nodeTypes = useMemo(() => ({ canvasNode: CanvasNode }), [])

  const flowNodes = useMemo<FlowCanvasNode[]>(() => {
    if (!activeView) {
      return []
    }
    return activeView.nodes.map((node) => ({
      id: node.id,
      type: "canvasNode",
      position: node.position,
      draggable: false,
      selectable: true,
      data: {
        node,
        selectedNodeId,
      },
    }))
  }, [activeView, selectedNodeId])

  const flowEdges = useMemo<Edge[]>(() => {
    if (!activeView) {
      return []
    }
    return activeView.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      animated: false,
      style: { stroke: "rgba(255,255,255,0.18)", strokeWidth: 1.4 },
    }))
  }, [activeView])

  const brainMode = useMemo(() => {
    const controlNode = overview?.nodes.find((node) => node.id === "domain.control_plane")
    const progress = controlNode?.progress_text ?? ""
    return progress.replace("Brain mode:", "").trim() || "unknown"
  }, [overview])

  const activeDomainGroup = currentDomain ? DOMAIN_ACTION_GROUPS[currentDomain] : null
  const visibleActions = useMemo(() => {
    if (!activeDomainGroup) {
      return actions
    }
    return actions.filter((action) => action.group === activeDomainGroup)
  }, [actions, activeDomainGroup])

  const runningRun = runs.find((run) => run.status === "running")

  async function handleActionRun(actionId: string) {
    try {
      await runAction(actionId)
      const [overviewPayload, runsPayload, activePayload] = await Promise.all([
        getOverview(),
        getActionRuns(),
        currentDomain ? getDomain(currentDomain) : getOverview(),
      ])
      setOverview(overviewPayload)
      setRuns(runsPayload)
      setActiveView(activePayload)
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Failed to launch action")
    }
  }

  function handleNodeSelect(node: GraphNode) {
    setSelectedNodeId(node.id)
    if (!currentDomain && node.kind === "domain") {
      setCurrentDomain(node.id.replace("domain.", ""))
    }
  }

  const recentItems = extractRecentItems(selectedDetail)

  return (
    <div className="canvas-app">
      <div className="canvas-shell">
        <header className="canvas-header">
          <div>
            <p className="canvas-header__kicker">AUTOSKILL</p>
            <h1>Agent Canvas</h1>
            <p className="canvas-header__subtitle">
              Visual layer for supervisor, company research, outreach, browser runtime, and reports.
            </p>
          </div>
          <div className="canvas-header__stats">
            <div>
              <span>Current run</span>
              <strong>{runningRun?.label ?? "No active launch"}</strong>
            </div>
            <div>
              <span>Brain mode</span>
              <strong>{brainMode}</strong>
            </div>
            <div>
              <span>Last refresh</span>
              <strong>{prettyTime(lastRefreshAt)}</strong>
            </div>
          </div>
        </header>

        <main className="canvas-main">
          <section className="canvas-stage">
            <div className="canvas-toolbar">
              <div className="canvas-toolbar__left">
                <button type="button" className="ghost-button" onClick={() => { setCurrentDomain(null); setSelectedNodeId(null) }}>
                  Back to graph
                </button>
                <div>
                  <strong>{activeView?.label ?? "Loading..."}</strong>
                  <span>{activeView?.subtitle ?? "Waiting for graph data"}</span>
                </div>
              </div>
              <div className="canvas-toolbar__right">
                {error ? <span className="canvas-error">{error}</span> : null}
                <span className="canvas-status-pill">{activeView?.status ?? "idle"}</span>
              </div>
            </div>

            <div className="canvas-grid" />
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.55}
              maxZoom={1.1}
              onNodeClick={(_, node: FlowCanvasNode) => handleNodeSelect(node.data.node)}
              proOptions={{ hideAttribution: true }}
            >
              <Background color="rgba(255,255,255,0.045)" gap={28} />
              <Controls position="top-left" showInteractive={false} />
            </ReactFlow>
          </section>

          <aside className="detail-drawer">
            {selectedDetail ? (
              <>
                <div className="detail-drawer__header">
                  <div>
                    <span className={`detail-status detail-status--${selectedDetail.status}`}>
                      {STATUS_META[selectedDetail.status]?.badge ?? selectedDetail.status}
                    </span>
                    <h2>{selectedDetail.label}</h2>
                    <p>{selectedDetail.subtitle}</p>
                  </div>
                </div>

                <div className="detail-drawer__meta">
                  <div>
                    <span>Updated</span>
                    <strong>{prettyTime(selectedDetail.last_updated_at)}</strong>
                  </div>
                  <div>
                    <span>Progress</span>
                    <strong>{selectedDetail.progress_text || "No progress text"}</strong>
                  </div>
                </div>

                <div className="detail-drawer__markdown">
                  <ReactMarkdown>{selectedDetail.detail_markdown}</ReactMarkdown>
                </div>

                {recentItems.length > 0 ? (
                  <div className="detail-drawer__recent">
                    <h3>Recent items</h3>
                    <ul>
                      {recentItems.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <div className="detail-drawer__links">
                  <h3>Links</h3>
                  <div className="detail-link-grid">
                    {selectedDetail.links.map((link) => (
                      <a
                        key={`${link.label}-${link.path}`}
                        href={link.kind === "directory" ? dirUrl(link.path) : fileUrl(link.path)}
                        target="_blank"
                        rel="noreferrer"
                        className="detail-link"
                      >
                        <span>{link.label}</span>
                        <small>{link.path}</small>
                      </a>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="detail-empty">
                <span className="detail-empty__eyebrow">Node detail</span>
                <h2>Select a node</h2>
                <p>Click a domain on the overview or a stage inside any drill-down graph to inspect live markdown, links, and recent activity.</p>
              </div>
            )}
          </aside>
        </main>

        <footer className="canvas-footer">
          <section className="action-panel">
            <div className="action-panel__header">
              <div>
                <span>Launch Actions</span>
                <strong>{currentDomain ? activeView?.label : "All domains"}</strong>
              </div>
            </div>
            <div className="action-panel__grid">
              {visibleActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  className="action-card"
                  onClick={() => void handleActionRun(action.id)}
                >
                  <strong>{action.label}</strong>
                  <span>{action.description}</span>
                </button>
              ))}
            </div>
          </section>

          <section className="runs-panel">
            <div className="action-panel__header">
              <div>
                <span>Recent runs</span>
                <strong>{runs.length ? `${runs.length} tracked` : "No tracked runs"}</strong>
              </div>
            </div>
            <div className="runs-list">
              {runs.slice(0, 6).map((run) => (
                <div key={run.run_id} className="run-item">
                  <div>
                    <strong>{run.label}</strong>
                    <span>{prettyTime(run.started_at)}</span>
                  </div>
                  <div className={`run-pill run-pill--${run.status}`}>{run.status}</div>
                </div>
              ))}
            </div>
          </section>
        </footer>
      </div>
    </div>
  )
}
