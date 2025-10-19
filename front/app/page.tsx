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
import {
  Play,
  Save,
  Trash2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ArrowRight,
  Clock,
  Coins,
  Download,
  Upload,
  Wallet,
  CheckCircle,
  AlertTriangle,
} from "lucide-react"
import { useState, useEffect, useMemo, useCallback } from "react"
import { DeFiStrategyFlow } from "@/components/defi-strategy-flow"
import type { Edge, Node } from "reactflow"
import type { ScratchBlockNodeData } from "@/components/scratch-block-node"
import { flowToParserJSON, parserJSONToFlow } from "@/lib/strategy-json-converter"
import { PeraWalletConnect } from "@perawallet/connect"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Spinner } from "@/components/ui/spinner"
import algosdk from "algosdk"

type WalletSignerTransaction = {
  txn: algosdk.Transaction
  signers?: string[]
  authAddr?: string
  msig?: unknown
  message?: string
}

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
  const [isExecuteModalOpen, setIsExecuteModalOpen] = useState(false)
  const [executeLoading, setExecuteLoading] = useState(false)
  const [executeError, setExecuteError] = useState<string | null>(null)
  const [workflowResult, setWorkflowResult] = useState<Record<string, any> | null>(null)
  const [workflowSummary, setWorkflowSummary] = useState("")
  const [walletError, setWalletError] = useState<string | null>(null)
  const [peraAccount, setPeraAccount] = useState<string | null>(null)
  const [unsignedTransactions, setUnsignedTransactions] = useState<string[] | null>(null)
  const [signedTransactions, setSignedTransactions] = useState<string[] | null>(null)
  const [transactionMetadata, setTransactionMetadata] = useState<
    { slug: string; intentId: number; workflowHash: string } | null
  >(null)
  const [signing, setSigning] = useState(false)

  const peraWallet = useMemo(() => new PeraWalletConnect({ compactMode: true }), [])

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
  const currentWorkflow = useMemo(() => {
    if (!workflowResult) return null
    const entries = Object.entries(workflowResult)
    if (entries.length === 0) return null
    const [slug, config] = entries[0]
    return { slug, config: config as Record<string, any> }
  }, [workflowResult])
  const gasEstimateLabel = builderMode === "flow" ? "~0.83 ALGO eq." : "~0.0042 ETH"
  const previewTitle = builderMode === "flow" ? "Strategy Preview" : "Transaction Preview"

  useEffect(() => {
    const interval = setInterval(() => {
      setLastSaved(new Date())
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let isMounted = true
    const reconnect = async () => {
      try {
        const accounts = await peraWallet.reconnectSession()
        if (isMounted && accounts.length > 0) {
          setPeraAccount(accounts[0])
        }
      } catch {
        // ignore reconnect errors so UI still loads
      }
    }
    reconnect()

    const handleDisconnect = () => {
      if (isMounted) {
        setPeraAccount(null)
      }
    }

    const connector = peraWallet.connector
    connector?.on("disconnect", handleDisconnect)

    return () => {
      isMounted = false
      if (connector?.off) {
        connector.off("disconnect")
      }
    }
  }, [peraWallet])

  const formatLastSaved = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)

    if (seconds < 60) return `${seconds}s ago`
    if (minutes < 60) return `${minutes}m ago`
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }

  const handleWalletDisconnect = useCallback(async () => {
    setWalletError(null)
    setUnsignedTransactions(null)
    setSignedTransactions(null)
    try {
      await peraWallet.disconnect()
    } catch {
      // ignore disconnect errors
    }
    setPeraAccount(null)
  }, [peraWallet])

  const handleConnectWallet = useCallback(async () => {
    setWalletError(null)
    try {
      const accounts = await peraWallet.connect()
      if (accounts.length > 0) {
        setPeraAccount(accounts[0])
      }
      setUnsignedTransactions(null)
      setSignedTransactions(null)
      if (peraWallet.connector?.off) {
        peraWallet.connector.off("disconnect")
      }
      peraWallet.connector?.on("disconnect", () => {
        setPeraAccount(null)
      })
    } catch (error: any) {
      setWalletError(error?.message ?? "Failed to connect wallet")
    }
  }, [peraWallet])

  const handleSignWorkflow = useCallback(async () => {
    if (!workflowResult || !currentWorkflow) {
      setWalletError("Build the workflow first")
      return
    }
    if (!peraAccount) {
      setWalletError("Connect Pera Wallet before signing")
      return
    }

    if (typeof window === "undefined") {
      setWalletError("Wallet signing is only available in the browser")
      return
    }

    setSigning(true)
    setWalletError(null)

    const base64ToBytes = (value: string) => {
      const binary = window.atob(value)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i)
      }
      return bytes
    }

    const bytesToBase64 = (bytes: Uint8Array) => {
      let binary = ""
      bytes.forEach((value) => {
        binary += String.fromCharCode(value)
      })
      return window.btoa(binary)
    }

    try {
      let localUnsigned = unsignedTransactions

      if (!localUnsigned) {
        const response = await fetch("/api/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ workflow: workflowResult, account: peraAccount }),
        })

        if (!response.ok) {
          let message = "Failed to build transactions"
          try {
            const payload = await response.json()
            if (payload?.error) {
              message = payload.error
            }
          } catch {
            // ignore parse errors
          }
          throw new Error(message)
        }

        const payload = (await response.json()) as {
          slug?: string
          transactions?: string[]
          intentId?: number
          workflowHash?: string
        }
        if (!Array.isArray(payload.transactions) || payload.transactions.length === 0) {
          throw new Error("Transaction builder returned no transactions")
        }
        localUnsigned = payload.transactions
        setUnsignedTransactions(localUnsigned)
        setSignedTransactions(null)
        setTransactionMetadata({
          slug: payload.slug ?? currentWorkflow?.slug ?? "workflow",
          intentId: typeof payload.intentId === "number" ? payload.intentId : 0,
          workflowHash: payload.workflowHash ?? "",
        })
      }

      const decodedTxns = localUnsigned.map((b64) => algosdk.decodeUnsignedTransaction(base64ToBytes(b64)))
      const signerGroup: WalletSignerTransaction[] = decodedTxns.map((txn) => ({ txn }))
      setSignedTransactions(null)
      const signed = await peraWallet.signTransaction([signerGroup as any], peraAccount)
      const encoded = signed.map((bytes) => bytesToBase64(bytes))
      setSignedTransactions(encoded)
    } catch (error: any) {
      setWalletError(error?.message ?? "Signing failed")
    } finally {
      setSigning(false)
    }
  }, [currentWorkflow, peraAccount, peraWallet, unsignedTransactions, workflowResult])

  const handleExportJSON = useCallback(() => {
    if (builderMode !== "flow" || flowNodes.length === 0) {
      alert("No strategy to export. Add blocks to the canvas first.")
      return
    }

    const strategyJSON = flowToParserJSON(flowNodes, flowEdges, "My Strategy", "Algorand", "1.0")
    const blob = new Blob([JSON.stringify(strategyJSON, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `strategy-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [builderMode, flowNodes, flowEdges])

  const handleExecute = useCallback(async () => {
    if (builderMode !== "flow") {
      setExecuteError("Switch to Scratch Flow mode to execute a strategy.")
      setIsExecuteModalOpen(true)
      return
    }

    if (flowNodes.length === 0) {
      setExecuteError("Add at least one block before executing.")
      setIsExecuteModalOpen(true)
      return
    }

    setIsExecuteModalOpen(true)
    setExecuteLoading(true)
    setExecuteError(null)
    setWorkflowResult(null)
    setWorkflowSummary("")
    setUnsignedTransactions(null)
    setSignedTransactions(null)
    setTransactionMetadata(null)
    setWalletError(null)

    try {
      const strategyJSON = flowToParserJSON(flowNodes, flowEdges, "Tinyman Workflow", "Algorand", "1.0")
      const jobName = strategyJSON.strategy_name.replace(/\s+/g, "-").toLowerCase()

      const response = await fetch("/api/workflow", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          diagramJson: strategyJSON,
          options: {
            jobName,
            description: strategyJSON.strategy_name,
          },
        }),
      })

      if (!response.ok) {
        let errorMessage = "Workflow service returned an error"
        try {
          const payload = await response.json()
          if (typeof payload?.error === "string") {
            errorMessage = payload.error
          }
        } catch {
          // swallow parse error
        }
        throw new Error(errorMessage)
      }

      const payload = await response.json()
      setWorkflowResult(payload.workflow ?? null)
      setWorkflowSummary(JSON.stringify(payload.workflow ?? {}, null, 2))
    } catch (error: any) {
      setExecuteError(error?.message ?? "Failed to build workflow")
    } finally {
      setExecuteLoading(false)
    }
  }, [builderMode, flowEdges, flowNodes])

  const handleImportJSON = useCallback(() => {
    const input = document.createElement("input")
    input.type = "file"
    input.accept = ".json"
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const json = JSON.parse(e.target?.result as string)
          const { nodes, edges } = parserJSONToFlow(json)
          setFlowNodes(nodes)
          setFlowEdges(edges)
        } catch (error) {
          alert("Failed to import JSON: " + (error instanceof Error ? error.message : "Unknown error"))
        }
      }
      reader.readAsText(file)
    }
    input.click()
  }, [])

  const handleDiagramUpdate = useCallback((nodes: Node<ScratchBlockNodeData>[], edges: Edge[]) => {
    setFlowNodes(nodes)
    setFlowEdges(edges)
  }, [])

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
            <Button variant="outline" size="sm" className="h-8 bg-transparent" onClick={handleImportJSON}>
              <Upload className="h-3.5 w-3.5 mr-2" />
              Import
            </Button>
            <Button variant="outline" size="sm" className="h-8 bg-transparent" onClick={handleExportJSON}>
              <Download className="h-3.5 w-3.5 mr-2" />
              Export
            </Button>
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
          <Button size="sm" className="h-8 bg-primary hover:bg-primary/90" onClick={handleExecute}>
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
                      <DeFiStrategyFlow 
                        initialBlocks={flowNodes}
                        initialEdges={flowEdges}
                        onNodesUpdate={setFlowNodes} 
                        onEdgesUpdate={setFlowEdges} 
                      />
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
                <CursorChat 
                  flowNodes={flowNodes} 
                  flowEdges={flowEdges} 
                  onDiagramUpdate={handleDiagramUpdate}
                />
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

      <Dialog open={isExecuteModalOpen} onOpenChange={setIsExecuteModalOpen}>
        <DialogContent className="sm:max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Play className="h-4 w-4 text-primary" />
              Execute Strategy
            </DialogTitle>
            <DialogDescription>
              We transformed your workflow into a Tinyman payload. Connect your wallet to review and sign before
              submission.
            </DialogDescription>
          </DialogHeader>

          {executeLoading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner className="h-6 w-6 text-primary" />
            </div>
          ) : executeError ? (
            <div className="flex items-start gap-3 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
              <AlertTriangle className="h-5 w-5 mt-0.5" />
              <div>
                <p className="font-semibold">Workflow build failed</p>
                <p className="mt-1 text-xs text-destructive/80">{executeError}</p>
              </div>
            </div>
          ) : currentWorkflow ? (
            <div className="space-y-5">
              <div className="rounded-xl border border-border/60 bg-muted/20 p-4 shadow-sm">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                      <CheckCircle className="h-4 w-4 text-primary" />
                      Ready to deploy
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground max-w-xl">
                      {currentWorkflow.config.description ?? "Tinyman workflow generated from your strategy diagram."}
                    </p>
                  </div>
                  <Badge variant="secondary" className="self-start text-[0.6rem] uppercase tracking-wide">
                    {currentWorkflow.slug}
                  </Badge>
                </div>
                <div className="mt-4 grid grid-cols-1 gap-3 text-xs text-muted-foreground sm:grid-cols-2">
                  <div>
                    <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Collateral</span>
                    {Number(currentWorkflow.config.collateral_microalgo ?? 0).toLocaleString()} µALGO
                  </div>
                  <div>
                    <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Keeper Override</span>
                    {currentWorkflow.config.keeper_override && currentWorkflow.config.keeper_override.length > 0
                      ? currentWorkflow.config.keeper_override
                      : "None"}
                  </div>
                  <div>
                    <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Tinyman App</span>
                    {currentWorkflow.config.app_escrow_id}
                  </div>
                  <div>
                    <span className="block text-[0.6rem] font-semibold uppercase text-foreground">LP Asset ID</span>
                    {currentWorkflow.config.app_asa_id || "N/A"}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                {(currentWorkflow.config.steps ?? []).map((step: Record<string, any>, index: number) => (
                  <div
                    key={step.name ?? index}
                    className="rounded-lg border border-border/50 bg-background/80 p-3 shadow-sm"
                  >
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[0.6rem] uppercase tracking-wide">
                          Step {index + 1}
                        </Badge>
                        <span className="text-sm font-semibold text-foreground">{step.name ?? `Step ${index + 1}`}</span>
                      </div>
                      <span className="text-[0.65rem] text-muted-foreground">Opcode {step.opcode}</span>
                    </div>
                    {step.notes ? (
                      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{step.notes}</p>
                    ) : null}
                    <div className="mt-3 grid grid-cols-1 gap-2 text-[0.65rem] text-muted-foreground sm:grid-cols-2">
                      <div>
                        <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Target App</span>
                        {step.target_app_id}
                      </div>
                      <div>
                        <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Assets</span>
                        {`${step.asset_in} → ${step.asset_out}`}
                      </div>
                      <div>
                        <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Amount</span>
                        {step.amount}
                      </div>
                      <div>
                        <span className="block text-[0.6rem] font-semibold uppercase text-foreground">Slippage</span>
                        {step.slippage_bps} bps
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="space-y-3 rounded-xl border border-border/60 bg-muted/20 p-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wallet className="h-4 w-4 text-primary" />
                    <span className="text-sm font-semibold text-foreground">Pera Wallet</span>
                  </div>
                  <Badge variant={peraAccount ? "secondary" : "outline"} className="text-[0.6rem] uppercase tracking-wide">
                    {peraAccount ? "Connected" : "Disconnected"}
                  </Badge>
                </div>

                {peraAccount ? (
                  <div className="flex items-center justify-between rounded-lg border border-border/50 bg-background/80 px-3 py-2 text-xs text-foreground">
                    <span className="font-mono text-[0.7rem]">{peraAccount}</span>
                    <Button variant="ghost" size="sm" onClick={handleWalletDisconnect}>
                      Disconnect
                    </Button>
                  </div>
                ) : (
                  <Button onClick={handleConnectWallet} className="w-full">
                    <Wallet className="h-3.5 w-3.5 mr-2" />
                    Connect Pera Wallet
                  </Button>
                )}

                {walletError ? <p className="text-xs text-destructive">{walletError}</p> : null}

                <Button
                  onClick={handleSignWorkflow}
                  disabled={!peraAccount || signing}
                  className="w-full bg-primary hover:bg-primary/90"
                >
                  {signing ? (
                    <>
                      <Spinner className="h-4 w-4 mr-2" />
                      Signing...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Build & sign transaction group
                    </>
                  )}
                </Button>

                {transactionMetadata ? (
                  <div className="rounded-lg border border-border/50 bg-background/80 px-3 py-2 space-y-2">
                    <p className="text-[0.6rem] uppercase text-muted-foreground">Intent metadata</p>
                    <div className="space-y-1 text-[0.65rem] text-foreground/90">
                      <div>
                        <span className="font-semibold text-foreground">Slug:</span> {transactionMetadata.slug}
                      </div>
                      <div>
                        <span className="font-semibold text-foreground">Intent ID:</span> {transactionMetadata.intentId}
                      </div>
                      {transactionMetadata.workflowHash ? (
                        <div>
                          <span className="block font-semibold text-foreground">Workflow hash (base64)</span>
                          <code className="block max-h-16 overflow-auto rounded bg-muted/30 px-2 py-1 text-[0.65rem] leading-relaxed text-foreground/90">
                            {transactionMetadata.workflowHash}
                          </code>
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}

                {unsignedTransactions && unsignedTransactions.length > 0 ? (
                  <div className="rounded-lg border border-border/50 bg-background/80 px-3 py-2 space-y-2">
                    <p className="text-[0.6rem] uppercase text-muted-foreground">Unsigned transactions (base64)</p>
                    <div className="space-y-1">
                      {unsignedTransactions.map((txn, index) => (
                        <code
                          key={`unsigned-${index}`}
                          className="block max-h-20 overflow-auto rounded bg-muted/30 px-2 py-1 text-[0.65rem] leading-relaxed text-foreground/90"
                        >
                          {txn}
                        </code>
                      ))}
                    </div>
                  </div>
                ) : null}

                {signedTransactions && signedTransactions.length > 0 ? (
                  <div className="rounded-lg border border-primary/40 bg-primary/5 px-3 py-2 space-y-2">
                    <p className="text-[0.6rem] uppercase text-primary">Signed group (base64)</p>
                    <div className="space-y-1">
                      {signedTransactions.map((txn, index) => (
                        <code
                          key={`signed-${index}`}
                          className="block max-h-20 overflow-auto rounded bg-background px-2 py-1 text-[0.65rem] leading-relaxed text-primary"
                        >
                          {txn}
                        </code>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>

              <div className="rounded-xl border border-border/60 bg-background/70 p-4 shadow-inner">
                <p className="mb-2 text-[0.6rem] uppercase text-muted-foreground">Raw payload</p>
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">
                  {workflowSummary}
                </pre>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm text-muted-foreground">
              Build a strategy in Scratch Flow mode to generate a workflow.
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button variant="outline" onClick={() => setIsExecuteModalOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
