import { NextRequest, NextResponse } from "next/server"
import { exec } from "child_process"
import { promisify } from "util"
import path from "path"
import fs from "fs/promises"

const execAsync = promisify(exec)

export async function POST(request: NextRequest) {
	try {
		const body = await request.json()
		const { userInput, diagramJson, registryJson } = body

		if (!userInput || typeof userInput !== "string") {
			return NextResponse.json({ error: "userInput is required and must be a string" }, { status: 400 })
		}

		console.log(`[Agent API] Processing request: "${userInput.substring(0, 50)}..."`)

		// Path to the agent.py script
		const projectRoot = path.join(process.cwd(), "..")
		const agentPath = path.join(projectRoot, "ai_agent", "agent.py")
		const registryPath = path.join(projectRoot, "ai_agent", "coin_registry.json")

		// Create a temporary file with the input data
		const tempDir = path.join(projectRoot, "temp")
		await fs.mkdir(tempDir, { recursive: true })

		const inputFile = path.join(tempDir, `input-${Date.now()}.json`)
		const outputFile = path.join(tempDir, `output-${Date.now()}.json`)

		const inputData = {
			instruction: userInput,
			current_diagram: diagramJson || null,
			registry_json: registryJson || null,
		}

		await fs.writeFile(inputFile, JSON.stringify(inputData, null, 2))

		// Read registry if not provided
		let registry = registryJson
		if (!registry) {
			try {
				const registryContent = await fs.readFile(registryPath, "utf-8")
				registry = JSON.parse(registryContent)
			} catch (error) {
				console.warn("Could not load registry:", error)
			}
		}

		// Execute Python script
		const pythonCommand = `python "${agentPath}" --input "${inputFile}" --output "${outputFile}"`

		try {
			// For now, we'll call the Python function directly via a wrapper script
			// Create a temporary Python script that calls the agent
			const wrapperScript = path.join(tempDir, `wrapper-${Date.now()}.py`)
			const wrapperContent = `
import sys
import json
sys.path.insert(0, r"${projectRoot.replace(/\\/g, "\\\\")}")

from ai_agent.agent import process_strategy

# Read input
with open(r"${inputFile.replace(/\\/g, "\\\\")}", "r") as f:
    data = json.load(f)

# Process
result = process_strategy(
    user_input=data["instruction"],
    registry_json=data.get("registry_json"),
    diagram_json=data.get("current_diagram"),
    model="gpt-4o-mini"
)

# Write output
with open(r"${outputFile.replace(/\\/g, "\\\\")}", "w") as f:
    json.dump(result, f, indent=2)

print("SUCCESS")
`

			await fs.writeFile(wrapperScript, wrapperContent)

			const { stdout, stderr } = await execAsync(`python "${wrapperScript}"`, {
				cwd: projectRoot,
				timeout: 60000, // 60 second timeout
			})

			console.log("[Agent API] Python stdout:", stdout)
			
			if (stderr && !stderr.includes("DeprecationWarning")) {
				console.warn("[Agent API] Python stderr:", stderr)
			}

			// Read the output file
			const outputContent = await fs.readFile(outputFile, "utf-8")
			const result = JSON.parse(outputContent)

			console.log("[Agent API] Success! Generated strategy:", result.diagram_json ? "Yes" : "No")

			// Clean up temp files
			try {
				await fs.unlink(inputFile)
				await fs.unlink(outputFile)
				await fs.unlink(wrapperScript)
			} catch (cleanupError) {
				console.warn("[Agent API] Cleanup error:", cleanupError)
			}

			return NextResponse.json(result)
		} catch (execError: any) {
			console.error("Execution error:", execError)

			// Clean up temp files even on error
			try {
				await fs.unlink(inputFile).catch(() => {})
				await fs.unlink(outputFile).catch(() => {})
			} catch {}

			return NextResponse.json(
				{
					error: "Failed to execute agent",
					details: execError.message,
					stderr: execError.stderr,
				},
				{ status: 500 }
			)
		}
	} catch (error: any) {
		console.error("Agent API error:", error)
		return NextResponse.json(
			{
				error: "Internal server error",
				details: error.message,
			},
			{ status: 500 }
		)
	}
}
