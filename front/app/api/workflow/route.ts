import { NextRequest, NextResponse } from "next/server"
import path from "path"
import fs from "fs/promises"
import { buildTinymanWorkflow } from "@/lib/tinyman-workflow-builder"

const DEFAULT_REGISTRY = path.join(process.cwd(), "..", "backend", "sample_registry.json")

export async function POST(request: NextRequest) {
	try {
		const body = await request.json()
		const { diagramJson, registryJson, options: optionsInput } = body ?? {}

		if (!diagramJson || typeof diagramJson !== "object") {
			return NextResponse.json({ error: "diagramJson is required" }, { status: 400 })
		}

		let registryData: any
		if (registryJson && typeof registryJson === "object") {
			registryData = registryJson
		} else {
			try {
				const raw = await fs.readFile(DEFAULT_REGISTRY, "utf8")
				registryData = JSON.parse(raw)
			} catch (error) {
				return NextResponse.json({ error: "Registry file missing", details: String(error) }, { status: 500 })
			}
		}

		const parseNumeric = (value: unknown): number | undefined => {
			if (typeof value === "number" && Number.isFinite(value)) {
				return value
			}
			if (typeof value === "string") {
				const trimmed = value.trim()
				if (!trimmed) return undefined
				const parsed = Number(trimmed)
				return Number.isFinite(parsed) ? parsed : undefined
			}
			return undefined
		}

		const options = typeof optionsInput === "object" && optionsInput
			? {
				jobName: typeof optionsInput.jobName === "string" ? optionsInput.jobName : undefined,
				description: typeof optionsInput.description === "string" ? optionsInput.description : undefined,
				collateralMicroalgo: parseNumeric(optionsInput.collateralMicroalgo),
				workflowVersion: parseNumeric(optionsInput.workflowVersion),
				keeperOverride:
					typeof optionsInput.keeperOverride === "string" ? optionsInput.keeperOverride.trim() : undefined,
			}
			: {}

		const workflowPayload = buildTinymanWorkflow(diagramJson, registryData, options)

		return NextResponse.json({ workflow: workflowPayload })
	} catch (error: any) {
		console.error("Workflow API error", error)
		return NextResponse.json(
			{
				error: "Failed to build workflow",
				details: error?.message ?? String(error),
			},
			{ status: 500 }
		)
	}
}
