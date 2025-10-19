"use client"

import { useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Copy, Trash2, GitBranch } from "lucide-react"

interface NodeDetailsDrawerProps {
  node: any | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onUpdate: (nodeId: string, data: any) => void
  onDelete: (nodeId: string) => void
  onDuplicate: (nodeId: string) => void
}

export function NodeDetailsDrawer({
  node,
  open,
  onOpenChange,
  onUpdate,
  onDelete,
  onDuplicate,
}: NodeDetailsDrawerProps) {
  const [editedData, setEditedData] = useState<Record<string, any>>(node?.data || {})

  if (!node) return null

  const handleSave = () => {
    onUpdate(node.id, editedData)
    onOpenChange(false)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <span className="text-2xl">
              {node.type === "wallet" ? "💼" : node.type === "contract" ? "📄" : node.type === "token" ? "🪙" : "⚙️"}
            </span>
            {node.label}
          </SheetTitle>
          <SheetDescription>
            <Badge variant="outline" className="mt-2">
              {node.type}
            </Badge>
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Node Details */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-foreground">Parameters</h3>
            {node.data &&
              Object.entries(node.data).map(([key, value]) => (
                <div key={key} className="space-y-2">
                  <Label htmlFor={key} className="text-xs font-medium">
                    {key}
                  </Label>
                  <Input
                    id={key}
                    value={editedData[key] || value}
                    onChange={(e) => setEditedData({ ...editedData, [key]: e.target.value })}
                    className="font-mono text-sm"
                  />
                </div>
              ))}
          </div>

          <Separator />

          {/* Quick Actions */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Quick Actions</h3>
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
                className="w-full justify-start bg-transparent"
                onClick={() => {
                  onDuplicate(node.id)
                  onOpenChange(false)
                }}
              >
                <Copy className="h-4 w-4 mr-2" />
                Duplicate Node
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start bg-transparent"
                onClick={() => {
                  // Convert to subgraph logic
                  onOpenChange(false)
                }}
              >
                <GitBranch className="h-4 w-4 mr-2" />
                Convert to Subgraph
              </Button>
              <Button
                variant="destructive"
                className="w-full justify-start"
                onClick={() => {
                  onDelete(node.id)
                  onOpenChange(false)
                }}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete Node
              </Button>
            </div>
          </div>

          <Separator />

          {/* Save/Cancel */}
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1 bg-transparent" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button className="flex-1" onClick={handleSave}>
              Save Changes
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
