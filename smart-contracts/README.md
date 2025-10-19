## AlgoFlow Smart Contracts
- PyTeal sources that back the intent lifecycle for AlgoFlow.
- Two router applications: intent storage and execution.
- Shared ABI structures and validation utilities live in `src/algo_flow_contracts/common`.

### 📁 Layout
- `src/algo_flow_contracts/intent_storage`: register, update, and withdraw intents.
- `src/algo_flow_contracts/execution`: execute approved workflow plans.
- `tests/`: pytest suite with TEAL compilation assertions.
- `build/`: generated `.teal` artifacts (not committed automatically).

### Intent Storage Router
- Manages the authoritative `IntentRecord` boxes and collateral.
- Key methods:
   - `configure(address,uint64,uint64,uint64)void`: owner sets keeper defaults, minimum collateral, fee split, execution app id.
   - `register_intent(...)uint64`: validates collateral payment, stores the encoded workflow hash/blob, returns new intent id.
   - `update_intent_status(uint64,uint64,byte[])void`: enforces allowed lifecycle transitions and emits status events.
   - `read_intent_raw(uint64)byte[]`: raw box loader used by the execution router via inner transactions.
   - `withdraw_intent(uint64,address)uint64`: releases collateral on completion/failure.
- `IntentRecord` (see `common/abi_types.py`) captures owner, keeper, workflow hash/blob, trigger config, escrow ids, ASA id, and collateral.

### Execution Router
- Reads intent boxes, validates hash + trigger guard, and dispatches workflow steps.
- Methods:
   - `configure(uint64,address,uint64)void`: owner sets storage app id, default keeper, fee split bps.
   - `execute_intent(uint64,byte[],address)void`: decodes workflow plan, executes each step, updates storage status, pays optional keeper.
- Supported workflow opcodes (defined in `common/opcodes.py`):
   - `SWAP` → `swap_step`: inner app call into AMM, amount-after-slippage guard.
   - `PROVIDE_LIQUIDITY` → `provide_liquidity_step`: dual-asset provide, paired minimum enforced.
   - `TRANSFER` → `transfer_step`: ALGO/ASA transfer with balance delta tracking.
- Safety checks include plan hash verification, trigger validation (`TRIGGER_TYPE_NONE` or `PRICE_THRESHOLD`), opt-in of required assets, and zero-fee inner transactions created with `InnerTxnBuilder`.

### Workflow Data Model
- `WorkflowStep` ABI tuple: `(opcode, target_app_id, asset_in, asset_out, amount, slippage_bps, extra)`.
- `extra` is a 32-byte prefix interpreted as a pool/account address (`extract_pool_address` enforces length).
- Execution loop walks the dynamic array of `WorkflowStep` values decoded from the blob supplied to `execute_intent`.

### Workflow Chaining
- Real AMMs make it impossible to pre-compute exact downstream amounts; pool ratios shift between steps.
- Convention: when a `WorkflowStep.amount` is `0`, the router calls `get_balance(asset_in)` and spends the entire balance the contract currently holds for that asset.
- This allows chaining results (e.g. swap USDC→ALGO, then with `amount=0` immediately swap **all** received ALGO into USDT, then `amount=0` transfer the full USDT balance).
- Provide an explicit amount whenever you need a fixed quantity; mix explicit and dynamic steps to split flows.
- Future improvements (percentage-based splits, register references) can be layered on top without changing the current plan schema.

### Building TEAL Artifacts
```python
from pathlib import Path
import sys
from pyteal import Mode, OptimizeOptions, compileTeal
from algo_flow_contracts.execution.contract import approval_program, clear_state_program

root = Path.cwd()
sys.path.append(str(root / "smart-contracts" / "src"))
opts = OptimizeOptions(scratch_slots=True)

approval = compileTeal(approval_program(), mode=Mode.Application, version=8, assembleConstants=True, optimize=opts)
clear = compileTeal(clear_state_program(), mode=Mode.Application, version=8, assembleConstants=True, optimize=opts)

(root / "smart-contracts" / "build" / "execution_approval_v8.teal").write_text(approval)
(root / "smart-contracts" / "build" / "execution_clear_v8.teal").write_text(clear)
```
- After generating TEAL, run an assembler (`goal clerk compile` or `algokit teal compile`) to confirm the approval program stays within Algorand’s 1,024-byte limit.

### Testing
- Run the suite from repo root:
   ```powershell
   python -m pytest smart-contracts/tests -q
   ```
- Highlights:
   - ABI shape checks for `IntentRecord` and `WorkflowStep`.
   - Dispatch tests ensuring all supported opcodes compile into the approval program.
   - Trigger validation and helper subroutine coverage (`amount_after_slippage`, `extract_pool_address`, `maybe_pay_keeper`).

### Deployment Checklist
- Compile both routers to TEAL and assemble to bytecode; record app program hashes.
- Deploy intent storage, call `configure`, and fund collateral escrow if required.
- Deploy execution router, call `configure` with storage app id, keeper address, and fee split (keeper rewards handled off-chain for now).
- Verify inner app IDs and box layout using AlgoExplorer or `goal app read`.
- Keep the generated TEAL and bytecode under version control (or artifact storage) for auditability.

#### `deploy_app.py`
- Environment setup:
   - `ALGOD_ADDRESS` – algod REST endpoint (`https://testnet-api.algonode.cloud` for public testnet).
   - `ALGOD_TOKEN` – API token if required (empty for Algonode).
   - `ALGOD_HEADER_NAME` / `ALGOD_HEADER_VALUE` – optional custom header pair (e.g. PureStake `X-API-Key`).
   - `ALGOD_ACCOUNT_MNEMONIC` – 25-word mnemonic for the deployer account (fund it via the faucet when targeting TestNet).
- Deploy both contracts: `python smart-contracts\deploy_app.py`
- Deploy a single contract: `python smart-contracts\deploy_app.py --contract execution`
- Flags: `--version` (TEAL version, default 8), `--no-assemble` (skip constant folding), `--extra-pages` (allocate additional program pages if ever needed).

### Tooling Tips
- Use AlgoKit or Algorand Sandbox for fast compile/deploy/test cycles.
- `pyteal.Router` helpers (`approval_program`, `clear_state_program`) smooth over PyTeal return shape differences between releases.
- Keep `requirements.txt` in sync (`pip freeze > requirements.txt`) when bumping PyTeal or testing dependencies.
