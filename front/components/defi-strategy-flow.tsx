"use client"

import * as React from "react"
import ReactFlow, {
	Background,
	BackgroundVariant,
	Connection,
	ConnectionMode,
	Controls,
	Edge,
	EdgeChange,
	MarkerType,
	MiniMap,
	ReactFlowProvider,
	XYPosition,
	addEdge,
	updateEdge,
	useEdgesState,
	useNodesState,
	useReactFlow,
	Node,
	NodeChange,
} from "reactflow"
import "reactflow/dist/style.css"

import { Card } from "@/components/ui/card"
import {
	ScratchBlockNode,
	ScratchBlockNodeData,
	ScratchBlockPortConfig,
	createScratchBlockNode,
} from "@/components/scratch-block-node"
import {
	StrategyBlockTemplate,
	defaultStrategyTemplates,
	defaultStrategyEdges,
	strategyPaletteTemplates,
} from "@/components/strategy-templates"

type InitialBlockInput = StrategyBlockTemplate[] | Node<ScratchBlockNodeData>[]
type FlowNode = Node<ScratchBlockNodeData>

export interface DeFiStrategyFlowProps {
	initialBlocks?: InitialBlockInput
	initialEdges?: Edge[]
	onNodesUpdate?: (nodes: Node<ScratchBlockNodeData>[]) => void
	onEdgesUpdate?: (edges: Edge[]) => void
}

const nodeTypes = { scratchBlock: ScratchBlockNode }

const SNAP_GRID: [number, number] = [20, 20]
const BLOCK_GAP = 36
const HORIZONTAL_STICK_DISTANCE = 60
const STICK_TOLERANCE = 8
const DEFAULT_BLOCK_WIDTH = 360
const ROW_TOLERANCE = 48

const getEffectiveNodeWidth = (node: Node<ScratchBlockNodeData>) => node.width ?? DEFAULT_BLOCK_WIDTH

const defaultEdgeOptions = {
	type: "smoothstep" as Edge["type"],
	animated: true,
	markerEnd: {
		type: MarkerType.ArrowClosed,
		width: 16,
		height: 16,
		color: "#1e293b",
	},
	style: {
		strokeWidth: 2,
		stroke: "#1e293b",
	},
}

const signatureForNodes = (nodes: FlowNode[]) =>
	JSON.stringify(
		nodes.map((node) => ({
			id: node.id,
			position: node.position,
			data: {
				title: node.data.title,
				typeLabel: node.data.typeLabel,
				description: node.data.description,
				values: node.data.values,
				variant: node.data.variant,
				accentColor: node.data.accentColor,
				backgroundColor: node.data.backgroundColor,
			},
		})),
	)

const signatureForEdges = (edges: Edge[]) =>
	JSON.stringify(
		edges.map((edge) => ({
			id: edge.id,
			source: edge.source,
			target: edge.target,
			sourceHandle: edge.sourceHandle,
			targetHandle: edge.targetHandle,
			type: edge.type,
		})),
	)

const isFlowNodeArray = (items: InitialBlockInput): items is Node<ScratchBlockNodeData>[] =>
	items.length > 0 && "type" in items[0] && "data" in items[0]

export function DeFiStrategyFlow({
	initialBlocks,
	initialEdges,
	onNodesUpdate,
	onEdgesUpdate,
}: DeFiStrategyFlowProps) {
	return (
		<ReactFlowProvider>
			<StrategyFlowCanvas
				initialBlocks={initialBlocks}
				initialEdges={initialEdges}
				onNodesUpdate={onNodesUpdate}
				onEdgesUpdate={onEdgesUpdate}
			/>
		</ReactFlowProvider>
	)
}

interface StrategyFlowCanvasProps extends DeFiStrategyFlowProps {}

const generateEdgeId = () =>
	typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
		? crypto.randomUUID()
		: `edge-${Math.random().toString(36).slice(2)}`

const snapToGridPosition = (position: XYPosition): XYPosition => ({
	x: Math.round(position.x / SNAP_GRID[0]) * SNAP_GRID[0],
	y: Math.round(position.y / SNAP_GRID[1]) * SNAP_GRID[1],
})

const alignToExistingRow = (position: XYPosition, nodes: FlowNode[]): XYPosition => {
	let closestY = position.y
	let smallestDistance = Number.POSITIVE_INFINITY

	for (const candidate of nodes) {
		const distance = Math.abs(candidate.position.y - position.y)
		if (distance <= ROW_TOLERANCE && distance < smallestDistance) {
			smallestDistance = distance
			closestY = candidate.position.y
		}
	}

	return { x: position.x, y: closestY }
}

const stickHorizontallyToNeighbors = (node: FlowNode, neighbors: FlowNode[]): XYPosition => {
	const nodeWidth = getEffectiveNodeWidth(node)
	const rowPeers = neighbors.filter(
		(peer) => Math.abs(peer.position.y - node.position.y) <= ROW_TOLERANCE + STICK_TOLERANCE,
	)

	if (rowPeers.length === 0) {
		return node.position
	}

	let targetX = node.position.x
	let bestDelta = Number.POSITIVE_INFINITY
	let snapped = false

	for (const peer of rowPeers) {
		if (peer.position.x <= node.position.x) {
			const desired = peer.position.x + getEffectiveNodeWidth(peer) + BLOCK_GAP
			const delta = Math.abs(desired - node.position.x)
			if (delta <= HORIZONTAL_STICK_DISTANCE && delta < bestDelta) {
				targetX = desired
				bestDelta = delta
				snapped = true
			}
		}
	}

	if (!snapped) {
		for (const peer of rowPeers) {
			if (peer.position.x >= node.position.x) {
				const desired = peer.position.x - nodeWidth - BLOCK_GAP
				const delta = Math.abs(desired - node.position.x)
				if (delta <= HORIZONTAL_STICK_DISTANCE && delta < bestDelta) {
					targetX = desired
					bestDelta = delta
				}
			}
		}
	}

	return {
		x: Math.max(0, targetX),
		y: node.position.y,
	}
}

const computeStickyPosition = (node: FlowNode, others: FlowNode[]): XYPosition => {
	const snapped = snapToGridPosition(node.position)
	const aligned = alignToExistingRow(snapped, others)
	const intermediate: FlowNode = { ...node, position: aligned }
	return stickHorizontallyToNeighbors(intermediate, others)
}

const decorateEdge = (edge: Edge): Edge => ({
	...edge,
	type: edge.type ?? defaultEdgeOptions.type,
	animated: edge.animated ?? defaultEdgeOptions.animated,
	markerEnd: edge.markerEnd ?? defaultEdgeOptions.markerEnd,
	style: { ...defaultEdgeOptions.style, ...(edge.style ?? {}) },
})

const autoConnectRowNeighbors = (edges: Edge[], node: FlowNode, nodes: FlowNode[]): Edge[] => {
	const rowPeers = nodes.filter((candidate) => Math.abs(candidate.position.y - node.position.y) <= ROW_TOLERANCE)
	if (rowPeers.length <= 1) {
		return edges
	}

	const orderedPeers = [...rowPeers].sort((a, b) => a.position.x - b.position.x)
	const index = orderedPeers.findIndex((candidate) => candidate.id === node.id)
	if (index === -1) {
		return edges
	}

	let nextEdges = edges.slice()

	const ensureEdge = (sourceNode: FlowNode, targetNode: FlowNode) => {
		const sourceHandle = sourceNode.data.outputs?.[0]?.id
		const targetHandle = targetNode.data.inputs?.[0]?.id
		if (!sourceHandle || !targetHandle) {
			return
		}

		const exists = nextEdges.some(
			(edge) =>
				edge.source === sourceNode.id &&
				edge.target === targetNode.id &&
				(edge.sourceHandle ?? sourceHandle) === sourceHandle &&
				(edge.targetHandle ?? targetHandle) === targetHandle,
		)

		if (exists) {
			return
		}

		nextEdges = [
			...nextEdges,
			decorateEdge({
				id: generateEdgeId(),
				source: sourceNode.id,
				target: targetNode.id,
				sourceHandle,
				targetHandle,
			}),
		]
	}

	if (index > 0) {
		ensureEdge(orderedPeers[index - 1], orderedPeers[index])
	}

	if (index < orderedPeers.length - 1) {
		ensureEdge(orderedPeers[index], orderedPeers[index + 1])
	}

	return nextEdges
}

function StrategyFlowCanvas({
	initialBlocks,
	initialEdges,
	onNodesUpdate,
	onEdgesUpdate,
}: StrategyFlowCanvasProps) {
	const reactFlow = useReactFlow<ScratchBlockNodeData>()
	const containerRef = React.useRef<HTMLDivElement | null>(null)
	const hasFitView = React.useRef(false)

	const nodesSignatureRef = React.useRef<string>("")
	const edgesSignatureRef = React.useRef<string>("")
	const [nodes, setNodes, onNodesChangeInternal] = useNodesState<ScratchBlockNodeData>([])
	const [edges, setEdges, onEdgesChangeInternal] = useEdgesState<Edge>([])

	const handleNodeDataChange = React.useCallback(
		(nodeId: string, updates: Record<string, unknown>) => {
			setNodes((prev) =>
				prev.map((node) => {
					if (node.id !== nodeId) return node
					return {
						...node,
						data: {
							...node.data,
							values: {
								...(node.data.values ?? {}),
								...updates,
							},
						},
					}
				})
			)
		},
		[setNodes],
	)

	const handleNodeDelete = React.useCallback(
		(nodeId: string) => {
			setNodes((prev) => prev.filter((node) => node.id !== nodeId))
			setEdges((prev) => prev.filter((edge) => edge.source !== nodeId && edge.target !== nodeId))
		},
		[setNodes, setEdges],
	)

	const attachNodeCallbacks = React.useCallback(
		(node: FlowNode): FlowNode => ({
			...node,
			data: {
				...node.data,
				onDataChange: handleNodeDataChange,
				onDelete: handleNodeDelete,
			},
		}),
		[handleNodeDataChange, handleNodeDelete],
	)

	const memoizedInitialNodes = React.useMemo(() => {
		if (!initialBlocks || initialBlocks.length === 0) {
			return defaultStrategyTemplates.map((template) => attachNodeCallbacks(createScratchBlockNode(template)))
		}
		if (isFlowNodeArray(initialBlocks)) {
			return initialBlocks.map((node) => attachNodeCallbacks(node))
		}
		return initialBlocks.map((template) => attachNodeCallbacks(createScratchBlockNode(template)))
	}, [initialBlocks, attachNodeCallbacks])

	const memoizedInitialEdges = React.useMemo(() => {
		const sourceEdges = initialEdges ?? defaultStrategyEdges
		return sourceEdges.map(decorateEdge)
	}, [initialEdges])

	// Sync nodes when initialBlocks change, avoid redundant resets
	React.useEffect(() => {
		const nextSignature = signatureForNodes(memoizedInitialNodes)
		if (nodesSignatureRef.current !== nextSignature) {
			nodesSignatureRef.current = nextSignature
			setNodes(memoizedInitialNodes)
		}
	}, [memoizedInitialNodes, setNodes])

	React.useEffect(() => {
		nodesSignatureRef.current = signatureForNodes(nodes)
	}, [nodes])

	React.useEffect(() => {
		const nextSignature = signatureForEdges(memoizedInitialEdges)
		if (edgesSignatureRef.current !== nextSignature) {
			edgesSignatureRef.current = nextSignature
			setEdges(memoizedInitialEdges)
		}
	}, [memoizedInitialEdges, setEdges])

	React.useEffect(() => {
		edgesSignatureRef.current = signatureForEdges(edges)
	}, [edges])

	React.useEffect(() => {
		onNodesUpdate?.(nodes)
	}, [nodes, onNodesUpdate])

	React.useEffect(() => {
		onEdgesUpdate?.(edges)
	}, [edges, onEdgesUpdate])

	React.useEffect(() => {
		if (!hasFitView.current && nodes.length > 0) {
			hasFitView.current = true
			reactFlow.fitView({ padding: 0.2 })
		}
	}, [nodes, reactFlow])

	const handleDragOver = React.useCallback((event: React.DragEvent<HTMLDivElement>) => {
		event.preventDefault()
		event.dataTransfer.dropEffect = "move"
	}, [])

	const handleDrop = React.useCallback(
		(event: React.DragEvent<HTMLDivElement>) => {
			event.preventDefault()
			if (!containerRef.current) return

			const templateId =
				event.dataTransfer.getData("application/x-algoflow-block") ||
				event.dataTransfer.getData("application/reactflow") ||
				event.dataTransfer.getData("text/plain")
			if (!templateId) return

			const template = strategyPaletteTemplates[templateId]
			if (!template) return

			const bounds = containerRef.current.getBoundingClientRect()
			const position = reactFlow.project({
				x: event.clientX - bounds.left,
				y: event.clientY - bounds.top,
			})

			const baseNode = attachNodeCallbacks(
				createScratchBlockNode({
					...template,
					id: undefined,
					position,
				}),
			)

			setNodes((prevNodes) => {
				const stickyPosition = computeStickyPosition(baseNode, prevNodes)
				const nextNode = { ...baseNode, position: stickyPosition }
				const nextNodes = [...prevNodes, nextNode]

				setEdges((prevEdges) => autoConnectRowNeighbors(prevEdges, nextNode, nextNodes))

				return nextNodes
			})
		},
		[attachNodeCallbacks, reactFlow, setNodes, setEdges],
	)

	const handleNodeDragStop = React.useCallback(
		(_: React.MouseEvent, dragged: FlowNode) => {
			setNodes((prevNodes) => {
				const current = prevNodes.find((node) => node.id === dragged.id)
				if (!current) return prevNodes

				const others = prevNodes.filter((node) => node.id !== dragged.id)
				const stickyPosition = computeStickyPosition({ ...current, position: dragged.position }, others)
				const updatedNode = { ...current, position: stickyPosition }
				const nextNodes = prevNodes.map((node) => (node.id === dragged.id ? updatedNode : node))

				setEdges((prevEdges) => autoConnectRowNeighbors(prevEdges, updatedNode, nextNodes))

				return nextNodes
			})
		},
		[setNodes, setEdges],
	)

	const handleNodesChange = React.useCallback(
		(changes: NodeChange[]) => {
			onNodesChangeInternal(changes)
		},
		[onNodesChangeInternal],
	)

	const handleEdgesChange = React.useCallback(
		(changes: EdgeChange[]) => {
			onEdgesChangeInternal(changes)
		},
		[onEdgesChangeInternal],
	)

	const handleConnect = React.useCallback(
		(connection: Connection) => {
			setEdges((prevEdges) => addEdge({ ...defaultEdgeOptions, ...connection }, prevEdges))
		},
		[setEdges],
	)

	const handleEdgeUpdate = React.useCallback(
		(oldEdge: Edge, newConnection: Connection) => {
			setEdges((prevEdges) => {
				const updated = updateEdge(oldEdge, newConnection, prevEdges)
				return updated.map(decorateEdge)
			})
		},
		[setEdges],
	)

	return (
		<Card className="h-full overflow-hidden border border-border/60 bg-background/40 shadow-sm">
			<div ref={containerRef} className="h-full">
				<ReactFlow
					nodes={nodes}
					edges={edges}
					nodeTypes={nodeTypes}
					defaultEdgeOptions={defaultEdgeOptions}
					snapToGrid
					snapGrid={SNAP_GRID}
					attributionPosition="bottom-right"
					connectionMode={ConnectionMode.Strict}
					onNodesChange={handleNodesChange}
					onEdgesChange={handleEdgesChange}
					onNodeDragStop={handleNodeDragStop}
					onConnect={handleConnect}
					onEdgeUpdate={handleEdgeUpdate}
					onDrop={handleDrop}
					onDragOver={handleDragOver}
					fitView
					className="h-full"
				>
					<Background color="#cbd5f5" gap={24} size={1} variant={BackgroundVariant.Dots} />
					<MiniMap
						nodeColor={(node) => node.data.accentColor ?? "#1e293b"}
						maskColor="rgba(15, 23, 42, 0.12)"
					/>
					<Controls position="top-left" showInteractive={false} />
				</ReactFlow>
			</div>
		</Card>
	)
}

