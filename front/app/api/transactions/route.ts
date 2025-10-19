import { NextRequest, NextResponse } from "next/server"
import algosdk, { ABIMethod, ABIType } from "algosdk"
import type { ABIValue } from "algosdk"
import { createHash } from "crypto"

const ALGOD_URL = "https://testnet-api.algonode.cloud"
const ALGOD_TOKEN = process.env.ALGOD_TOKEN ?? process.env.NEXT_PUBLIC_ALGOD_TOKEN ?? ""
const ALGOD_PORT = process.env.ALGOD_PORT ?? process.env.NEXT_PUBLIC_ALGOD_PORT ?? ""

const INTENT_STORAGE_APP_ID = parseEnvInt(
	process.env.INTENT_STORAGE_APP_ID ?? process.env.NEXT_PUBLIC_INTENT_STORAGE_APP_ID,
	748015612
)
const EXECUTION_APP_ID = parseEnvInt(
	process.env.EXECUTION_APP_ID ?? process.env.NEXT_PUBLIC_EXECUTION_APP_ID,
	748015611
)

const REGISTER_SIGNATURE = "register_intent(byte[32],byte[],byte[],uint64,address,uint64,uint64,uint64)uint64"
const EXECUTE_SIGNATURE = "execute_intent(uint64,byte[],address)void"

const STEP_TYPE = ABIType.from("(uint64,uint64,uint64,uint64,uint64,uint64,byte[])[]")
const REGISTER_METHOD = ABIMethod.fromSignature(REGISTER_SIGNATURE)
const EXECUTE_METHOD = ABIMethod.fromSignature(EXECUTE_SIGNATURE)
const ZERO_ADDRESS = algosdk.ALGORAND_ZERO_ADDRESS_STRING
const ZERO_BIGINT = BigInt(0)

interface WorkflowStep {
	opcode: number
	target_app_id: number
	asset_in?: number
	asset_out?: number
	amount?: number
	slippage_bps?: number
	extra_b64?: string
	extra?: string
	notes?: string
	[key: string]: unknown
}

interface WorkflowConfig {
	description?: string
	collateral_microalgo?: number
	keeper_override?: string
	workflow_version?: number
	app_escrow_id: number
	app_asa_id?: number
	trigger_condition_b64?: string
	steps: WorkflowStep[]
	[key: string]: unknown
}

interface WorkflowShape {
	[key: string]: WorkflowConfig
}

const encodeMethodCall = (method: ABIMethod, values: ABIValue[]) => {
	if (values.length !== method.args.length) {
		throw new Error(`Expected ${method.args.length} arguments for ${method.getSignature()}, received ${values.length}`)
	}
	const selector = method.getSelector()
	const encoded = method.args.map((arg, index) => {
		const type = arg.type as ABIType
		return type.encode(values[index])
	})
	return [selector, ...encoded]
}

const toBigInt = (value: unknown): bigint => {
	if (typeof value === "bigint") {
		return value >= ZERO_BIGINT ? value : ZERO_BIGINT
	}
	if (typeof value === "number") {
		if (!Number.isFinite(value) || value < 0) {
			return ZERO_BIGINT
		}
		return BigInt(Math.floor(value))
	}
	if (typeof value === "string" && value.trim().length > 0) {
		const parsed = Number(value)
		if (Number.isFinite(parsed) && parsed >= 0) {
			return BigInt(Math.floor(parsed))
		}
	}
	return ZERO_BIGINT
}

const resolveExtraBase64 = (step: WorkflowStep) => {
	if (typeof step.extra_b64 === "string" && step.extra_b64.trim().length > 0) {
		return step.extra_b64.trim()
	}
	if (typeof step.extra === "string" && step.extra.trim().length > 0) {
		return step.extra.trim()
	}
	return ""
}

const decodeExtraBytes = (value: string) => {
	const raw = value.trim()
	if (!raw) {
		throw new Error("Workflow step is missing Tinyman escrow metadata (extra_b64)")
	}
	const bytes = Buffer.from(raw, "base64")
	if (bytes.length < 32) {
		throw new Error("Workflow step extra_b64 must decode to at least 32 bytes")
	}
	return new Uint8Array(bytes)
}

const encodeWorkflowSteps = (steps: WorkflowStep[]) => {
	const tuples = steps.map((step) => [
		toBigInt(step.opcode),
		toBigInt(step.target_app_id),
		toBigInt(step.asset_in ?? 0),
		toBigInt(step.asset_out ?? 0),
		toBigInt(step.amount ?? 0),
		toBigInt(step.slippage_bps ?? 0),
		decodeExtraBytes(resolveExtraBase64(step)),
	])
	return STEP_TYPE.encode(tuples)
}

const decodeTrigger = (value: unknown) => {
	if (typeof value !== "string" || value.trim().length === 0) {
		return new Uint8Array()
	}
	try {
		return new Uint8Array(Buffer.from(value.trim(), "base64"))
	} catch (error) {
		throw new Error("Trigger condition must be base64 encoded")
	}
}

const collectForeignAssets = (config: WorkflowConfig) => {
	const assets = new Set<number>()
	config.steps.forEach((step) => {
		const maybeAdd = (candidate: unknown) => {
			const value = typeof candidate === "bigint" ? Number(candidate) : Number(candidate)
			if (Number.isFinite(value) && value > 0) {
				assets.add(value)
			}
		}
		maybeAdd(step.asset_in)
		maybeAdd(step.asset_out)
	})
	if (config.app_asa_id) {
		const asaId = Number(config.app_asa_id)
		if (Number.isFinite(asaId) && asaId > 0) {
			assets.add(asaId)
		}
	}
	return Array.from(assets)
}

const collectForeignApps = (config: WorkflowConfig) => {
	const apps = new Set<number>()
	config.steps.forEach((step) => {
		const appId = Number(step.target_app_id)
		if (Number.isFinite(appId) && appId > 0 && appId !== EXECUTION_APP_ID) {
			apps.add(appId)
		}
	})
	if (Number.isFinite(config.app_escrow_id) && config.app_escrow_id > 0 && config.app_escrow_id !== EXECUTION_APP_ID) {
		apps.add(Number(config.app_escrow_id))
	}
	apps.add(INTENT_STORAGE_APP_ID)
	return Array.from(apps)
}

const buildIntentBoxName = (intentId: bigint) => {
	const prefix = Buffer.from("intent:")
	const idBytes = Buffer.from(algosdk.encodeUint64(intentId))
	return new Uint8Array(Buffer.concat([prefix, idBytes]))
}

const normalizeAddress = (value: unknown, label: string): string => {
	if (typeof value === "string") {
		const trimmed = value.trim()
		if (!trimmed) {
			throw new Error(`${label} must be a valid Algorand address`)
		}
		try {
			algosdk.decodeAddress(trimmed)
			return trimmed
		} catch {
			throw new Error(`${label} must be a valid Algorand address`)
		}
	}
	if (value && typeof value === "object") {
		const record = value as Record<string, unknown>
		if (typeof record.addr === "string") {
			return normalizeAddress(record.addr, label)
		}
		if (record.publicKey instanceof Uint8Array) {
			return algosdk.encodeAddress(record.publicKey)
		}
		if (Array.isArray(record.publicKey)) {
			return algosdk.encodeAddress(new Uint8Array(record.publicKey))
		}
		if (typeof (record as { toString?: () => string }).toString === "function") {
			const rendered = String((record as { toString: () => string }).toString()).trim()
			if (rendered && rendered !== "[object Object]") {
				return normalizeAddress(rendered, label)
			}
		}
	}
	throw new Error(`${label} must be a valid Algorand address`)
}

const fetchNextIntentId = async (client: algosdk.Algodv2) => {
	const app = await client.getApplicationByID(INTENT_STORAGE_APP_ID).do()
	const paramsRecord = (app.params as unknown as Record<string, unknown>) ?? {}
	const globalState = (paramsRecord["global-state"] ?? []) as Array<{
		key: string
		value: { type: number; bytes?: string; uint?: number }
	}>
	const entry = globalState.find((item) => Buffer.from(item.key, "base64").toString("utf8") === "g_next_intent")
	if (!entry || typeof entry.value?.uint !== "number") {
		return 0
	}
	return entry.value.uint
}

function parseEnvInt(value: string | undefined, fallback: number) {
	if (!value) return fallback
	const parsed = Number(value)
	return Number.isFinite(parsed) ? parsed : fallback
}

export async function POST(request: NextRequest) {
	try {
		if (!ALGOD_URL) {
			return NextResponse.json({ error: "ALGOD_URL is not configured on the server" }, { status: 500 })
		}

		const body = (await request.json()) as { workflow?: WorkflowShape; account?: string }
		const workflow = body.workflow
		const account = body.account

		if (!workflow || typeof workflow !== "object") {
			return NextResponse.json({ error: "workflow is required" }, { status: 400 })
		}
		if (!account || typeof account !== "string") {
			return NextResponse.json({ error: "account is required" }, { status: 400 })
		}

		const entries = Object.entries(workflow)
		if (entries.length === 0) {
			return NextResponse.json({ error: "workflow must include at least one job" }, { status: 400 })
		}

		const [slug, config] = entries[0]
		if (!config || !Array.isArray(config.steps) || config.steps.length === 0) {
			return NextResponse.json({ error: "workflow contains no steps" }, { status: 400 })
		}

		if (!Number.isFinite(config.app_escrow_id) || config.app_escrow_id <= 0) {
			return NextResponse.json({ error: "workflow is missing app_escrow_id" }, { status: 400 })
		}

		const client = new algosdk.Algodv2(ALGOD_TOKEN, ALGOD_URL, ALGOD_PORT)
		const intentIdValue = await fetchNextIntentId(client)
		const intentId = BigInt(intentIdValue)

		const workflowBlob = encodeWorkflowSteps(config.steps)
		if (workflowBlob.length === 0) {
			return NextResponse.json({ error: "workflow steps produced an empty plan" }, { status: 400 })
		}

		const workflowHash = createHash("sha256").update(workflowBlob).digest()
		const triggerBytes = decodeTrigger(config.trigger_condition_b64)
		const collateral = toBigInt(config.collateral_microalgo)
		const senderAddress = normalizeAddress(account, "account")
		const keeperOverride = typeof config.keeper_override === "string" ? config.keeper_override.trim() : ""
		const keeperAddress = keeperOverride ? normalizeAddress(keeperOverride, "keeper_override") : ZERO_ADDRESS
		const workflowVersion = toBigInt(config.workflow_version ?? 1)
		const appEscrowId = toBigInt(config.app_escrow_id)
		const appAsaId = toBigInt(config.app_asa_id ?? 0)
		const feeRecipient = keeperAddress === ZERO_ADDRESS ? senderAddress : keeperAddress
		const storageAppAddress = normalizeAddress(
			algosdk.getApplicationAddress(INTENT_STORAGE_APP_ID).toString(),
			"intent storage address"
		)

		const suggestedParams = await client.getTransactionParams().do()
		const normalizedFee = Math.max(Number(suggestedParams.fee) || 0, Number(suggestedParams.minFee) || 0, 1000)
		suggestedParams.flatFee = true
		suggestedParams.fee = BigInt(normalizedFee)
		suggestedParams.minFee = BigInt(normalizedFee)

		const boxName = buildIntentBoxName(intentId)
		const workflowHashBytes = new Uint8Array(workflowHash)
		const workflowPlanBytes = new Uint8Array(workflowBlob)
		const registerArgs = encodeMethodCall(REGISTER_METHOD, [
			workflowHashBytes,
			workflowPlanBytes,
			triggerBytes,
			collateral,
			keeperAddress,
			workflowVersion,
			appEscrowId,
			appAsaId,
		])

		const txns: algosdk.Transaction[] = []

		if (collateral > ZERO_BIGINT) {
			txns.push(
				algosdk.makePaymentTxnWithSuggestedParamsFromObject({
					sender: senderAddress,
					receiver: storageAppAddress,
					amount: Number(collateral),
					suggestedParams,
				})
			)
		}

		txns.push(
			algosdk.makeApplicationCallTxnFromObject({
				sender: senderAddress,
				appIndex: INTENT_STORAGE_APP_ID,
				onComplete: algosdk.OnApplicationComplete.NoOpOC,
				suggestedParams,
				appArgs: registerArgs,
				boxes: [{ appIndex: INTENT_STORAGE_APP_ID, name: boxName }],
				foreignApps: [EXECUTION_APP_ID],
			})
		)

		const executeArgs = encodeMethodCall(EXECUTE_METHOD, [intentId, workflowPlanBytes, feeRecipient])
		const foreignApps = collectForeignApps(config)
		const foreignAssets = collectForeignAssets(config)

		txns.push(
			algosdk.makeApplicationCallTxnFromObject({
				sender: senderAddress,
				appIndex: EXECUTION_APP_ID,
				onComplete: algosdk.OnApplicationComplete.NoOpOC,
				suggestedParams,
				appArgs: executeArgs,
				boxes: [{ appIndex: INTENT_STORAGE_APP_ID, name: boxName }],
				foreignApps,
				foreignAssets,
			})
		)

		algosdk.assignGroupID(txns)
		const encoded = txns.map((txn) => Buffer.from(algosdk.encodeUnsignedTransaction(txn)).toString("base64"))

		return NextResponse.json({
			slug,
			intentId: intentIdValue,
			workflowHash: Buffer.from(workflowHash).toString("base64"),
			transactions: encoded,
		})
	} catch (error: any) {
		console.error("/api/transactions error", error)
		return NextResponse.json(
			{
				error: "Failed to build transactions",
				details: error?.message ?? String(error),
			},
			{ status: 500 }
		)
	}
}
