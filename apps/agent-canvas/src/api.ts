import type { ActionRun, GraphView, LaunchAction, NodeDetail } from "./types"

const API_BASE = "http://127.0.0.1:8000"

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }
  return response.json() as Promise<T>
}

export function getOverview(): Promise<GraphView> {
  return requestJson("/api/graph/overview")
}

export function getDomain(domainId: string): Promise<GraphView> {
  return requestJson(`/api/graph/domain/${domainId}`)
}

export function getNodeDetail(nodeId: string): Promise<NodeDetail> {
  return requestJson(`/api/node/${nodeId}`)
}

export function getActions(): Promise<LaunchAction[]> {
  return requestJson("/api/actions")
}

export function getActionRuns(): Promise<ActionRun[]> {
  return requestJson("/api/actions/runs")
}

export function runAction(actionId: string): Promise<ActionRun> {
  return requestJson("/api/actions/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action_id: actionId }),
  })
}

export function fileUrl(path: string): string {
  return `${API_BASE}/api/file?path=${encodeURIComponent(path)}`
}

export function dirUrl(path: string): string {
  return `${API_BASE}/api/dir?path=${encodeURIComponent(path)}`
}
