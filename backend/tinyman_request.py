"""
pool_info_fetcher.py
Fetches on-chain pool data (address, tokens, reserves, TVL, APY) from Tinyman Analytics API.
Works for any public Tinyman pool — no SDK or keys needed.
"""

import requests
import sys

def get_pool_info(pair="USDC_ALGO", network="mainnet"):
    url = f"https://{network}.analytics.tinyman.org/api/v1/pools/?search={pair}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()["results"]
    if not data:
        return {"error": f"Pool {pair} not found"}

    p = data[0]
    asset_1 = p["asset_1"]
    asset_2 = p["asset_2"]
    return {
        "pair": f"{asset_1['unit_name']}/{asset_2['unit_name']}",
        "pool_app_id": p["app_id"],
        "pool_address": p["address"],
        "tvl_usd": p["tvl"],
        "apy": p.get("apy") or p.get("apr"),
        "volume_24h": p["volume_24h"],
        "reserves": {
            asset_1["unit_name"]: p["asset_1_reserves"],
            asset_2["unit_name"]: p["asset_2_reserves"]
        }
    }

if __name__ == "__main__":
    pair = sys.argv[1] if len(sys.argv) > 1 else "ALGO_USDC"
    info = get_pool_info(pair)
    for k, v in info.items():
        print(f"{k}: {v}")
