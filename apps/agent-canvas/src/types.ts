export type NodeStatus =
  | "idle"
  | "queued"
  | "running"
  | "completed"
  | "partial"
  | "waiting_review"
  | "waiting_approval"
  | "blocked"
  | "failed"

export type GraphLink = {
  label: string
  path: string
  kind: string
}

export type NodeActionRef = {
  action_id: string
  label: string
}

export type GraphNode = {
  id: string
  kind: string
  status: NodeStatus
  label: string
  subtitle: string
  counts: Record<string, number>
  last_updated_at: string
  progress_text: string
  detail_markdown: string
  links: GraphLink[]
  actions: NodeActionRef[]
  position: { x: number; y: number }
  metadata?: Record<string, unknown>
}

export type GraphEdge = {
  id: string
  source: string
  target: string
  label?: string
}

export type GraphView = {
  id: string
  label: string
  subtitle: string
  status: NodeStatus
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata?: Record<string, unknown>
}

export type NodeDetail = {
  node_id: string
  domain_id: string
  status: NodeStatus
  label: string
  subtitle: string
  counts: Record<string, number>
  last_updated_at: string
  progress_text: string
  detail_markdown: string
  links: GraphLink[]
  actions: NodeActionRef[]
  metadata?: Record<string, unknown>
}

export type LaunchAction = {
  id: string
  label: string
  description: string
  command: string[]
  group: string
}

export type ActionRun = {
  run_id: string
  action_id: string
  label: string
  status: string
  started_at: string
  finished_at?: string
  exit_code?: number | null
  log_path?: string
  pid?: number | null
}
