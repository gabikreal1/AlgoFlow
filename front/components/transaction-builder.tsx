"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { NodeDetailsDrawer } from "@/components/node-details-drawer"
import { MiniMap } from "@/components/mini-map"

interface TransactionNode {
  id: string
  type: "wallet" | "contract" | "token" | "function"
  label: string
  x: number
  y: number
  data?: Record<string, any>
}

interface Connection {
  from: string
  to: string
}

interface TransactionBuilderProps {
  nodes: TransactionNode[]
  setNodes: (nodes: TransactionNode[]) => void
  connections: Connection[]
  setConnections: (connections: Connection[]) => void
}

export function TransactionBuilder({ nodes, setNodes, connections, setConnections }: TransactionBuilderProps) {
  const [selectedNode, setSelectedNode] = useState<TransactionNode | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const handleNodeClick = (node: TransactionNode) => {
    setSelectedNode(node)
    setDrawerOpen(true)
  }

  const handleNodeUpdate = (nodeId: string, data: any) => {
    setNodes(nodes.map((node) => (node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node)))
  }

  const handleNodeDelete = (nodeId: string) => {
    setNodes(nodes.filter((node) => node.id !== nodeId))
    setConnections(connections.filter((conn) => conn.from !== nodeId && conn.to !== nodeId))
  }

  const handleNodeDuplicate = (nodeId: string) => {
    const node = nodes.find((n) => n.id === nodeId)
    if (node) {
      const newNode = {
        ...node,
        id: `node-${Date.now()}`,
        x: node.x + 50,
        y: node.y + 50,
      }
      setNodes([...nodes, newNode])
    }
  }

  const getNodeColor = (type: TransactionNode["type"]) => {
    switch (type) {
      case "wallet":
        return "bg-primary/20 border-primary"
      case "contract":
        return "bg-accent/20 border-accent"
      case "token":
        return "bg-chart-2/20 border-chart-2"
      case "function":
        return "bg-chart-3/20 border-chart-3"
      default:
        return "bg-muted border-border"
    }
  }

  const getNodeIcon = (type: TransactionNode["type"]) => {
    switch (type) {
      case "wallet":
        return "💼"
      case "contract":
        return "📄"
      case "token":
        return "🪙"
      case "function":
        return "⚙️"
      default:
        return "📦"
    }
  }

  const getNodeGlow = (type: TransactionNode["type"]) => {
    switch (type) {
      case "wallet":
        return "shadow-lg shadow-primary/30 hover:shadow-primary/50"
      case "contract":
        return "shadow-lg shadow-accent/30 hover:shadow-accent/50"
      case "token":
        return "shadow-lg shadow-chart-2/30 hover:shadow-chart-2/50"
      case "function":
        return "shadow-lg shadow-chart-3/30 hover:shadow-chart-3/50"
      default:
        return "shadow-lg"
    }
  }

  return (
    <>
      <div className="h-full w-full p-6">
        {/* Canvas */}
        <Card className="h-full relative overflow-hidden bg-gradient-to-br from-card/50 to-card/30 backdrop-blur-sm border-border shadow-lg">
          {/* Grid Background */}
          <div
            className="absolute inset-0 opacity-30"
            style={{
              backgroundImage: `
                linear-gradient(to right, oklch(0.25 0.02 240) 1px, transparent 1px),
                linear-gradient(to bottom, oklch(0.25 0.02 240) 1px, transparent 1px)
              `,
              backgroundSize: "24px 24px",
            }}
          />

          {/* Subtle gradient overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 pointer-events-none" />

          {/* Connections */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
            {connections.map((conn, idx) => {
              const fromNode = nodes.find((n) => n.id === conn.from)
              const toNode = nodes.find((n) => n.id === conn.to)
              if (!fromNode || !toNode) return null

              const x1 = fromNode.x + 120
              const y1 = fromNode.y + 40
              const x2 = toNode.x
              const y2 = toNode.y + 40

              return (
                <g key={idx}>
                  <defs>
                    <marker id={`arrowhead-${idx}`} markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                      <polygon points="0 0, 10 3, 0 6" fill="oklch(0.65 0.22 240)" />
                    </marker>
                    <filter id={`glow-${idx}`}>
                      <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                      <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>
                  <path
                    d={`M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`}
                    stroke="oklch(0.65 0.22 240)"
                    strokeWidth="2.5"
                    fill="none"
                    markerEnd={`url(#arrowhead-${idx})`}
                    className="opacity-70"
                    filter={`url(#glow-${idx})`}
                  />
                </g>
              )
            })}
          </svg>

          {/* Nodes */}
          <div className="relative w-full h-full z-20">
            {nodes.map((node) => (
              <div
                key={node.id}
                onClick={() => handleNodeClick(node)}
                className={`absolute cursor-pointer transition-all duration-200 hover:scale-105 ${getNodeColor(
                  node.type,
                )} ${getNodeGlow(node.type)} border-2 rounded-xl p-4 w-64 hover:shadow-xl backdrop-blur-sm`}
                style={{
                  left: `${node.x}px`,
                  top: `${node.y}px`,
                }}
              >
                <div className="flex items-start gap-3">
                  <div className="text-2xl">{getNodeIcon(node.type)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="outline" className="text-xs font-medium">
                        {node.type}
                      </Badge>
                    </div>
                    <h3 className="font-semibold text-sm text-foreground mb-2 truncate">{node.label}</h3>
                    {node.data && (
                      <div className="space-y-1.5">
                        {Object.entries(node.data).map(([key, value]) => (
                          <div key={key} className="text-xs text-muted-foreground flex items-center gap-1.5">
                            <span className="font-mono font-medium">{key}:</span>
                            <span className="truncate font-mono">
                              {Array.isArray(value) ? value.join(", ") : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Connection Points with enhanced glow effect */}
                <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-primary rounded-full border-2 border-background shadow-lg shadow-primary/50" />
                <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-accent rounded-full border-2 border-background shadow-lg shadow-accent/50" />
              </div>
            ))}
          </div>

          <MiniMap nodes={nodes} connections={connections} viewportWidth={1200} viewportHeight={800} />
        </Card>
      </div>

      <NodeDetailsDrawer
        node={selectedNode}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onUpdate={handleNodeUpdate}
        onDelete={handleNodeDelete}
        onDuplicate={handleNodeDuplicate}
      />
    </>
  )
}
