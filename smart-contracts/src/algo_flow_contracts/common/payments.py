"""Group payment validation helpers."""

from pyteal import (
    Assert,
    Expr,
    Global,
    Gtxn,
    If,
    Int,
    Seq,
    Subroutine,
    TealType,
    Txn,
)

@Subroutine(TealType.none)
def ensure_collateral_payment(amount: Expr) -> Expr:
    group_index = Txn.group_index()
    expected_receiver = Global.current_application_address()
    return If(amount != Int(0)).Then(
        Seq(
            Assert(group_index > Int(0)),
            Assert(Gtxn[group_index - Int(1)].type_enum() == Int(1)),
            Assert(Gtxn[group_index - Int(1)].receiver() == expected_receiver),
            Assert(Gtxn[group_index - Int(1)].sender() == Txn.sender()),
            Assert(Gtxn[group_index - Int(1)].amount() == amount),
        )
    )
