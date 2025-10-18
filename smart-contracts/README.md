# AlgoFlow Smart Contracts

This package contains the PyTeal contracts that back the AlgoFlow intent engine. It currently ships two router-based applications:

- **Intent Storage Router** (`smart-contracts/src/algo_flow_contracts/intent_storage/contract.py`)
- **Execution Router** (`smart-contracts/src/algo_flow_contracts/execution/contract.py`)

Both contracts are authored in PyTeal v8, compiled through `pyteal.Router`, and exported via helper functions that keep compatibility with multiple `Router.compile_program` return shapes.

## Intent Storage Router

The storage app tracks user intents, their collateral, and lifecycle transitions. Its ABI surface is:

| Method | Purpose |
| --- | --- |
| `configure(address,uint64,uint64,uint64)void` | Set keeper defaults, minimum collateral, fee split, and the execution app ID. Owner-only. |
| `register_intent(staticBytes[32],byte[],byte[],uint64,address,uint64)uint64` | Persist a new intent record, enforce collateral payment, and emit creation events. |
| `update_intent_status(uint64,uint64,byte[])void` | Transition an intent between lifecycle states. Supports executor delegation when configured. |
| `export_intent(uint64)IntentRecord` | Fetch the ABI-encoded record for off-chain coordination. |
| `read_intent_raw(uint64)byte[]` | Return the raw box contents (used by the execution app). |
| `withdraw_intent(uint64,address)uint64` | Release collateral to owner or designated recipient once the intent has completed or failed. |

### Boxes and encoding

- Each intent is stored in an application box keyed by `layout.intent_box_key(intent_id)`.
- `IntentRecord` is defined in `common/abi_types.py` and is the canonical on-chain layout.
- `WorkflowStep` (decoded by the execution router) is a 7-field ABI tuple `(opcode, target_app_id, asset_in, asset_out, amount, slippage_bps, extra)`.

### Permissions and guards

- Application owner must call `configure`, `update_application`, and `delete_application` (enforced via `validation.ensure_owner`).
- `register_intent` validates workflow size, minimum collateral, and collateral payment grouping.
- `update_intent_status` enforces allowed status transitions and shared authority between owner, keeper, and optional executor.

## Execution Router

The execution app reads intents from storage, verifies hashes, and dispatches the workflow. Key methods:

| Method | Purpose |
| --- | --- |
| `configure(uint64,address,uint64)void` | Point to the storage app, set default keeper, and configure keeper fee split. Owner-only. |
| `execute_intent(uint64,byte[],address)void` | Execute a validated workflow plan, update storage status, and optionally pay a keeper. |

### Workflow dispatch

`execute_intent` decodes the workflow blob into `WorkflowStep` entries and routes each step through `dispatch_workflow_step`. Supported opcodes (see `common/opcodes.py`):

| Opcode | Subroutine | Description |
| --- | --- | --- |
| `SWAP` | `execute_swap` | Invoke target DEX app with amount-after-slippage guard. |
| `PROVIDE_LIQUIDITY` | `execute_provide_liquidity` | Dual-asset provide call with paired amount guard. |
| `WITHDRAW_LIQUIDITY` | `execute_withdraw_liquidity` | Withdraw LP value with slippage bound. |
| `STAKE` | `execute_stake` | Deposit into staking app. |
| `UNSTAKE` | `execute_unstake` | Withdraw from staking app. |
| `TRANSFER` | `execute_transfer` | Send ALGO or ASA to destination. |
| `LEND_SUPPLY` | `execute_lend_supply` | Supply an asset to a lending market. |
| `LEND_WITHDRAW` | `execute_lend_withdraw` | Withdraw supplied asset from lending market. |

Each subroutine builds a zero-fee inner transaction, populates the required fields, and asserts minimal safety conditions (positive amounts, receiver format, slippage bounds, etc.). `maybe_pay_keeper` issues an optional ALGO payment if a non-zero fee is due and a recipient is provided.

### Status management

`execute_intent` interacts with storage via:

1. `read_intent_raw` (inner app call) to fetch and decode the intent record.
2. `call_update_status` (inner app call) to transition statuses in storage, emitting log events through `events.log_intent_status`.

The flow guarantees:

- Hash of provided plan matches the stored `workflow_hash`.
- Status transitions follow `INTENT_STATUS_ACTIVE -> EXECUTING -> SUCCESS` (or failure paths via storage API).
- Keeper fee is derived from collateral using `WideRatio` and global fee split basis points.
- Trigger validation runs before the workflow executes. Trigger payloads encode `(trigger_type, oracle_app_id, oracle_price_key, comparator, threshold)` and currently support:
   - `TRIGGER_TYPE_NONE` – no guard.
   - `TRIGGER_TYPE_PRICE_THRESHOLD` – fetches a value from the specified oracle app (via `App.globalGetEx`) and asserts it satisfies the comparator (`COMPARATOR_GTE` or `COMPARATOR_LTE`) against the stored threshold.

## Compiling the contracts

Both routers expose helper functions for on-demand compilation:

```python
from algo_flow_contracts.execution.contract import approval_program, clear_state_program
from pyteal import compileTeal, Mode, OptimizeOptions

teal = compileTeal(
    approval_program(),
    mode=Mode.Application,
    version=8,
    optimize=OptimizeOptions(scratch_slots=True),
)
```

`approval_program` and `clear_state_program` detect whether `Router.compile_program` returns a tuple or an object with `approval_program` / `clear_state_program` attributes, ensuring compatibility across PyTeal releases.

## Testing

Unit tests live in `smart-contracts/tests/` and can be executed via:

```powershell
Set-Location 'smart-contracts'
python -m pytest tests -q
```

Coverage highlights:

- Opcode map expectations (`test_common.py`).
- ABI encoding round-trips for workflow plans, including reverse operations.
- Execution dispatch tests verifying each subroutine is reachable and emits required TEAL fields.
- Guard tests asserting assertions/slippage checks remain intact.

Run the suite after making contract changes to ensure the generated TEAL and ABI surfaces remain consistent.

## Interacting with the deployed contracts

1. **Storage App**
   - Deploy using the compiled approval/clear TEAL.
   - Call `configure` as the creator, passing keeper address, minimum collateral, fee split (bps), and execution app ID (0 until execution app exists).
   - Users call `register_intent`, grouping the transaction with a collateral payment.
   - Keepers/executors consume `update_intent_status` as workflows progress.

2. **Execution App**
   - Deploy and configure with storage app ID, default keeper, and keeper fee split.
   - For each execution, keepers submit `execute_intent(intent_id, execution_plan, fee_recipient)` where `execution_plan` is the ABI-encoded array of `WorkflowStep` tuples and `fee_recipient` is optional.
   - Group the call with any additional transactions required by downstream protocols (swaps, staking, etc.), ensuring the execution app remains the sender of inner transactions.

3. **Encoding workflow plans**
   - Off-chain services should generate the plan using the ABI stepped tuple `(uint64,uint64,uint64,uint64,uint64,uint64,byte[])[]`.
   - Hash the encoded bytes (SHA-256) and store the digest in the intent record so `execute_intent` can validate integrity.

By following this structure, AlgoFlow separates lifecycle management (storage) from action execution while keeping both routers auditable, modular, and covered by unit tests.

## Calling the contracts from a frontend

The typical flow for a dApp UI is:

```ts
import algosdk from "algosdk";
import { encodeTriggerConfig, encodeWorkflowPlan } from "./workflowEncoder";

const storageAppId = 123456;
const executionAppId = 654321;

async function registerIntent(client: algosdk.Algodv2, sender: algosdk.Account) {
   const params = await client.getTransactionParams().do();

   const workflowSteps = [
      { opcode: OPCODE_SWAP, targetAppId: pactPoolAppId, assetIn: 0, assetOut: usdcId, amount: 100_000_000n, slippageBps: 50n, extra: new Uint8Array() },
      { opcode: OPCODE_PROVIDE_LIQUIDITY, targetAppId: pactPoolAppId, assetIn: algoId, assetOut: usdcId, amount: 100_000_000n, slippageBps: 50n, extra: new Uint8Array() },
   ];

   const encodedPlan = encodeWorkflowPlan(workflowSteps);
   const workflowHash = new Uint8Array(await crypto.subtle.digest("SHA-256", encodedPlan));

   const trigger = encodeTriggerConfig({
      triggerType: TRIGGER_TYPE_PRICE_THRESHOLD,
      oracleAppId: 21321231231,
      oraclePriceKey: new TextEncoder().encode("ALGO/USDC"),
      comparator: COMPARATOR_GTE,
      threshold: 1_500_000n,
   });

   const collateralTxn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
      from: sender.addr,
      to: algosdk.getApplicationAddress(storageAppId),
      amount: 200_000_000, // microAlgos
      suggestedParams: params,
   });

   const registerTxn = algosdk.makeApplicationNoOpTxnFromObject({
      from: sender.addr,
      appIndex: storageAppId,
      appArgs: [
         new Uint8Array(Buffer.from("register_intent", "utf8")),
         workflowHash,
         encodedPlan,
         trigger,
         algosdk.encodeUint64(200_000_000),
         algosdk.decodeAddress(keeperAddr).publicKey,
         algosdk.encodeUint64(1),
      ],
      suggestedParams: params,
   });

   const group = algosdk.assignGroupID([collateralTxn, registerTxn]);
   const signed = group.map((txn) => txn.signTxn(sender.sk));
   await client.sendRawTransaction(signed).do();
}
```

Frontend helper modules should mirror the ABI layout from `common/abi_types.py` so encoding remains consistent with the on-chain expectations.

### Workflow step snippets by opcode

```ts
const swapStep = {
   opcode: OPCODE_SWAP,
   targetAppId: pactPoolAppId,
   assetIn: algoId,
   assetOut: usdcId,
   amount: 100_000_000n,
   slippageBps: 50n,
   extra: new Uint8Array(),
};

const provideLiquidityStep = {
   opcode: OPCODE_PROVIDE_LIQUIDITY,
   targetAppId: pactPoolAppId,
   assetIn: algoId,
   assetOut: usdcId,
   amount: 200_000_000n,
   slippageBps: 50n,
   extra: new Uint8Array(),
};

const withdrawLiquidityStep = {
   opcode: OPCODE_WITHDRAW_LIQUIDITY,
   targetAppId: pactPoolAppId,
   assetIn: algoId,
   assetOut: usdcId,
   amount: 10_000_000n, // LP tokens to burn
   slippageBps: 75n,
   extra: new Uint8Array(),
};

const stakeStep = {
   opcode: OPCODE_STAKE,
   targetAppId: stakingAppId,
   assetIn: gAlgoId,
   assetOut: 0n,
   amount: 500_000_000n,
   slippageBps: 0n,
   extra: new Uint8Array(),
};

const unstakeStep = {
   opcode: OPCODE_UNSTAKE,
   targetAppId: stakingAppId,
   assetIn: gAlgoId,
   assetOut: 0n,
   amount: 500_000_000n,
   slippageBps: 0n,
   extra: new Uint8Array(),
};

const transferAlgoStep = {
   opcode: OPCODE_TRANSFER,
   targetAppId: 0n,
   assetIn: 0n,
   assetOut: 0n,
   amount: 5_000_000n,
   slippageBps: 0n,
   extra: algosdk.decodeAddress(destinationAddr).publicKey,
};

const lendSupplyStep = {
   opcode: OPCODE_LEND_SUPPLY,
   targetAppId: folksFinanceAppId,
   assetIn: usdcId,
   assetOut: 0n,
   amount: 300_000_000n,
   slippageBps: 0n,
   extra: new Uint8Array(),
};

const lendWithdrawStep = {
   opcode: OPCODE_LEND_WITHDRAW,
   targetAppId: folksFinanceAppId,
   assetIn: 0n,
   assetOut: usdcId,
   amount: 150_000_000n,
   slippageBps: 0n,
   extra: new Uint8Array(),
};
```

When composing a workflow, choose the steps that match the user action, tweak the numeric values, and pass the resulting array into `encodeWorkflowPlan`. Leave `extra` as `new Uint8Array()` unless the downstream protocol needs additional arguments (e.g., pool-specific hints, encoded recipients, or serialized structs).

## Keeper server execution loop

A keeper typically scans the storage app for intents with status `ACTIVE`, evaluates the trigger off-chain, and if satisfied composes the execution plan and calls the execution app:

```python
import base64
import json
from algosdk import account, transaction
from algosdk.v2client import algod

ALGOD = algod.AlgodClient(token, url)
EXECUTION_APP_ID = 654321
STORAGE_APP_ID = 123456

def fetch_active_intents():
      boxes = ALGOD.application_boxes(STORAGE_APP_ID)
      for box in boxes.get("boxes", []):
            key = base64.b64decode(box["name"])
            value = ALGOD.application_box_by_name(STORAGE_APP_ID, key)["value"]
            record = decode_intent_record(value)
            if record.status == INTENT_STATUS_ACTIVE:
                  yield key, record

def run_keeper_loop(keeper_sk):
      keeper_addr = account.address_from_private_key(keeper_sk)
      for intent_key, record in fetch_active_intents():
            trigger = decode_trigger_config(record.trigger_condition)
            if not evaluate_trigger(trigger):
                  continue

            plan = build_execution_plan(record)  # returns ABI-encoded workflow
            params = ALGOD.suggested_params()

            call = transaction.ApplicationNoOpTxn(
                  sender=keeper_addr,
                  index=EXECUTION_APP_ID,
                  app_args=[
                        b"execute_intent",
                        intent_key,
                        plan,
                        record.keeper.encode(),
                  ],
                  suggested_params=params,
            )

            signed = call.sign(keeper_sk)
            ALGOD.send_transaction(signed)

```

Key responsibilities of the keeper:

- Decode the `IntentRecord` (including trigger configuration) using the same ABI helpers as the frontend.
- Validate triggers off-chain if they require complex logic beyond the on-chain guard.
- Provide the ABI-encoded workflow bytes that hash to the value stored in the intent.
- Supply any auxiliary transactions required for the target protocols in the same group as the execution call.
