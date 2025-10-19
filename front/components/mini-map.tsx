"use client"

import { Card } from "@/components/ui/card"

interface MiniMapProps {
  nodes: any[]
  connections: any[]
  viewportWidth: number
  viewportHeight: number
}

export function MiniMap({ nodes, connections, viewportWidth, viewportHeight }: MiniMapProps) {
  // Calculate bounds
  const padding = 50
  const minX = Math.min(...nodes.map((n) => n.x)) - padding
  const minY = Math.min(...nodes.map((n) => n.y)) - padding
  const maxX = Math.max(...nodes.map((n) => n.x + 240)) + padding
  const maxY = Math.max(...nodes.map((n) => n.y + 80)) + padding

  const width = maxX - minX
  const height = maxY - minY

  // Scale to fit minimap
  const minimapWidth = 200
  const minimapHeight = 150
  const scale = Math.min(minimapWidth / width, minimapHeight / height)

  return (
    <Card className="absolute bottom-4 right-4 w-[200px] h-[150px] bg-card/95 backdrop-blur-sm border-border shadow-lg overflow-hidden z-50">
      <svg width={minimapWidth} height={minimapHeight} className="w-full h-full">
        {/* Background */}
        <rect width={minimapWidth} height={minimapHeight} fill="oklch(0.15 0.02 240)" />

        {/* Connections */}
        {connections.map((conn, idx) => {
          const fromNode = nodes.find((n) => n.id === conn.from)
          const toNode = nodes.find((n) => n.id === conn.to)
          if (!fromNode || !toNode) return null

          const x1 = (fromNode.x - minX) * scale
          const y1 = (fromNode.y - minY) * scale
          const x2 = (toNode.x - minX) * scale
          const y2 = (toNode.y - minY) * scale

          return (
            <line
              key={idx}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="oklch(0.65 0.22 240)"
              strokeWidth="1"
              opacity="0.5"
            />
          )
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const x = (node.x - minX) * scale
          const y = (node.y - minY) * scale
          const nodeWidth = 240 * scale
          const nodeHeight = 80 * scale

          const getColor = (type: string) => {
            switch (type) {
              case "wallet":
                return "oklch(0.65 0.22 240)"
              case "contract":
                return "oklch(0.65 0.15 180)"
              case "token":
                return "oklch(0.65 0.18 150)"
              case "function":
                return "oklch(0.65 0.20 300)"
              default:
                return "oklch(0.5 0.1 240)"
            }
          }

          return (
            <rect
              key={node.id}
              x={x}
              y={y}
              width={nodeWidth}
              height={nodeHeight}
              fill={getColor(node.type)}
              opacity="0.8"
              rx="2"
            />
          )
        })}

        {/* Viewport indicator */}
        <rect
          x="0"
          y="0"
          width={minimapWidth}
          height={minimapHeight}
          fill="none"
          stroke="oklch(0.8 0.22 240)"
          strokeWidth="2"
          opacity="0.5"
        />
      </svg>
    </Card>
  )
}
