const fs = require("fs")
const path = require("path")
const algosdk = require("../front/node_modules/algosdk")

const workflow = JSON.parse(fs.readFileSync(path.join(__dirname, "test-workflow.json"), "utf8"))
const account = algosdk.generateAccount().addr.toString()

const ALGOD_URL = "https://testnet-api.algonode.cloud"
const client = new algosdk.Algodv2("", ALGOD_URL, "")

const INTENT_STORAGE_APP_ID = 748015612
const EXECUTION_APP_ID = 748015611

const REGISTER_SIGNATURE = "register_intent(byte[32],byte[],byte[],uint64,address,uint64,uint64,uint64)uint64"
const EXECUTE_SIGNATURE = "execute_intent(uint64,byte[],address)void"

const STEP_TYPE = algosdk.ABIType.from("(uint64,uint64,uint64,uint64,uint64,uint64,byte[])[]")
const REGISTER_METHOD = algosdk.ABIMethod.fromSignature(REGISTER_SIGNATURE)
const EXECUTE_METHOD = algosdk.ABIMethod.fromSignature(EXECUTE_SIGNATURE)
const ZERO_ADDRESS = algosdk.ALGORAND_ZERO_ADDRESS_STRING
const ZERO_BIGINT = BigInt(0)

const toBigInt = (value) => {
  if (typeof value === "bigint") return value >= ZERO_BIGINT ? value : ZERO_BIGINT
  if (typeof value === "number") return Number.isFinite(value) && value >= 0 ? BigInt(Math.floor(value)) : ZERO_BIGINT
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value)
    if (Number.isFinite(parsed) && parsed >= 0) return BigInt(Math.floor(parsed))
  }
  return ZERO_BIGINT
}

const encodeWorkflowSteps = (steps) => {
  const tuples = steps.map((step) => {
    const extra = step.extra_b64 ?? step.extra
    const bytes = Buffer.from(extra, "base64")
    return [
      toBigInt(step.opcode),
      toBigInt(step.target_app_id),
      toBigInt(step.asset_in ?? 0),
      toBigInt(step.asset_out ?? 0),
      toBigInt(step.amount ?? 0),
      toBigInt(step.slippage_bps ?? 0),
      new Uint8Array(bytes),
    ]
  })
  return STEP_TYPE.encode(tuples)
}

async function run() {
  const [slug, config] = Object.entries(workflow)[0]
  const workflowBlob = encodeWorkflowSteps(config.steps)
  const workflowHash = require("crypto").createHash("sha256").update(workflowBlob).digest()
  const triggerBytes = new Uint8Array()
  const collateral = toBigInt(config.collateral_microalgo)
  const keeperAddress = (config.keeper_override ?? "").trim() || ZERO_ADDRESS
  const workflowVersion = toBigInt(config.workflow_version ?? 1)
  const appEscrowId = toBigInt(config.app_escrow_id)
  const appAsaId = toBigInt(config.app_asa_id ?? 0)
  const feeRecipient = keeperAddress === ZERO_ADDRESS ? account : keeperAddress

  const suggestedParams = await client.getTransactionParams().do()
  suggestedParams.flatFee = true
  suggestedParams.fee = BigInt(1000)

  const intentId = BigInt(123)
  const boxName = new Uint8Array(Buffer.concat([Buffer.from("intent:"), Buffer.from(algosdk.encodeUint64(intentId))]))
  const registerArgs = [
    REGISTER_METHOD.getSelector(),
    ...REGISTER_METHOD.args.map((arg, index) => {
      const encode = arg.type.encode.bind(arg.type)
      const values = [
        new Uint8Array(workflowHash),
        new Uint8Array(workflowBlob),
        triggerBytes,
        collateral,
        keeperAddress,
        workflowVersion,
        appEscrowId,
        appAsaId,
      ]
      return encode(values[index])
    }),
  ]

  console.log("registerArgs length", registerArgs.length)

  const txns = []
  if (collateral > ZERO_BIGINT) {
      console.log('account', account)
      console.log('to', algosdk.getApplicationAddress(INTENT_STORAGE_APP_ID).toString())
    txns.push(
      algosdk.makePaymentTxnWithSuggestedParamsFromObject({
        sender: account,
        receiver: algosdk.getApplicationAddress(INTENT_STORAGE_APP_ID).toString(),
        amount: Number(collateral),
        suggestedParams,
      })
    )
  }

  txns.push(
    algosdk.makeApplicationCallTxnFromObject({
      sender: account,
      appIndex: INTENT_STORAGE_APP_ID,
      onComplete: algosdk.OnApplicationComplete.NoOpOC,
      suggestedParams,
      appArgs: registerArgs,
      boxes: [{ appIndex: INTENT_STORAGE_APP_ID, name: boxName }],
      foreignApps: [EXECUTION_APP_ID],
    })
  )

  const executeArgs = [
    EXECUTE_METHOD.getSelector(),
    ...EXECUTE_METHOD.args.map((arg, index) => {
      const encode = arg.type.encode.bind(arg.type)
      const values = [intentId, new Uint8Array(workflowBlob), feeRecipient]
      return encode(values[index])
    }),
  ]

  txns.push(
    algosdk.makeApplicationCallTxnFromObject({
      sender: account,
      appIndex: EXECUTION_APP_ID,
      onComplete: algosdk.OnApplicationComplete.NoOpOC,
      suggestedParams,
      appArgs: executeArgs,
      boxes: [{ appIndex: INTENT_STORAGE_APP_ID, name: boxName }],
      foreignApps: [EXECUTION_APP_ID],
    })
  )

  console.log("built register call")
}

run().catch((err) => {
  console.error(err)
  process.exit(1)
})
