"use client"

import { TransactionBuilder } from "@/components/transaction-builder"
import { ChatHistory } from "@/components/chat-history"
import { CursorChat } from "@/components/cursor-chat"
import { ComponentPalette } from "@/components/component-palette"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Play, Save, Trash2, ZoomIn, ZoomOut, Maximize2, ArrowRight, Clock, Coins } from "lucide-react"
import { useState, useEffect, useMemo } from "react"
import { DeFiStrategyFlow } from "@/components/defi-strategy-flow"
import type { Edge, Node } from "reactflow"
import type { ScratchBlockNodeData } from "@/components/scratch-block-node"

interface FlowRowGroup {
  id: string
  y: number
  nodes: Node<ScratchBlockNodeData>[]
  marker?: Node<ScratchBlockNodeData>
  heading: string
  stage?: string
}

const FLOW_ROW_GROUP_TOLERANCE = 48

export default function Home() {
  const [builderMode, setBuilderMode] = useState<"flow" | "legacy">("flow")
  const [flowNodes, setFlowNodes] = useState<Node<ScratchBlockNodeData>[]>([])
  const [flowEdges, setFlowEdges] = useState<Edge[]>([])
  const [nodes, setNodes] = useState<any[]>([
    {
      id: "node-1",
      type: "wallet",
      label: "Wallet Address",
      x: 100,
      y: 100,
      data: { address: "0x742d...4e89" },
    },
    {
      id: "node-2",
      type: "contract",
      label: "Smart Contract",
      x: 400,
      y: 100,
      data: { contract: "UniswapV3Router" },
    },
    {
      id: "node-3",
      type: "function",
      label: "swapExactTokensForTokens",
      x: 700,
      y: 100,
      data: { params: ["amountIn", "amountOutMin", "path"] },
    },
  ])
  const [connections, setConnections] = useState<any[]>([
    { from: "node-1", to: "node-2" },
    { from: "node-2", to: "node-3" },
  ])
  const [activeTab, setActiveTab] = useState("all")
  const [lastSaved, setLastSaved] = useState<Date>(new Date())

  const nodeCount = builderMode === "flow" ? flowNodes.length : nodes.length
  const connectionCount = builderMode === "flow" ? flowEdges.length : connections.length
  const flowNodeGroups = useMemo<FlowRowGroup[]>(() => {
    if (flowNodes.length === 0) return []

    const sorted = [...flowNodes].sort((a, b) => {
      if (a.position.y === b.position.y) {
        return a.position.x - b.position.x
      }
      return a.position.y - b.position.y
    })

    const groups: { y: number; nodes: Node<ScratchBlockNodeData>[] }[] = []

    sorted.forEach((node) => {
      const existing = groups.find((group) => Math.abs(group.y - node.position.y) <= FLOW_ROW_GROUP_TOLERANCE)
      if (existing) {
        existing.nodes.push(node)
      } else {
        groups.push({ y: node.position.y, nodes: [node] })
      }
    })

    return groups.map((group, index) => {
      const rowNodes = [...group.nodes].sort((a, b) => a.position.x - b.position.x)
      const markerNode = rowNodes.find((candidate) => {
        const typeLabel = candidate.data.typeLabel ?? ""
        return candidate.data.variant === "marker" || typeLabel.toLowerCase().includes("marker")
      })
      const stageValue =
        markerNode && typeof markerNode.data.values?.stage === "string"
          ? (markerNode.data.values.stage as string)
          : undefined
      const heading = stageValue
        ? `${stageValue.charAt(0).toUpperCase()}${stageValue.slice(1)} Stage`
        : markerNode
          ? markerNode.data.title
          : `Flow Row ${index + 1}`

      return {
        id: `row-${index}-${Math.round(group.y)}`,
        y: group.y,
        nodes: rowNodes,
        marker: markerNode,
        heading,
        stage: stageValue,
      }
    })
  }, [flowNodes])
  const gasEstimateLabel = builderMode === "flow" ? "~0.83 ALGO eq." : "~0.0042 ETH"
  const previewTitle = builderMode === "flow" ? "Strategy Preview" : "Transaction Preview"

  useEffect(() => {
    const interval = setInterval(() => {
      setLastSaved(new Date())
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  const formatLastSaved = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)

    if (seconds < 60) return `${seconds}s ago`
    if (minutes < 60) return `${minutes}m ago`
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }

  const categories = [
    { value: "all", label: "All" },
    { value: "wallet", label: "Wallets" },
    { value: "contract", label: "Contracts" },
    { value: "token", label: "Tokens" },
    { value: "logic", label: "Logic" },
    { value: "marker", label: "Markers" },
    { value: "defi", label: "DeFi" },
  ]

  return (
    <div className="h-screen w-full bg-background flex flex-col">
      <div className="flex items-center justify-between bg-card/80 backdrop-blur-sm border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <h1 className="text-xl font-bold text-foreground">DeFi Transaction Builder</h1>
          </div>
          <Separator orientation="vertical" className="h-6" />
          <Badge variant="secondary" className="text-xs font-mono">
            {nodeCount} nodes
          </Badge>
          <Badge variant="outline" className="text-xs">
            {connectionCount} connections
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 mr-2">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ZoomIn className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <Maximize2 className="h-4 w-4" />
            </Button>
          </div>
          <Separator orientation="vertical" className="h-6" />
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-end mr-2">
              <Button variant="outline" size="sm" className="h-8 bg-transparent">
                <Save className="h-3.5 w-3.5 mr-2" />
                Save
              </Button>
              <span className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                <Clock className="h-3 w-3" />
                {formatLastSaved(lastSaved)}
              </span>
            </div>
            <Button variant="outline" size="sm" className="h-8 bg-transparent">
              <Trash2 className="h-3.5 w-3.5 mr-2" />
              Clear
            </Button>
          </div>
          <Separator orientation="vertical" className="h-6" />
          <Button size="sm" className="h-8 bg-primary hover:bg-primary/90">
            <Play className="h-3.5 w-3.5 mr-2" />
            Execute
          </Button>
        </div>
      </div>

      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Sidebar - Chat History */}
        <ResizablePanel defaultSize={15} minSize={10} maxSize={30} className="min-w-[200px]">
          <div className="h-full border-r border-border bg-card">
            <ChatHistory />
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle className="bg-border hover:bg-primary/20 transition-colors" />

        {/* Main Content Area - Vertical split for builder and palette */}
        <ResizablePanel defaultSize={60} minSize={40}>
          <ResizablePanelGroup direction="vertical">
            {/* Transaction Builder Canvas */}
            <ResizablePanel defaultSize={70} minSize={50}>
              <div className="flex h-full flex-col bg-background">
                <div className="flex items-center justify-between border-b border-border bg-card/60 px-4 py-2">
                  <Tabs value={builderMode} onValueChange={(value: string) => setBuilderMode(value as "flow" | "legacy")}>
                    <TabsList className="grid w-36 grid-cols-2 bg-muted/60">
                      <TabsTrigger value="flow" className="text-xs">
                        Scratch Flow
                      </TabsTrigger>
                      <TabsTrigger value="legacy" className="text-xs">
                        Canvas
                      </TabsTrigger>
                    </TabsList>
                  </Tabs>
                  <Badge variant="outline" className="text-[0.65rem] uppercase tracking-wide">
                    {builderMode === "flow" ? "React Flow" : "Canvas"}
                  </Badge>
                </div>
                <div className="flex-1 overflow-hidden">
                  {builderMode === "flow" ? (
                    <div className="h-full overflow-hidden p-4">
                      <DeFiStrategyFlow onNodesUpdate={setFlowNodes} onEdgesUpdate={setFlowEdges} />
                    </div>
                  ) : (
                    <div className="h-full overflow-auto bg-background">
                      <TransactionBuilder
                        nodes={nodes}
                        setNodes={setNodes}
                        connections={connections}
                        setConnections={setConnections}
                      />
                    </div>
                  )}
                </div>
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle className="bg-border hover:bg-primary/20 transition-colors" />

            {/* Bottom Component Palette */}
            <ResizablePanel defaultSize={30} minSize={20} maxSize={45}>
              <div className="h-full border-t border-border bg-card flex flex-col">
                <div className="px-4 pt-3 pb-2 border-b border-border bg-card/50">
                  <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="w-full justify-start h-9 bg-muted/50">
                      {categories.map((cat) => (
                        <TabsTrigger key={cat.value} value={cat.value} className="text-xs">
                          {cat.label}
                        </TabsTrigger>
                      ))}
                    </TabsList>
                  </Tabs>
                </div>
                <ComponentPalette activeTab={activeTab} />
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>

        <ResizableHandle withHandle className="bg-border hover:bg-primary/20 transition-colors" />

        {/* Right Sidebar - Split between Chat and Transaction Preview */}
        <ResizablePanel defaultSize={25} minSize={15} maxSize={40} className="min-w-[280px]">
          <ResizablePanelGroup direction="vertical">
            {/* Cursor Chat */}
            <ResizablePanel defaultSize={70} minSize={40}>
              <div className="h-full border-l border-border bg-card">
                <CursorChat />
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle className="bg-border hover:bg-primary/20 transition-colors" />

            <ResizablePanel defaultSize={30} minSize={20} maxSize={50}>
              <div className="h-full border-l border-t border-border bg-card/80 backdrop-blur-sm p-4 overflow-auto">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                    {previewTitle}
                  </h3>
                  <Badge variant="secondary" className="text-xs font-mono">
                    Ready
                  </Badge>
                </div>

                {/* Visual tree with icons and token info */}
                <div className="space-y-3">
                  {builderMode === "flow" ? (
                    flowNodeGroups.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-border/60 bg-muted/30 p-4 text-center text-xs text-muted-foreground">
                        Add blocks in the canvas to preview your automated strategy.
                      </div>
                    ) : (
                      flowNodeGroups.map((group) => {
                        const accentColor =
                          group.marker?.data.accentColor ?? group.nodes[0]?.data.accentColor ?? "#1e293b"
                        const markerSummary = group.marker?.data.description
                        return (
                          <div
                            key={group.id}
                            className="rounded-xl border border-border/60 bg-muted/30 p-3 shadow-sm space-y-3"
                            style={{ borderColor: accentColor }}
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span
                                  className="text-[0.65rem] font-semibold uppercase tracking-wide"
                                  style={{ color: accentColor }}
                                >
                                  {group.heading}
                                </span>
                                {group.stage ? (
                                  <Badge variant="secondary" className="text-[0.6rem] uppercase tracking-wide">
                                    {group.stage?.toUpperCase()}
                                  </Badge>
                                ) : null}
                              </div>
                              {group.marker ? (
                                <span className="text-[0.6rem] font-mono text-muted-foreground truncate max-w-[120px]">
                                  {group.marker.id}
                                </span>
                              ) : null}
                            </div>
                            {markerSummary ? (
                              <p className="text-[0.65rem] text-muted-foreground">{markerSummary}</p>
                            ) : null}
                            <div className="space-y-2">
                              {group.nodes.map((node) => {
                                if (group.marker && node.id === group.marker.id) {
                                  return null
                                }
                                return (
                                  <div
                                    key={node.id}
                                    className="rounded-lg border border-border/50 bg-background/80 p-3 shadow-sm"
                                    style={{ borderColor: node.data.accentColor ?? accentColor }}
                                  >
                                    <div className="flex items-center justify-between gap-2">
                                      <span
                                        className="text-[0.6rem] font-semibold uppercase tracking-wide"
                                        style={{ color: node.data.accentColor ?? accentColor }}
                                      >
                                        {node.data.typeLabel}
                                      </span>
                                      <span className="text-[0.55rem] font-mono text-muted-foreground truncate max-w-[120px]">
                                        {node.id}
                                      </span>
                                    </div>
                                    <div className="mt-1 text-sm font-semibold text-foreground">{node.data.title}</div>
                                    {node.data.description ? (
                                      <p className="mt-1 text-xs text-muted-foreground">{node.data.description}</p>
                                    ) : null}
                                    {node.data.values && Object.keys(node.data.values).length > 0 ? (
                                      <div className="mt-2 space-y-1">
                                        {Object.entries(node.data.values).map(([key, value]) => (
                                          <div
                                            key={key}
                                            className="flex items-center justify-between gap-3 text-[0.65rem] text-muted-foreground font-mono"
                                          >
                                            <span>{key}</span>
                                            <span className="truncate">
                                              {Array.isArray(value) ? value.join(", ") : String(value)}
                                            </span>
                                          </div>
                                        ))}
                                      </div>
                                    ) : null}
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )
                      })
                    )
                  ) : (
                    nodes.map((node, idx) => (
                      <div key={node.id}>
                        <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 border border-border/50">
                          <div className="text-xl">
                            {node.type === "wallet"
                              ? "💼"
                              : node.type === "contract"
                                ? "⚙️"
                                : node.type === "function"
                                  ? "🔁"
                                  : "🪙"}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-xs text-foreground mb-1">{node.label}</div>
                            {node.data && (
                              <div className="space-y-0.5">
                                {Object.entries(node.data).map(([key, value]) => (
                                  <div key={key} className="text-xs text-muted-foreground font-mono">
                                    {key}: {Array.isArray(value) ? value.join(", ") : String(value)}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                        {idx < nodes.length - 1 && (
                          <div className="flex items-center justify-center py-1">
                            <ArrowRight className="h-4 w-4 text-primary" />
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>

                {/* Simulate Gas button */}
                <div className="mt-4 space-y-2">
                  <Button variant="outline" size="sm" className="w-full text-xs bg-transparent">
                    <Coins className="h-3 w-3 mr-2" />
                    {builderMode === "flow" ? "Simulate Strategy" : "Simulate Gas"}
                  </Button>
                  <div className="text-xs text-muted-foreground text-center font-mono">Est. Network Cost: {gasEstimateLabel}</div>
                </div>
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
