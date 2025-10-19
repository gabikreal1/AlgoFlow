"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Wallet,
  FileCode,
  Coins,
  Settings,
  Database,
  Lock,
  ArrowLeftRight,
  Droplets,
  HandCoins,
  TrendingUp,
  GitBranch,
  Flag,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { strategyPaletteTemplates } from "@/components/strategy-templates"

interface Component {
  id: string
  type: "wallet" | "contract" | "token" | "function" | "defi" | "storage" | "security" | "bridge" | "logic" | "marker"
  name: string
  description: string
  icon: React.ReactNode
  color: string
}

const components: Component[] = [
  {
    id: "wallet-1",
    type: "wallet",
    name: "Wallet Address",
    description: "Connect a wallet address",
    icon: <Wallet className="h-4 w-4" />,
    color: "bg-primary/20 border-primary text-primary",
  },
  {
    id: "wallet-2",
    type: "wallet",
    name: "Multi-Sig Wallet",
    description: "Multi-signature wallet",
    icon: <Wallet className="h-4 w-4" />,
    color: "bg-primary/20 border-primary text-primary",
  },
  {
    id: "contract-1",
    type: "contract",
    name: "Smart Contract",
    description: "Deploy or interact with contract",
    icon: <FileCode className="h-4 w-4" />,
    color: "bg-accent/20 border-accent text-accent",
  },
  {
    id: "contract-2",
    type: "contract",
    name: "ERC-20 Contract",
    description: "Standard token contract",
    icon: <FileCode className="h-4 w-4" />,
    color: "bg-accent/20 border-accent text-accent",
  },
  {
    id: "contract-3",
    type: "contract",
    name: "ERC-721 Contract",
    description: "NFT contract",
    icon: <FileCode className="h-4 w-4" />,
    color: "bg-accent/20 border-accent text-accent",
  },
  {
    id: "token-1",
    type: "token",
    name: "Token Transfer",
    description: "Transfer tokens",
    icon: <Coins className="h-4 w-4" />,
    color: "bg-chart-2/20 border-chart-2 text-chart-2",
  },
  {
    id: "token-2",
    type: "token",
    name: "Token Approval",
    description: "Approve token spending",
    icon: <Coins className="h-4 w-4" />,
    color: "bg-chart-2/20 border-chart-2 text-chart-2",
  },
  {
    id: "function-1",
    type: "function",
    name: "Function Call",
    description: "Call contract function",
    icon: <Settings className="h-4 w-4" />,
    color: "bg-chart-3/20 border-chart-3 text-chart-3",
  },
  {
    id: "logic-conditional-wrapper",
    type: "logic",
    name: "Conditional Wrapper",
    description: "Wrap a branch with pass/fail logic",
    icon: <GitBranch className="h-4 w-4" />,
    color: "bg-fuchsia-500/15 border-fuchsia-500 text-fuchsia-600",
  },
  {
    id: "defi-1",
    type: "defi",
    name: "Swap",
    description: "Swap tokens on DEX",
    icon: <ArrowLeftRight className="h-4 w-4" />,
    color: "bg-chart-4/20 border-chart-4 text-chart-4",
  },
  {
    id: "defi-2",
    type: "defi",
    name: "Provide Liquidity",
    description: "Add liquidity to pool",
    icon: <Droplets className="h-4 w-4" />,
    color: "bg-chart-4/20 border-chart-4 text-chart-4",
  },
  {
    id: "defi-3",
    type: "defi",
    name: "Lend",
    description: "Lend assets to protocol",
    icon: <HandCoins className="h-4 w-4" />,
    color: "bg-chart-4/20 border-chart-4 text-chart-4",
  },
  {
    id: "defi-4",
    type: "defi",
    name: "Borrow",
    description: "Borrow assets from protocol",
    icon: <TrendingUp className="h-4 w-4" />,
    color: "bg-chart-4/20 border-chart-4 text-chart-4",
  },
  {
    id: "defi-5",
    type: "defi",
    name: "Stake",
    description: "Stake tokens in pool",
    icon: <Lock className="h-4 w-4" />,
    color: "bg-chart-4/20 border-chart-4 text-chart-4",
  },
  {
    id: "marker-1",
    type: "marker",
    name: "Sequence Stage",
    description: "Mark entry or exit stages",
    icon: <Flag className="h-4 w-4" />,
    color: "bg-sky-500/15 border-sky-500 text-sky-600",
  },
  {
    id: "storage-1",
    type: "storage",
    name: "Store Data",
    description: "Store on-chain data",
    icon: <Database className="h-4 w-4" />,
    color: "bg-chart-5/20 border-chart-5 text-chart-5",
  },
]

interface ComponentPaletteProps {
  activeTab: string
}

export function ComponentPalette({ activeTab }: ComponentPaletteProps) {
  const [draggedComponent, setDraggedComponent] = useState<string | null>(null)

  const filteredComponents = activeTab === "all" ? components : components.filter((comp) => comp.type === activeTab)

  const handleDragStart = (event: React.DragEvent<HTMLButtonElement>, componentId: string) => {
    if (!strategyPaletteTemplates[componentId]) {
      return
    }

    setDraggedComponent(componentId)
    event.dataTransfer.effectAllowed = "move"
    event.dataTransfer.setData("application/x-algoflow-block", componentId)
    event.dataTransfer.setData("application/reactflow", componentId)
    event.dataTransfer.setData("text/plain", componentId)
  }

  const handleDragEnd = () => {
    setDraggedComponent(null)
  }

  return (
    <div className="h-full flex flex-col bg-card">
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4">
          <div className="grid grid-cols-2 gap-2">
            {filteredComponents.map((component) => {
              const hasTemplate = Boolean(strategyPaletteTemplates[component.id])

              return (
              <button
                key={component.id}
                type="button"
                draggable={hasTemplate}
                onDragStart={(event) => handleDragStart(event, component.id)}
                onDragEnd={handleDragEnd}
                className={cn(
                  "group relative p-3 rounded-lg border-2 transition-all cursor-grab active:cursor-grabbing",
                  "hover:shadow-md hover:scale-105",
                  component.color,
                  draggedComponent === component.id && "opacity-50 scale-95",
                  !hasTemplate && "cursor-not-allowed opacity-60 hover:scale-100",
                )}
                aria-grabbed={draggedComponent === component.id}
              >
                <div className="flex flex-col items-start gap-2">
                  <div className="flex items-center justify-between w-full">
                    <div className={cn("p-1.5 rounded", component.color)}>{component.icon}</div>
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Badge variant="outline" className="text-xs">
                        Drag
                      </Badge>
                    </div>
                  </div>
                  <div className="text-left">
                    <h4 className="font-medium text-xs text-foreground mb-0.5">{component.name}</h4>
                    <p className="text-xs text-muted-foreground line-clamp-1">{component.description}</p>
                  </div>
                </div>

                {/* Drag indicator */}
                <div className="absolute inset-0 rounded-lg border-2 border-dashed border-primary opacity-0 group-hover:opacity-30 pointer-events-none" />
              </button>
              )
            })}
          </div>
        </div>
      </ScrollArea>

      {/* Quick Actions */}
      <div className="p-3 border-t border-border bg-muted/30">
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="flex-1 text-xs h-8 bg-transparent">
            Templates
          </Button>
          <Button variant="outline" size="sm" className="flex-1 text-xs h-8 bg-transparent">
            Custom
          </Button>
        </div>
      </div>
    </div>
  )
}
