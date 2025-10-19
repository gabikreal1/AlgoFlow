"use client"

import * as React from "react"
import { Handle, NodeProps, Node, Position, XYPosition } from "reactflow"

import { cn } from "@/lib/utils"

export type ScratchBlockFieldType = "text" | "number" | "select" | "textarea"

export interface ScratchBlockFieldOption {
  label: string
  value: string
}

export interface ScratchBlockFieldConfig {
  key: string
  label: string
  type?: ScratchBlockFieldType
  placeholder?: string
  options?: ScratchBlockFieldOption[]
  helperText?: string
}

export type ScratchBlockPortSide = "left" | "right" | "top" | "bottom"

export interface ScratchBlockPortConfig {
  id: string
  label?: string
  side?: ScratchBlockPortSide
  position?: number
}

export interface ScratchBlockNodeData {
  title: string
  typeLabel: string
  accentColor?: string
  backgroundColor?: string
  description?: string
  fields?: ScratchBlockFieldConfig[]
  values?: Record<string, unknown>
  inputs?: ScratchBlockPortConfig[]
  outputs?: ScratchBlockPortConfig[]
  variant?: "default" | "tall" | "marker"
  onDataChange?: (nodeId: string, updates: Record<string, unknown>) => void
  onDelete?: (nodeId: string) => void
}

export interface CreateScratchBlockNodeArgs {
  id?: string
  position: XYPosition
  title: string
  typeLabel: string
  accentColor?: string
  backgroundColor?: string
  description?: string
  fields?: ScratchBlockFieldConfig[]
  values?: Record<string, unknown>
  inputs?: ScratchBlockPortConfig[]
  outputs?: ScratchBlockPortConfig[]
  variant?: ScratchBlockNodeData["variant"]
  onDataChange?: ScratchBlockNodeData["onDataChange"]
  onDelete?: ScratchBlockNodeData["onDelete"]
}

const clamp = (value: number) => Math.min(Math.max(value, 0), 1)

const hexToRgb = (hex: string): [number, number, number] | null => {
  const normalized = hex.replace("#", "")
  if (normalized.length !== 6) return null
  const bigint = Number.parseInt(normalized, 16)
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255
  return [r, g, b]
}

const toRgba = (hex: string, alpha: number) => {
  const rgb = hexToRgb(hex)
  if (!rgb) return `rgba(99, 102, 241, ${alpha})`
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`
}

const getHandlePosition = (side: ScratchBlockPortSide = "left") => {
  switch (side) {
    case "right":
      return Position.Right
    case "top":
      return Position.Top
    case "bottom":
      return Position.Bottom
    default:
      return Position.Left
  }
}

const buildHandleStyles = (
  config: ScratchBlockPortConfig,
  accent: string,
): { handle: React.CSSProperties; label: React.CSSProperties } => {
  const side = config.side ?? "top"
  const ratio = clamp(config.position ?? 0.5)

  const baseValue = `${ratio * 100}%`
  const handleStyle: React.CSSProperties = {
    backgroundColor: accent,
    border: `2px solid ${accent}`,
    width: 12,
    height: 12,
    borderRadius: "9999px",
    boxShadow: `0 0 0 3px rgba(255, 255, 255, 0.95), 0 0 16px ${accent}40`,
  }
  const labelStyle: React.CSSProperties = {
    position: "absolute",
    fontSize: "0.65rem",
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "rgba(15, 23, 42, 0.8)",
    pointerEvents: "none",
    whiteSpace: "nowrap",
  }

  if (side === "left" || side === "right") {
    handleStyle.top = baseValue
    handleStyle.transform = "translateY(-50%)"
    labelStyle.top = baseValue
    labelStyle.transform = "translateY(-50%)"
  } else {
    handleStyle.left = baseValue
    handleStyle.transform = "translateX(-50%)"
    labelStyle.left = baseValue
    labelStyle.transform = "translateX(-50%)"
  }

  switch (side) {
    case "left":
      labelStyle.left = "-0.5rem"
      labelStyle.transform = `${labelStyle.transform ?? ""} translateX(-100%)`
      break
    case "right":
      labelStyle.left = "calc(100% + 0.5rem)"
      break
    case "top":
      labelStyle.top = "-0.75rem"
      break
    case "bottom":
      labelStyle.top = "calc(100% + 0.25rem)"
      break
    default:
      break
  }

  return { handle: handleStyle, label: labelStyle }
}

const generateNodeId = () =>
  (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `scratch-block-${Math.random().toString(16).slice(2)}`)

export const ScratchBlockNode = ({ id, data, selected }: NodeProps<ScratchBlockNodeData>) => {
  const accent = data.accentColor ?? "#6366f1"
  const fields: ScratchBlockFieldConfig[] = data.fields ?? []
  const values: Record<string, unknown> = data.values ?? {}
  const inputs: ScratchBlockPortConfig[] = data.inputs ?? []
  const outputs: ScratchBlockPortConfig[] = data.outputs ?? []
  const variant = data.variant ?? "default"

  const emitChange = React.useCallback(
    (key: string, value: unknown) => {
      data.onDataChange?.(id, { [key]: value })
    },
    [data, id],
  )

  const friendlyId = React.useMemo(() => {
    if (!id) return "NODE"
    const segment = id.split("-").filter(Boolean).pop() ?? id
    return segment.slice(-4).toUpperCase()
  }, [id])

  const gradientStart = toRgba(accent, 0.92)
  const baseColor =
    data.backgroundColor && data.backgroundColor.startsWith("#")
      ? toRgba(data.backgroundColor, 0.65)
      : toRgba(accent, 0.6)
  const accentShadow = toRgba(accent, 0.35)
  const containerStyle: React.CSSProperties = {
    borderColor: accent,
    background: `linear-gradient(140deg, ${gradientStart} 0%, ${baseColor} 100%)`,
    boxShadow: `0 14px 28px ${accentShadow}`,
    color: "#0f172a",
  }

  if (selected) {
    containerStyle.outline = `2px solid ${accent}`
    containerStyle.outlineOffset = 4
  }

  return (
    <div
      className={cn(
        "group relative flex w-[360px] flex-col rounded-2xl border-2 text-left shadow-xl transition-all",
        variant === "tall"
          ? "min-h-[520px] px-5 py-4"
          : variant === "marker"
            ? "min-h-[200px] px-5 py-3"
            : "min-h-[260px] px-5 py-3",
        selected ? "shadow-2xl scale-[1.01]" : "shadow-lg",
      )}
      style={containerStyle}
    >
      <button
        type="button"
        aria-label="Delete block"
        onClick={(event) => {
          event.stopPropagation()
          data.onDelete?.(id)
        }}
        className={cn(
          "absolute right-3 top-3 hidden items-center gap-1 rounded-full border border-white/70 bg-white/80 px-2 py-1 text-[0.55rem] font-semibold uppercase tracking-[0.18em] text-rose-600 shadow-sm transition hover:bg-white group-hover:inline-flex",
          selected && "inline-flex",
        )}
      >
        <span aria-hidden>&times;</span>
        Delete
      </button>
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1.5">
          <span
            className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/80 px-2.5 py-1 text-[0.55rem] font-semibold uppercase tracking-[0.18em] text-slate-600 shadow-sm"
          >
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: accent }} />
            <span style={{ color: accent }}>{data.typeLabel}</span>
          </span>
          <h3 className="text-base font-semibold text-slate-900">{data.title}</h3>
          {data.description ? <p className="max-w-[300px] text-xs text-slate-600">{data.description}</p> : null}
        </div>
        <div className="flex flex-col items-end gap-1 text-[0.6rem] font-medium text-slate-500">
          <span className="rounded-full bg-white/80 px-2 py-1 font-mono text-[0.6rem] tracking-wide text-slate-600 shadow-sm">
            #{friendlyId}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white/70 px-2 py-1 text-[0.6rem] shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: accent }} />
            {inputs.length} in • {outputs.length} out
          </span>
        </div>
      </div>

      {fields.length > 0 ? (
        <div className={cn("mt-3 space-y-2.5", variant === "tall" && "flex-1")}
        >
          {fields.map((field: ScratchBlockFieldConfig) => {
            const fieldType = field.type ?? "text"
            const rawValue = values[field.key]
            const value = rawValue === undefined || rawValue === null ? "" : rawValue

            return (
              <div key={field.key} className="space-y-1 rounded-xl border border-white/70 bg-white/80 px-3 py-2 shadow-sm">
                <label className="text-[0.65rem] font-semibold uppercase tracking-wide text-slate-600">
                  {field.label}
                </label>
                {fieldType === "select" ? (
                  <select
                    value={String(value)}
                    onChange={(event: React.ChangeEvent<HTMLSelectElement>) => emitChange(field.key, event.target.value)}
                    className="w-full rounded-md border border-white/40 bg-white px-3 py-1.5 text-sm shadow-inner outline-none transition focus:border-transparent focus:ring-2 focus:ring-slate-300"
                  >
                    {(field.options ?? []).map((option: ScratchBlockFieldOption) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                ) : fieldType === "textarea" ? (
                  <textarea
                    value={String(value)}
                    placeholder={field.placeholder}
                    onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => emitChange(field.key, event.target.value)}
                    className="w-full rounded-md border border-white/40 bg-white px-3 py-1.5 text-sm shadow-inner outline-none transition focus:border-transparent focus:ring-2 focus:ring-slate-300"
                    rows={3}
                  />
                ) : (
                  <input
                    type={fieldType === "number" ? "number" : "text"}
                    value={fieldType === "number" ? (value === "" ? "" : Number(value)) : String(value)}
                    placeholder={field.placeholder}
                    onChange={(event: React.ChangeEvent<HTMLInputElement>) => {
                      const nextValue = event.target.value
                      const incoming = fieldType === "number" ? (nextValue === "" ? "" : Number(nextValue)) : nextValue
                      emitChange(field.key, incoming)
                    }}
                    className="w-full rounded-md border border-white/40 bg-white px-3 py-1.5 text-sm shadow-inner outline-none transition focus:border-transparent focus:ring-2 focus:ring-slate-300"
                  />
                )}
                {field.helperText ? (
                  <p className="text-[0.6rem] text-slate-500">{field.helperText}</p>
                ) : null}
              </div>
            )
          })}
        </div>
      ) : null}

    {(inputs.length > 0 || outputs.length > 0) ? (
  <div
    className={cn(
      "flex items-center justify-between text-[0.65rem] font-semibold uppercase tracking-wide text-slate-700",
      variant === "tall" ? "mt-auto border-t border-white/60 pt-4" : "mt-4",
    )}
  >
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: accent }} />
            Inputs {inputs.length}
          </span>
          <span className="flex items-center gap-1">
            Outputs {outputs.length}
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: accent }} />
          </span>
        </div>
      ) : null}

      {inputs.map((input) => {
        const normalizedInput: ScratchBlockPortConfig = { ...input, side: input.side ?? "left" }
        const styles = buildHandleStyles(normalizedInput, accent)
        const handleStyle: React.CSSProperties = {
          ...styles.handle,
          opacity: 0,
          pointerEvents: "none",
          transition: "opacity 140ms ease",
          width: 1,
          height: 1,
          border: "0",
          backgroundColor: "transparent",
          boxShadow: "none",
        }
        return (
          <Handle
            key={`in-${input.id}`}
            id={input.id}
            type="target"
            position={getHandlePosition(normalizedInput.side)}
            style={handleStyle}
          />
        )
      })}

      {outputs.map((output) => {
        const normalizedOutput: ScratchBlockPortConfig = { ...output, side: output.side ?? "right" }
        const styles = buildHandleStyles(normalizedOutput, accent)
        const handleStyle: React.CSSProperties = {
          ...styles.handle,
          opacity: 0,
          pointerEvents: "none",
          transition: "opacity 140ms ease",
          width: 1,
          height: 1,
          border: "0",
          backgroundColor: "transparent",
          boxShadow: "none",
        }
        return (
          <Handle
            key={`out-${output.id}`}
            id={output.id}
            type="source"
            position={getHandlePosition(normalizedOutput.side)}
            style={handleStyle}
          />
        )
      })}
    </div>
  )
}

export const createScratchBlockNode = (config: CreateScratchBlockNodeArgs): Node<ScratchBlockNodeData> => {
  const id = config.id ?? generateNodeId()
  return {
    id,
    type: "scratchBlock",
    position: config.position,
    data: {
      title: config.title,
      typeLabel: config.typeLabel,
      accentColor: config.accentColor,
      backgroundColor: config.backgroundColor,
      description: config.description,
      fields: config.fields ?? [],
      values: { ...(config.values ?? {}) },
      inputs: config.inputs ?? [],
      outputs: config.outputs ?? [],
      variant: config.variant ?? "default",
      onDataChange: config.onDataChange,
      onDelete: config.onDelete,
    },
  }
}
