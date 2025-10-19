from __future__ import annotations

import os

from algosdk.v2client import algod
from dotenv import load_dotenv


def main() -> None:
    load_dotenv("smart-contracts/.env")
    load_dotenv()

    algod_address = os.environ.get("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
    algod_token = os.environ.get("ALGOD_TOKEN", "")
    client = algod.AlgodClient(algod_token, algod_address, headers={"User-Agent": "algosdk"})

    app_ids = [748015611, 748015612]
    for app_id in app_ids:
        try:
            info = client.application_info(app_id)
        except Exception as exc:  # noqa: BLE001 - surface raw error for clarity
            print(f"app {app_id}: lookup failed -> {exc}")
            continue

        if "application" not in info:
            print(f"app {app_id}: unexpected response -> {info}")
            continue

        params = info["application"]["params"]
        schema = params["global-state-schema"]
        creator = params.get("creator")
        created_round = info.get("created-at-round")
        print(
            f"app {app_id}: creator={creator} "
            f"uints={schema['num-uint']} bytes={schema['num-byte-slice']} "
            f"created-round={created_round}"
        )


if __name__ == "__main__":
    main()
