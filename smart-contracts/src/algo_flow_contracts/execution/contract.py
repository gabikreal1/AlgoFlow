"""Execution router contract for AlgoFlow intents."""

from pyteal import (
    AccountParam,
    And,
    App,
    Approve,
    Assert,
    AssetHolding,
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
    Not,
    OnComplete,
    OnCompleteAction,
    Or,
    Reject,
    Return,
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

from ..common import abi_types, abi_utils, constants, events, layout, opcodes, triggers
from ..common.abi_types import WorkflowStep
from ..common.expressions import (
    g_fee_split_bps_key,
    g_keeper_key,
    g_owner_key,
    g_storage_app_key,
    g_version_key,
)
from ..common.inner_txn import itxn_set_box_reference


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
        app_escrow_field = abi.Uint64()
        app_asa_field = abi.Uint64()
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

        return Seq(
            storage_value.store(App.globalGet(storage_key)),
            Assert(storage_value.load() != Int(0)),
            intent_bytes.store(
                read_intent_raw(storage_value.load(), intent_id.get())
            ),
            intent_record.decode(intent_bytes.load()),
            intent_record.owner.store_into(owner_field),
            intent_record.keeper.store_into(keeper_field),
            intent_record.status.store_into(status_field),
            intent_record.workflow_hash.store_into(workflow_hash),
            intent_record.workflow_blob.store_into(workflow_blob),
            intent_record.version.store_into(version_field),
            intent_record.trigger_condition.store_into(trigger_field),
            intent_record.app_escrow_id.store_into(app_escrow_field),
            intent_record.app_asa_id.store_into(app_asa_field),
            intent_record.collateral.store_into(collateral_field),
            status_int.store(status_field.get()),
            Assert(status_int.load() == Int(constants.INTENT_STATUS_ACTIVE)),
            opt_in_asset(app_asa_field.get()),
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
            # Balance tracking: asset_id -> available_amount
            # For first step, use plan amount; subsequent steps use actual output
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
                    # Use plan amount for first step, or if amount is non-zero (explicit amount)
                    # Otherwise steps inherit actual output from previous step via balance delta
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
def read_intent_raw(storage_app_id: Expr, intent_id_int: Expr) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: storage_app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: [READ_INTENT_RAW_SELECTOR, Itob(intent_id_int)],
                TxnField.fee: Int(0),
            }
        ),
        itxn_set_box_reference(
            storage_app_id, layout.intent_box_key(intent_id_int)
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
        itxn_set_box_reference(
            storage_app_id, layout.intent_box_key(intent_id_int)
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
        [opcode == Int(opcodes.OPCODE_SWAP),
         swap_step(target_app_id, asset_in, asset_out, amount, slippage_bps, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_PROVIDE_LIQUIDITY),
         provide_liquidity_step(target_app_id, asset_in, asset_out, amount, slippage_bps, extra_args, owner)],
        [opcode == Int(opcodes.OPCODE_TRANSFER),
         transfer_step(asset_in, amount, extra_args)],
        [Int(1), Reject()],
    )


@Subroutine(TealType.uint64)
def amount_after_slippage(amount: Expr, slippage_bps: Expr) -> Expr:
    return amount - WideRatio(
        [amount, slippage_bps],
        [Int(constants.KEEPER_FEE_SCALE)],
    )


@Subroutine(TealType.none)
def transfer_to_pool(asset_id: Expr, amount: Expr, destination: Expr) -> Expr:
    return Seq(
        Assert(Len(destination) == Int(32)),
        Assert(amount > Int(0)),
        InnerTxnBuilder.Begin(),
        If(asset_id == Int(0))
        .Then(
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: Int(1),
                    TxnField.receiver: destination,
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
                    TxnField.asset_receiver: destination,
                    TxnField.fee: Int(0),
                }
            )
        ),
        InnerTxnBuilder.Submit(),
    )


def inner_app_call(
    app_id: Expr,
    args,
    assets,
    accounts,
) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(6),
                TxnField.application_id: app_id,
                TxnField.on_completion: Int(0),
                TxnField.application_args: args,
                TxnField.assets: assets,
                TxnField.accounts: accounts,
                TxnField.fee: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


def capture_balance(asset_id: Expr, slot: ScratchVar) -> Expr:
    return slot.store(get_balance(asset_id))


@Subroutine(TealType.uint64)
def compute_delta(pre_value: Expr, post_value: Expr) -> Expr:
    return post_value - pre_value


@Subroutine(TealType.uint64)
def resolve_amount(asset_id: Expr, requested_amount: Expr) -> Expr:
    return If(requested_amount == Int(0)).Then(get_balance(asset_id)).Else(requested_amount)


@Subroutine(TealType.none)
def swap_step(
    pool_app: Expr,
    asset_in: Expr,
    asset_out: Expr,
    amount: Expr,
    slippage_bps: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    """
    Swap asset_in for asset_out.
    If amount == 0, use entire balance of asset_in.
    """
    pre_out = ScratchVar(TealType.uint64)
    post_out = ScratchVar(TealType.uint64)
    delta_out = ScratchVar(TealType.uint64)
    min_return = ScratchVar(TealType.uint64)
    pool_addr = ScratchVar(TealType.bytes)
    actual_amount = ScratchVar(TealType.uint64)
    return Seq(
        pool_addr.store(extract_pool_address(extra_args)),
        actual_amount.store(resolve_amount(asset_in, amount)),
        Assert(actual_amount.load() > Int(0)),
        Assert(slippage_bps <= Int(constants.KEEPER_FEE_SCALE)),
        opt_in_asset(asset_in),
        opt_in_asset(asset_out),
        capture_balance(asset_out, pre_out),
        transfer_to_pool(asset_in, actual_amount.load(), pool_addr.load()),
        min_return.store(amount_after_slippage(actual_amount.load(), slippage_bps)),
        inner_app_call(
            pool_app,
            [
                Bytes("swap"),
                Itob(asset_in),
                Itob(asset_out),
                Itob(actual_amount.load()),
                Itob(min_return.load()),
            ],
            [asset_in, asset_out],
            [pool_addr.load(), owner],
        ),
        capture_balance(asset_out, post_out),
        delta_out.store(compute_delta(pre_out.load(), post_out.load())),
    )


@Subroutine(TealType.none)
def provide_liquidity_step(
    pool_app: Expr,
    asset_a: Expr,
    asset_b: Expr,
    amount_a: Expr,
    slippage_bps: Expr,
    extra_args: Expr,
    owner: Expr,
) -> Expr:
    """
    Provide liquidity with asset_a and asset_b.
    If amount_a == 0, use entire balance of asset_a.
    """
    pre_b = ScratchVar(TealType.uint64)
    post_b = ScratchVar(TealType.uint64)
    delta_b = ScratchVar(TealType.uint64)
    paired_amount = ScratchVar(TealType.uint64)
    pool_addr = ScratchVar(TealType.bytes)
    actual_amount = ScratchVar(TealType.uint64)
    return Seq(
        pool_addr.store(extract_pool_address(extra_args)),
        actual_amount.store(resolve_amount(asset_a, amount_a)),
        Assert(actual_amount.load() > Int(0)),
        Assert(slippage_bps <= Int(constants.KEEPER_FEE_SCALE)),
        opt_in_asset(asset_a),
        opt_in_asset(asset_b),
        capture_balance(asset_b, pre_b),
        transfer_to_pool(asset_a, actual_amount.load(), pool_addr.load()),
        paired_amount.store(amount_after_slippage(actual_amount.load(), slippage_bps)),
        inner_app_call(
            pool_app,
            [
                Bytes("add_liquidity"),
                Itob(asset_a),
                Itob(asset_b),
                Itob(actual_amount.load()),
                Itob(paired_amount.load()),
            ],
            [asset_a, asset_b],
            [pool_addr.load(), owner],
        ),
        capture_balance(asset_b, post_b),
        delta_b.store(compute_delta(pre_b.load(), post_b.load())),
    )


@Subroutine(TealType.none)
def transfer_step(asset_id: Expr, amount: Expr, extra_args: Expr) -> Expr:
    """
    Transfer asset to recipient.
    If amount == 0, transfer entire balance of asset_id.
    """
    pre_value = ScratchVar(TealType.uint64)
    post_value = ScratchVar(TealType.uint64)
    delta_value = ScratchVar(TealType.uint64)
    recipient = ScratchVar(TealType.bytes)
    actual_amount = ScratchVar(TealType.uint64)
    return Seq(
        recipient.store(extract_pool_address(extra_args)),
        actual_amount.store(resolve_amount(asset_id, amount)),
        Assert(actual_amount.load() > Int(0)),
        opt_in_asset(asset_id),
        capture_balance(asset_id, pre_value),
        transfer_to_pool(asset_id, actual_amount.load(), recipient.load()),
        capture_balance(asset_id, post_value),
        delta_value.store(compute_delta(pre_value.load(), post_value.load())),
    )


@Subroutine(TealType.none)
def opt_in_asset(asset_id: Expr) -> Expr:
    holding = AssetHolding.balance(Global.current_application_address(), asset_id)
    return If(asset_id != Int(0)).Then(
        Seq(
            holding,
            If(Not(holding.hasValue())).Then(
                Seq(
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetFields(
                        {
                            TxnField.type_enum: Int(4),
                            TxnField.xfer_asset: asset_id,
                            TxnField.asset_amount: Int(0),
                            TxnField.asset_receiver: Global.current_application_address(),
                            TxnField.fee: Int(0),
                        }
                    ),
                    InnerTxnBuilder.Submit(),
                )
            ),
        )
    )


@Subroutine(TealType.uint64)
def get_balance(asset_id: Expr) -> Expr:
    contract_address = Global.current_application_address()
    balance_slot = ScratchVar(TealType.uint64)
    algo_balance = AccountParam.balance(contract_address)
    asset_balance = AssetHolding.balance(contract_address, asset_id)
    return Seq(
        If(asset_id == Int(0))
        .Then(
            Seq(
                algo_balance,
                Assert(algo_balance.hasValue()),
                balance_slot.store(algo_balance.value()),
            )
        )
        .Else(
            Seq(
                asset_balance,
                If(asset_balance.hasValue())
                .Then(balance_slot.store(asset_balance.value()))
                .Else(balance_slot.store(Int(0))),
            )
        ),
        balance_slot.load(),
    )


@Subroutine(TealType.bytes)
def extract_pool_address(extra: Expr) -> Expr:
    return Seq(
        Assert(Len(extra) >= Int(32)),
        Substring(extra, Int(0), Int(32)),
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


def approval_program(version: int = TEAL_VERSION) -> Expr:
    router = build_router()
    if hasattr(router, "approval_ast"):
        approval_expr = router.approval_ast.program_construction()
    else:
        compiled = router.compile_program(version=version)
        if isinstance(compiled, tuple):
            approval_expr = compiled[0]
        elif hasattr(compiled, "approval_program"):
            approval_expr = compiled.approval_program
        else:
            approval_expr = compiled

    create_action = router.bare_call_actions.no_op.action
    delete_action = router.bare_call_actions.delete_application.action
    update_action = router.bare_call_actions.update_application.action

    bare_dispatch = Cond(
        [Txn.application_id() == Int(0), create_action],
        [Txn.on_completion() == OnComplete.DeleteApplication, delete_action],
        [Txn.on_completion() == OnComplete.UpdateApplication, update_action],
        [Int(1), Reject()],
    )

    return Seq(
        If(Txn.application_args.length() == Int(0)).Then(
            Seq(
                bare_dispatch,
                Return(Int(1)),
            )
        ),
        approval_expr,
    )


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
