"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Send, Sparkles, Code, Copy, Check, Plus, Eye } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Node, Edge } from "reactflow"
import type { ScratchBlockNodeData } from "@/components/scratch-block-node"
import { flowToParserJSON, parserJSONToFlow, type ParserStrategyJSON } from "@/lib/strategy-json-converter"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  code?: string
  actions?: { label: string; icon: React.ReactNode }[]
  context?: { label: string; value: string }[]
  diagramJson?: ParserStrategyJSON | null
}

interface CursorChatProps {
  flowNodes?: Node<ScratchBlockNodeData>[]
  flowEdges?: Edge[]
  onDiagramUpdate?: (nodes: Node<ScratchBlockNodeData>[], edges: Edge[]) => void
}

export function CursorChat({ flowNodes = [], flowEdges = [], onDiagramUpdate }: CursorChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "Hello! I'm your AI assistant. I can help you build blockchain transactions visually. What would you like to create?",
      timestamp: new Date(),
      actions: [
        { label: "Add new block", icon: <Plus className="h-3 w-3" /> },
        { label: "Swap tokens", icon: <Code className="h-3 w-3" /> },
        { label: "Create liquidity pool", icon: <Sparkles className="h-3 w-3" /> },
      ],
    },
  ])

  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // Scroll to bottom when messages change
    if (scrollRef.current) {
      const scrollViewport = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight
      } else {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      }
    }
  }, [messages, isTyping])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    const userInput = input
    setInput("")
    setIsTyping(true)

    try {
      // Convert current flow to parser JSON
      const currentDiagram = flowNodes.length > 0 
        ? flowToParserJSON(flowNodes, flowEdges)
        : null

      // Call the agent API
      const response = await fetch("/api/agent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          userInput,
          diagramJson: currentDiagram,
          registryJson: null, // Will use default registry
        }),
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`)
      }

      const data = await response.json()

      // Create AI message
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.commentary || "I've processed your request.",
        timestamp: new Date(),
        diagramJson: data.diagram_json,
      }

      // If we have a new diagram, update the flow
      if (data.diagram_json && onDiagramUpdate) {
        const { nodes, edges } = parserJSONToFlow(data.diagram_json)
        onDiagramUpdate(nodes, edges)

        aiMessage.actions = [
          { label: "Strategy updated", icon: <Check className="h-3 w-3" /> },
        ]
        aiMessage.context = [
          { label: "Blocks", value: String(nodes.length) },
          { label: "Network", value: data.diagram_json.network },
        ]
      } else if (!data.diagram_json && data.commentary) {
        aiMessage.context = [
          { label: "Status", value: "No diagram changes" },
        ]
      }

      setMessages((prev) => [...prev, aiMessage])
    } catch (error) {
      console.error("Agent error:", error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `I encountered an error: ${error instanceof Error ? error.message : "Unknown error"}. Please try again.`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCopy = (code: string, id: string) => {
    navigator.clipboard.writeText(code)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="h-full flex flex-col bg-card overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Avatar className="h-9 w-9 bg-primary/20 border border-primary/30">
              <div className="flex items-center justify-center w-full h-full">
                <Sparkles className="h-5 w-5 text-primary" />
              </div>
            </Avatar>
            <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 bg-accent rounded-full border-2 border-card" />
          </div>
          <div className="flex-1">
            <h2 className="font-semibold text-foreground">AI Assistant</h2>
            <p className="text-xs text-muted-foreground">Online</p>
          </div>
          <Badge variant="secondary" className="text-xs">
            GPT-4
          </Badge>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}
            >
              {message.role === "assistant" && (
                <Avatar className="h-8 w-8 bg-primary/20 border border-primary/30 flex-shrink-0">
                  <div className="flex items-center justify-center w-full h-full">
                    <Sparkles className="h-4 w-4 text-primary" />
                  </div>
                </Avatar>
              )}

              <div className={cn("max-w-[85%] space-y-2", message.role === "user" ? "items-end" : "items-start")}>
                {message.context && message.context.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {message.context.map((ctx, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs font-mono">
                        {ctx.label}: {ctx.value}
                      </Badge>
                    ))}
                  </div>
                )}

                <div
                  className={cn(
                    "rounded-lg p-3 text-sm",
                    message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
                  )}
                >
                  <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
                </div>

                {message.code && (
                  <div className="bg-secondary/50 rounded-lg border border-border overflow-hidden">
                    <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-secondary/30">
                      <div className="flex items-center gap-2">
                        <Code className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs font-medium text-foreground">Code</span>
                      </div>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-6 w-6"
                        onClick={() => handleCopy(message.code!, message.id)}
                      >
                        {copiedId === message.id ? (
                          <Check className="h-3 w-3 text-accent" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <pre className="p-3 text-xs font-mono overflow-x-auto">
                      <code className="text-foreground">{message.code}</code>
                    </pre>
                  </div>
                )}

                {message.actions && message.actions.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.actions.map((action, idx) => (
                      <Button key={idx} variant="outline" size="sm" className="h-7 text-xs bg-transparent">
                        {action.icon}
                        <span className="ml-1.5">{action.label}</span>
                      </Button>
                    ))}
                  </div>
                )}

                <span className="text-xs text-muted-foreground px-1">
                  {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>

              {message.role === "user" && (
                <Avatar className="h-8 w-8 bg-accent/20 border border-accent/30 flex-shrink-0">
                  <div className="flex items-center justify-center w-full h-full text-xs font-semibold text-accent-foreground">
                    U
                  </div>
                </Avatar>
              )}
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3">
              <Avatar className="h-8 w-8 bg-primary/20 border border-primary/30">
                <div className="flex items-center justify-center w-full h-full">
                  <Sparkles className="h-4 w-4 text-primary" />
                </div>
              </Avatar>
              <div className="bg-muted rounded-lg p-3">
                <div className="flex gap-1">
                  <div
                    className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="flex-shrink-0 p-4 border-t border-border">
        <div className="relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything about blockchain transactions..."
            className="min-h-[80px] pr-12 resize-none bg-background"
          />
          <Button
            size="icon"
            onClick={handleSend}
            disabled={!input.trim()}
            className="absolute bottom-2 right-2 h-8 w-8"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">Press Enter to send, Shift+Enter for new line</p>
      </div>
    </div>
  )
}
