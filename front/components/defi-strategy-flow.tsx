"use client"

import * as React from "react"
import ReactFlow, {
	Background,
	BackgroundVariant,
	Connection,
	ConnectionMode,
	Controls,
	Edge,
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

export interface DeFiStrategyFlowProps {
	initialBlocks?: StrategyBlockTemplate[]
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

