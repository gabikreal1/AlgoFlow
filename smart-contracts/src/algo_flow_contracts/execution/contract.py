"""Execution router contract for AlgoFlow intents."""

from pyteal import (
    And,
    App,
    Approve,
    Assert,
    BareCallActions,
    Bytes,
    Cond,
    Expr,
    For,
    Global,
    If,
    Int,
    Itob,
    Len,
    MethodSignature,
    OnCompleteAction,
    Or,
    Reject,
    Router,
    ScratchVar,
    Seq,
    Sha256,
    Subroutine,
    Substring,
    TealType,
    Txn,
    TxnField,
    WideRatio,
    abi,
    InnerTxnBuilder,
    InnerTxn,
)

from ..common import abi_types, abi_utils, constants, events, opcodes, triggers
from ..common.abi_types import WorkflowStep
from ..common.expressions import (
    g_fee_split_bps_key,
    g_keeper_key,
    g_owner_key,
    g_storage_app_key,
    g_version_key,
)


TEAL_VERSION = 8
from ..common.validation import ensure_fee_bounds, ensure_owner

ABI_RETURN_PREFIX = Bytes("base16", "151f7c75")
READ_INTENT_RAW_SELECTOR = MethodSignature("read_intent_raw(uint64)byte[]")
UPDATE_STATUS_SELECTOR = MethodSignature("update_intent_status(uint64,uint64,byte[])void")


def build_router() -> Router:
    owner_key = g_owner_key()
    keeper_key = g_keeper_key()
    storage_key = g_storage_app_key()
    fee_key = g_fee_split_bps_key()
    version_key = g_version_key()

    router = Router(
        "AlgoFlowExecution",
        BareCallActions(
            no_op=OnCompleteAction.create_only(
                Seq(
                    App.globalPut(owner_key, Txn.sender()),
                    App.globalPut(keeper_key, Txn.sender()),
                    App.globalPut(storage_key, Int(0)),
                    App.globalPut(fee_key, Int(0)),
                    App.globalPut(version_key, Int(1)),
                    Approve(),
                )
            ),
            delete_application=OnCompleteAction.call_only(
                Seq(ensure_owner(Txn.sender(), App.globalGet(owner_key)), Approve())
            ),
            update_application=OnCompleteAction.call_only(
                Seq(ensure_owner(Txn.sender(), App.globalGet(owner_key)), Approve())
            ),
            close_out=OnCompleteAction.never(),
            opt_in=OnCompleteAction.never(),
        ),
    )

    @router.method(name="configure")
    def configure_contract(
        storage_app_id: abi.Uint64,
        default_keeper: abi.Address,
        keeper_fee_bps: abi.Uint64,
    ) -> Expr:
        storage_value = ScratchVar(TealType.uint64)
        fee_value = ScratchVar(TealType.uint64)
        return Seq(
            storage_value.store(storage_app_id.get()),
            fee_value.store(keeper_fee_bps.get()),
            ensure_owner(Txn.sender(), App.globalGet(owner_key)),
            ensure_fee_bounds(fee_value.load()),
            App.globalPut(storage_key, storage_value.load()),
            App.globalPut(keeper_key, default_keeper.get()),
            App.globalPut(fee_key, fee_value.load()),
            Approve(),
        )

    @router.method(name="execute_intent")
    def execute_intent(
        intent_id: abi.Uint64,
        execution_plan: abi.DynamicBytes,
        fee_recipient: abi.Address,
    ) -> Expr:
        storage_value = ScratchVar(TealType.uint64)
        intent_bytes = ScratchVar(TealType.bytes)
        intent_record = abi_types.IntentRecord()
        owner_field = abi.Address()
        keeper_field = abi.Address()
        status_field = abi.Uint64()
        workflow_hash = abi_types.new_static_bytes32()
        workflow_blob = abi.DynamicBytes()
        version_field = abi.Uint64()
        trigger_field = abi.DynamicBytes()
        trigger_config = abi_types.TriggerConfig()
        trigger_type_field = abi.Uint64()
        trigger_oracle_app_field = abi.Uint64()
        trigger_oracle_key_field = abi.DynamicBytes()
        trigger_comparator_field = abi.Uint64()
        trigger_threshold_field = abi.Uint64()
        plan_array = abi.DynamicArray(
            abi.DynamicArrayTypeSpec(WorkflowStep().type_spec())
        )
        plan_length = ScratchVar(TealType.uint64)
        index = ScratchVar(TealType.uint64)
        step_tuple = WorkflowStep()
        opcode_field = abi.Uint64()
        target_field = abi.Uint64()
        asset_in_field = abi.Uint64()
        asset_out_field = abi.Uint64()
        amount_field = abi.Uint64()
        slippage_field = abi.Uint64()
        extra_field = abi.DynamicBytes()
        opcode_int = ScratchVar(TealType.uint64)
        target_int = ScratchVar(TealType.uint64)
        asset_in_int = ScratchVar(TealType.uint64)
        asset_out_int = ScratchVar(TealType.uint64)
        amount_int = ScratchVar(TealType.uint64)
        slippage_int = ScratchVar(TealType.uint64)
        status_int = ScratchVar(TealType.uint64)
        hash_check = ScratchVar(TealType.bytes)
        collateral_field = abi.Uint64()
        collateral_int = ScratchVar(TealType.uint64)
        keeper_fee_int = ScratchVar(TealType.uint64)
        keeper_account = abi.Address()

        return Seq(
            storage_value.store(App.globalGet(storage_key)),
            Assert(storage_value.load() != Int(0)),
            intent_bytes.store(
                read_intent_raw(storage_value.load(), intent_id.encode())
            ),
            intent_record.decode(intent_bytes.load()),
            intent_record.owner.store_into(owner_field),
            intent_record.keeper.store_into(keeper_field),
            intent_record.status.store_into(status_field),
            intent_record.workflow_hash.store_into(workflow_hash),
            intent_record.workflow_blob.store_into(workflow_blob),
            intent_record.version.store_into(version_field),
            intent_record.trigger_condition.store_into(trigger_field),
            intent_record.collateral.store_into(collateral_field),
            status_int.store(status_field.get()),
            Assert(status_int.load() == Int(constants.INTENT_STATUS_ACTIVE)),
            If(Len(trigger_field.get()) == Int(0))
            .Then(
                Seq(
                    trigger_type_field.set(Int(triggers.TRIGGER_TYPE_NONE)),
                    trigger_oracle_app_field.set(Int(0)),
                    trigger_oracle_key_field.set(Bytes("")),
                    trigger_comparator_field.set(Int(triggers.COMPARATOR_GTE)),
                    trigger_threshold_field.set(Int(0)),
                )
            )
            .Else(
                Seq(
                    trigger_config.decode(trigger_field.get()),
                    trigger_config.trigger_type.store_into(trigger_type_field),
                    trigger_config.oracle_app_id.store_into(trigger_oracle_app_field),
                    trigger_config.oracle_price_key.store_into(trigger_oracle_key_field),
                    trigger_config.comparator.store_into(trigger_comparator_field),
                    trigger_config.threshold.store_into(trigger_threshold_field),
                )
            ),
            validate_trigger(
                trigger_type_field.get(),
                trigger_oracle_app_field.get(),
                trigger_oracle_key_field.get(),
                trigger_comparator_field.get(),
                trigger_threshold_field.get(),
            ),
            hash_check.store(Sha256(execution_plan.get())),
            Assert(hash_check.load() == workflow_hash.get()),
            call_update_status(
                storage_value.load(),
                intent_id.get(),
                Int(constants.INTENT_STATUS_EXECUTING),
                Bytes("exec_start"),
            ),
            plan_array.decode(execution_plan.get()),
            plan_length.store(plan_array.length()),
            Assert(plan_length.load() > Int(0)),
            For(index.store(Int(0)), index.load() < plan_length.load(), index.store(index.load() + Int(1))).Do(
                Seq(
                    plan_array[index.load()].store_into(step_tuple),
                    step_tuple.opcode.store_into(opcode_field),
                    step_tuple.target_app_id.store_into(target_field),
                    step_tuple.asset_in.store_into(asset_in_field),
                    step_tuple.asset_out.store_into(asset_out_field),
                    step_tuple.amount.store_into(amount_field),
                    step_tuple.slippage_bps.store_into(slippage_field),
                    step_tuple.extra.store_into(extra_field),
                    opcode_int.store(abi_utils.uint64_to_int(opcode_field)),
                    target_int.store(abi_utils.uint64_to_int(target_field)),
                    asset_in_int.store(abi_utils.uint64_to_int(asset_in_field)),
                    asset_out_int.store(abi_utils.uint64_to_int(asset_out_field)),
                    amount_int.store(abi_utils.uint64_to_int(amount_field)),
                    slippage_int.store(abi_utils.uint64_to_int(slippage_field)),
                    dispatch_workflow_step(
                        opcode_int.load(),
                        target_int.load(),
                        asset_in_int.load(),
                        asset_out_int.load(),
                        amount_int.load(),
                        slippage_int.load(),
                        extra_field.get(),
                        owner_field.get(),
                    ),
                )
            ),
            collateral_int.store(abi_utils.uint64_to_int(collateral_field)),
            keeper_fee_int.store(
                WideRatio(
                    [collateral_int.load(), App.globalGet(fee_key)],
                    [Int(constants.KEEPER_FEE_SCALE)],
                )
            ),
            keeper_account.set(
                If(fee_recipient.get() == Global.zero_address())
                .Then(keeper_field.get())
                .Else(fee_recipient.get())
            ),
            maybe_pay_keeper(keeper_account.get(), keeper_fee_int.load()),
            call_update_status(
                storage_value.load(),
                intent_id.get(),
                Int(constants.INTENT_STATUS_SUCCESS),
                hash_check.load(),
            ),
            events.log_intent_status(
                intent_id.encode(),
                Itob(Int(constants.INTENT_STATUS_SUCCESS)),
                Txn.sender(),
            ),
            Approve(),
        )

    return router


@Subroutine(TealType.bytes)
def read_intent_raw(storage_app_id: Expr, intent_id_bytes: Expr) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: storage_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [READ_INTENT_RAW_SELECTOR, intent_id_bytes],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    extract_abi_return(InnerTxn.last_log()),
    )


@Subroutine(TealType.none)
def call_update_status(storage_app_id: Expr, intent_id_int: Expr, status_code: Expr, detail: Expr) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: storage_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    UPDATE_STATUS_SELECTOR,
                    Itob(intent_id_int),
                    Itob(status_code),
                    detail,
                ],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.bytes)
def extract_abi_return(log_value: Expr) -> Expr:
    return Seq(
        Assert(Len(log_value) >= Int(4)),
        Assert(Substring(log_value, Int(0), Int(4)) == ABI_RETURN_PREFIX),
        Substring(log_value, Int(4), Len(log_value)),
    )


@Subroutine(TealType.none)
def dispatch_workflow_step(
    opcode: Expr,
    target_app_id: Expr,
    asset_in: Expr,
    asset_out: Expr,
    amount: Expr,
    slippage_bps: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    return Cond(
        [opcode == Int(opcodes.OPCODE_SWAP), execute_swap(target_app_id, asset_in, asset_out, amount, slippage_bps, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_PROVIDE_LIQUIDITY), execute_provide_liquidity(target_app_id, asset_in, asset_out, amount, slippage_bps, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_STAKE), execute_stake(target_app_id, asset_in, amount, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_TRANSFER), execute_transfer(asset_in, amount, extra_args)],
        [opcode == Int(opcodes.OPCODE_LEND_SUPPLY), execute_lend_supply(target_app_id, asset_in, amount, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_LEND_WITHDRAW), execute_lend_withdraw(target_app_id, asset_out, amount, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_WITHDRAW_LIQUIDITY), execute_withdraw_liquidity(target_app_id, asset_in, asset_out, amount, slippage_bps, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_UNSTAKE), execute_unstake(target_app_id, asset_in, amount, extra_args, owner)],
        [Int(1), Reject()],
    )


@Subroutine(TealType.uint64)
def amount_after_slippage(amount: Expr, slippage_bps: Expr) -> Expr:
    return amount - WideRatio(
        [amount, slippage_bps],
        [Int(constants.KEEPER_FEE_SCALE)],
    )


@Subroutine(TealType.none)
def execute_swap(
    target_app_id: Expr,
    asset_in: Expr,
    asset_out: Expr,
    amount: Expr,
    slippage_bps: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    min_return = ScratchVar(TealType.uint64)
    return Seq(
        Assert(amount > Int(0)),
        Assert(slippage_bps <= Int(constants.KEEPER_FEE_SCALE)),
        min_return.store(amount_after_slippage(amount, slippage_bps)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: target_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("swap"),
                    Itob(asset_in),
                    Itob(asset_out),
                    Itob(amount),
                    Itob(min_return.load()),
                    extra_args,
                ],
                TxnField.assets: [asset_in, asset_out],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def execute_provide_liquidity(
    target_app_id: Expr,
    asset_a: Expr,
    asset_b: Expr,
    amount_a: Expr,
    slippage_bps: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    paired_amount = ScratchVar(TealType.uint64)
    return Seq(
        Assert(amount_a > Int(0)),
        Assert(slippage_bps <= Int(constants.KEEPER_FEE_SCALE)),
        paired_amount.store(amount_after_slippage(amount_a, slippage_bps)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: target_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("provide_liquidity"),
                    Itob(asset_a),
                    Itob(asset_b),
                    Itob(amount_a),
                    Itob(paired_amount.load()),
                    extra_args,
                ],
                TxnField.assets: [asset_a, asset_b],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def execute_stake(
    staking_app_id: Expr,
    asset_id: Expr,
    amount: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    return Seq(
        Assert(amount > Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: staking_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("stake"),
                    Itob(asset_id),
                    Itob(amount),
                    extra_args,
                ],
                TxnField.assets: [asset_id],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def execute_transfer(asset_id: Expr, amount: Expr, recipient_bytes: Expr) -> Expr:
    return Seq(
        Assert(amount > Int(0)),
        Assert(Len(recipient_bytes) == Int(32)),
        InnerTxnBuilder.Begin(),
        If(asset_id == Int(0))
        .Then(
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: Int(1),
                    TxnField.receiver: recipient_bytes,
                    TxnField.amount: amount,
                    TxnField.fee: Int(0),
                }
            )
        )
        .Else(
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: Int(4),
                    TxnField.xfer_asset: asset_id,
                    TxnField.asset_amount: amount,
                    TxnField.asset_receiver: recipient_bytes,
                    TxnField.fee: Int(0),
                }
            )
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def maybe_pay_keeper(recipient: Expr, amount: Expr) -> Expr:
    return If(And(recipient != Global.zero_address(), amount > Int(0))).Then(
        Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: Int(1),
                    TxnField.receiver: recipient,
                    TxnField.amount: amount,
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
        )
    )


@Subroutine(TealType.none)
def validate_trigger(
    trigger_type: Expr,
    oracle_app_id: Expr,
    oracle_key: Expr,
    comparator: Expr,
    threshold: Expr,
) -> Expr:
    price_value = ScratchVar(TealType.uint64)
    oracle_param = App.globalGetEx(oracle_app_id, oracle_key)
    return Seq(
        If(trigger_type != Int(triggers.TRIGGER_TYPE_NONE)).Then(
            Seq(
                Assert(oracle_app_id != Int(0)),
                oracle_param,
                Assert(oracle_param.hasValue()),
                price_value.store(oracle_param.value()),
                Assert(
                    Or(
                        comparator == Int(triggers.COMPARATOR_GTE),
                        comparator == Int(triggers.COMPARATOR_LTE),
                    )
                ),
                If(comparator == Int(triggers.COMPARATOR_GTE))
                .Then(Assert(price_value.load() >= threshold))
                .Else(Assert(price_value.load() <= threshold)),
            )
        )
    )


@Subroutine(TealType.none)
def execute_lend_supply(
    lending_app_id: Expr,
    asset_id: Expr,
    amount: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    return Seq(
        Assert(asset_id > Int(0)),
        Assert(amount > Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: lending_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("lend_supply"),
                    Itob(asset_id),
                    Itob(amount),
                    extra_args,
                ],
                TxnField.assets: [asset_id],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def execute_lend_withdraw(
    lending_app_id: Expr,
    asset_id: Expr,
    amount: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    return Seq(
        Assert(asset_id > Int(0)),
        Assert(amount > Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: lending_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("lend_withdraw"),
                    Itob(asset_id),
                    Itob(amount),
                    extra_args,
                ],
                TxnField.assets: [asset_id],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def execute_withdraw_liquidity(
    target_app_id: Expr,
    asset_a: Expr,
    asset_b: Expr,
    liquidity_amount: Expr,
    slippage_bps: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    return Seq(
        Assert(liquidity_amount > Int(0)),
        Assert(slippage_bps <= Int(constants.KEEPER_FEE_SCALE)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: target_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("withdraw_liquidity"),
                    Itob(asset_a),
                    Itob(asset_b),
                    Itob(liquidity_amount),
                    Itob(slippage_bps),
                    extra_args,
                ],
                TxnField.assets: [asset_a, asset_b],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


@Subroutine(TealType.none)
def execute_unstake(
    staking_app_id: Expr,
    asset_id: Expr,
    amount: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    return Seq(
        Assert(amount > Int(0)),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: staking_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [
                    Bytes("unstake"),
                    Itob(asset_id),
                    Itob(amount),
                    extra_args,
                ],
                TxnField.assets: [asset_id],
                TxnField.accounts: [owner],
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


def approval_program(version: int = TEAL_VERSION) -> Expr:
    router = build_router()
    if hasattr(router, "approval_ast"):
        return router.approval_ast.program_construction()
    compiled = router.compile_program(version=version)
    if isinstance(compiled, tuple):
        return compiled[0]
    if hasattr(compiled, "approval_program"):
        return compiled.approval_program
    return compiled


def clear_state_program(version: int = TEAL_VERSION) -> Expr:
    router = build_router()
    if hasattr(router, "clear_state"):
        return router.clear_state
    compiled = router.compile_program(version=version)
    if isinstance(compiled, tuple):
        return compiled[1]
    if hasattr(compiled, "clear_state_program"):
        return compiled.clear_state_program
    return compiled
