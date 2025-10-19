"""Intent storage contract for AlgoFlow intents."""

from pyteal import (
    And,
    App,
    AppParam,
    Approve,
    Assert,
    BareCallActions,
    Bytes,
    Itob,
    Expr,
    Global,
    If,
    Int,
    Len,
    Pop,
    OnCompleteAction,
    Or,
    Router,
    ScratchVar,
    Seq,
    Subroutine,
    TealType,
    Txn,
    TxnField,
    abi,
    InnerTxnBuilder,
)

from ..common import abi_types, constants, events, layout, payments, status, validation
from ..common.expressions import (
    g_fee_split_bps_key,
    g_keeper_key,
    g_min_collateral_key,
    g_next_intent_key,
    g_owner_key,
    g_executor_app_key,
    g_version_key,
)


TEAL_VERSION = 8


def build_router() -> Router:
    owner_key = g_owner_key()
    keeper_key = g_keeper_key()
    next_intent_key = g_next_intent_key()
    min_collateral_key = g_min_collateral_key()
    version_key = g_version_key()
    fee_split_key = g_fee_split_bps_key()
    executor_key = g_executor_app_key()

    router = Router(
        "AlgoFlowIntentStorage",
        BareCallActions(
            no_op=OnCompleteAction.create_only(
                Seq(
                    App.globalPut(owner_key, Txn.sender()),
                    App.globalPut(keeper_key, Txn.sender()),
                    App.globalPut(next_intent_key, Int(1)),
                    App.globalPut(version_key, Int(1)),
                    App.globalPut(min_collateral_key, Int(0)),
                    App.globalPut(fee_split_key, Int(0)),
                    App.globalPut(executor_key, Int(0)),
                    Approve(),
                )
            ),
            delete_application=OnCompleteAction.call_only(owner_assert(owner_key)),
            update_application=OnCompleteAction.call_only(owner_assert(owner_key)),
            close_out=OnCompleteAction.never(),
            opt_in=OnCompleteAction.never(),
        ),
    )

    @router.method(name="configure")
    def configure_contract(
        default_keeper: abi.Address,
        min_collateral: abi.Uint64,
        fee_split_bps: abi.Uint64,
        executor_app_id: abi.Uint64,
    ) -> Expr:
        min_collateral_value = ScratchVar(TealType.uint64)
        fee_value = ScratchVar(TealType.uint64)
        executor_value = ScratchVar(TealType.uint64)
        return Seq(
            min_collateral_value.store(min_collateral.get()),
            fee_value.store(fee_split_bps.get()),
            executor_value.store(executor_app_id.get()),
            validation.ensure_owner(Txn.sender(), App.globalGet(owner_key)),
            validation.ensure_fee_bounds(fee_value.load()),
            App.globalPut(keeper_key, default_keeper.get()),
            App.globalPut(min_collateral_key, min_collateral_value.load()),
            App.globalPut(fee_split_key, fee_value.load()),
            App.globalPut(executor_key, executor_value.load()),
            Approve(),
        )

    @router.method(name="register_intent")
    def register_intent(
        workflow_hash: abi_types.StaticBytes32,
        workflow_blob: abi.DynamicBytes,
        trigger_condition: abi.DynamicBytes,
        collateral_amount: abi.Uint64,
        keeper_override: abi.Address,
        workflow_version: abi.Uint64,
        app_escrow_id: abi.Uint64,
        app_asa_id: abi.Uint64,
        *,
        output: abi.Uint64,
    ) -> Expr:
        next_id = ScratchVar(TealType.uint64)
        encoded_intent = ScratchVar(TealType.bytes)
        record = abi_types.IntentRecord()
        owner_addr = abi.Address()
        keeper_addr = abi.Address()
        status_field = abi.Uint64()
        collateral_value = ScratchVar(TealType.uint64)
        escrow_value = ScratchVar(TealType.uint64)
        asa_value = ScratchVar(TealType.uint64)

        return Seq(
            validation.ensure_workflow_size(workflow_blob.get()),
            collateral_value.store(collateral_amount.get()),
            Assert(collateral_value.load() >= App.globalGet(min_collateral_key)),
            payments.ensure_collateral_payment(collateral_value.load()),
            next_id.store(App.globalGet(next_intent_key)),
            App.globalPut(next_intent_key, next_id.load() + Int(1)),
            owner_addr.set(Txn.sender()),
            keeper_addr.set(
                If(keeper_override.get() == Global.zero_address())
                .Then(App.globalGet(keeper_key))
                .Else(keeper_override.get())
            ),
            status_field.set(status.active()),
            escrow_value.store(app_escrow_id.get()),
            asa_value.store(app_asa_id.get()),
            record.set(
                owner_addr,
                collateral_amount,
                workflow_hash,
                status_field,
                workflow_blob,
                keeper_addr,
                workflow_version,
                trigger_condition,
                app_escrow_id,
                app_asa_id,
            ),
            encoded_intent.store(record.encode()),
            write_box(layout.intent_box_key(next_id.load()), encoded_intent.load()),
            output.set(next_id.load()),
            events.log_intent_created(
                Itob(next_id.load()),
                owner_addr.get(),
                workflow_version.encode(),
            ),
            Approve(),
        )

    @router.method(name="update_intent_status")
    def update_intent_status(
        intent_id: abi.Uint64,
        new_status: abi.Uint64,
        detail: abi.DynamicBytes,
    ) -> Expr:
        stored_record = abi_types.IntentRecord()
        owner_field = abi.Address()
        keeper_field = abi.Address()
        current_status = abi.Uint64()
        collateral = abi.Uint64()
        workflow_hash = abi_types.new_static_bytes32()
        workflow_blob = abi.DynamicBytes()
        version_field = abi.Uint64()
        trigger_field = abi.DynamicBytes()
        escrow_field = abi.Uint64()
        asa_field = abi.Uint64()
        encoded = ScratchVar(TealType.bytes)
        new_record = abi_types.IntentRecord()
        current_status_int = ScratchVar(TealType.uint64)
        new_status_int = ScratchVar(TealType.uint64)
        executor_addr = ScratchVar(TealType.bytes)
        executor_param = AppParam.address(App.globalGet(executor_key))

        key = layout.intent_box_key(intent_id.get())
        box_value = App.box_get(key)

        return Seq(
            box_value,
            executor_param,
            new_status_int.store(new_status.get()),
            Assert(new_status_int.load() >= Int(constants.INTENT_STATUS_ACTIVE)),
            Assert(new_status_int.load() <= Int(constants.INTENT_STATUS_CANCELLED)),
            Assert(box_value.hasValue()),
            stored_record.decode(box_value.value()),
            stored_record.owner.store_into(owner_field),
            stored_record.keeper.store_into(keeper_field),
            stored_record.status.store_into(current_status),
            stored_record.collateral.store_into(collateral),
            stored_record.workflow_hash.store_into(workflow_hash),
            stored_record.workflow_blob.store_into(workflow_blob),
            stored_record.version.store_into(version_field),
            stored_record.trigger_condition.store_into(trigger_field),
            stored_record.app_escrow_id.store_into(escrow_field),
            stored_record.app_asa_id.store_into(asa_field),
            current_status_int.store(current_status.get()),
            If(executor_param.hasValue())
            .Then(executor_addr.store(executor_param.value()))
            .Else(executor_addr.store(Bytes(""))),
            Assert(
                Or(
                    Txn.sender() == owner_field.get(),
                    Txn.sender() == keeper_field.get(),
                    And(
                        App.globalGet(executor_key) != Int(0),
                        executor_param.hasValue(),
                        Txn.sender() == executor_addr.load(),
                    ),
                )
            ),
            Assert(
                valid_status_transition(
                    current_status_int.load(), new_status_int.load()
                )
            ),
            new_record.set(
                owner_field,
                collateral,
                workflow_hash,
                new_status,
                workflow_blob,
                keeper_field,
                version_field,
                trigger_field,
                escrow_field,
                asa_field,
            ),
            encoded.store(new_record.encode()),
            write_box(key, encoded.load()),
            events.log_intent_status(
                intent_id.encode(), new_status.encode(), Txn.sender()
            ),
            events.log_execution_result(
                intent_id.encode(), new_status.encode(), detail.get()
            ),
            Approve(),
        )

    @router.method(name="export_intent")
    def export_intent(intent_id: abi.Uint64, *, output: abi_types.IntentRecord) -> Expr:
        key = layout.intent_box_key(intent_id.get())
        box_value = App.box_get(key)
        return Seq(
            box_value,
            Assert(box_value.hasValue()),
            output.decode(box_value.value()),
            Approve(),
        )

    @router.method(name="read_intent_raw")
    def read_intent_raw(intent_id: abi.Uint64, *, output: abi.DynamicBytes) -> Expr:
        key = layout.intent_box_key(intent_id.get())
        box_value = App.box_get(key)
        return Seq(
            box_value,
            Assert(box_value.hasValue()),
            output.set(box_value.value()),
            Approve(),
        )

    @router.method(name="withdraw_intent")
    def withdraw_intent(
        intent_id: abi.Uint64,
        recipient: abi.Address,
        *,
        output: abi.Uint64,
    ) -> Expr:
        stored_record = abi_types.IntentRecord()
        owner_field = abi.Address()
        keeper_field = abi.Address()
        status_field = abi.Uint64()
        collateral = abi.Uint64()
        workflow_hash = abi_types.new_static_bytes32()
        workflow_blob = abi.DynamicBytes()
        version_field = abi.Uint64()
        trigger_field = abi.DynamicBytes()
        escrow_field = abi.Uint64()
        asa_field = abi.Uint64()
        new_record = abi_types.IntentRecord()
        encoded = ScratchVar(TealType.bytes)
        receiver_addr = abi.Address()
        collateral_int = ScratchVar(TealType.uint64)
        status_int = ScratchVar(TealType.uint64)

        key = layout.intent_box_key(intent_id.get())
        box_value = App.box_get(key)

        return Seq(
            box_value,
            Assert(box_value.hasValue()),
            stored_record.decode(box_value.value()),
            stored_record.owner.store_into(owner_field),
            stored_record.keeper.store_into(keeper_field),
            stored_record.status.store_into(status_field),
            stored_record.collateral.store_into(collateral),
            stored_record.workflow_hash.store_into(workflow_hash),
            stored_record.workflow_blob.store_into(workflow_blob),
            stored_record.version.store_into(version_field),
            stored_record.trigger_condition.store_into(trigger_field),
            stored_record.app_escrow_id.store_into(escrow_field),
            stored_record.app_asa_id.store_into(asa_field),
            validation.ensure_owner(Txn.sender(), owner_field.get()),
            status_int.store(status_field.get()),
            Assert(
                Or(
                    status_int.load() == Int(constants.INTENT_STATUS_SUCCESS),
                    status_int.load() == Int(constants.INTENT_STATUS_FAILED),
                    status_int.load() == Int(constants.INTENT_STATUS_CANCELLED),
                )
            ),
            collateral_int.store(collateral.get()),
            validation.ensure_nonzero(collateral_int.load()),
            receiver_addr.set(
                If(recipient.get() == Global.zero_address())
                .Then(owner_field.get())
                .Else(recipient.get())
            ),
            send_payment(receiver_addr.get(), collateral_int.load()),
            collateral.set(Int(0)),
            new_record.set(
                owner_field,
                collateral,
                workflow_hash,
                status_field,
                workflow_blob,
                keeper_field,
                version_field,
                trigger_field,
                escrow_field,
                asa_field,
            ),
            encoded.store(new_record.encode()),
            write_box(key, encoded.load()),
            output.set(collateral_int.load()),
            events.log_intent_status(
                intent_id.encode(), status_field.encode(), Txn.sender()
            ),
            Approve(),
        )

    return router


@Subroutine(TealType.none)
def owner_assert(owner_key: Expr) -> Expr:
    return Seq(validation.ensure_owner(Txn.sender(), App.globalGet(owner_key)), Approve())


@Subroutine(TealType.none)
def write_box(key: Expr, value: Expr) -> Expr:
    length = ScratchVar(TealType.uint64)
    existing = App.box_get(key)
    return Seq(
        length.store(Len(value)),
        Assert(length.load() <= Int(constants.MAX_WORKFLOW_BYTES_LITERAL)),
        existing,
        If(existing.hasValue())
        .Then(App.box_put(key, value))
        .Else(
            Seq(Pop(App.box_create(key, length.load())), App.box_put(key, value))
        ),
    )


@Subroutine(TealType.uint64)
def valid_status_transition(current_status: Expr, new_status: Expr) -> Expr:
    allowed = Or(
        current_status == new_status,
        And(
            current_status == Int(constants.INTENT_STATUS_ACTIVE),
            Or(
                new_status == Int(constants.INTENT_STATUS_EXECUTING),
                new_status == Int(constants.INTENT_STATUS_CANCELLED),
            ),
        ),
        And(
            current_status == Int(constants.INTENT_STATUS_EXECUTING),
            Or(
                new_status == Int(constants.INTENT_STATUS_SUCCESS),
                new_status == Int(constants.INTENT_STATUS_FAILED),
            ),
        ),
    )
    return If(allowed, Int(1), Int(0))


@Subroutine(TealType.none)
def send_payment(receiver: Expr, amount: Expr) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: Int(1),
                TxnField.receiver: receiver,
                TxnField.amount: amount,
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
