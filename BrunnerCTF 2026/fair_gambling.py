#!/usr/bin/env python3
"""
Exploit for web_fair-gambling.

Bug: prepareSpin() commits to sha1(emoji_triplet) BEFORE you spin, but the
search space is only 7^3 = 343 combos, so the "commitment" is brute-forceable
instantly. Combined with the free "invalid sid -> discard & reprepare" path,
you can pre-check every offered hash for free and only ever spin on hashes
that resolve to a winning triplet

Usage:
    python3 fair_gambling.py wss://TARGET_HOST:PORT/ws
"""

import asyncio
import hashlib
import itertools
import json
import sys
import websockets

SYMBOLS = ["🍒", "🍋", "🍇", "🍉", "🔔", "⭐", "💎"]

# Precompute hash -> combo for every possible triplet
HASH_MAP = {
    hashlib.sha1("".join(combo).encode()).hexdigest(): combo
    for combo in itertools.product(SYMBOLS, repeat=3)
}


def crack(target_hash: str):
    return HASH_MAP.get(target_hash)


def is_win(combo):
    return combo[0] == combo[1] == combo[2]


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fair_gambling.py wss://host:port/ws")
        return
    url = sys.argv[1]

    async with websockets.connect(url) as ws:
        next_ref = None  # {"sid": ..., "hash": ...}
        flag_cost = None
        cash = None

        async def recv_json():
            return json.loads(await ws.recv())

        # initial state message
        state = await recv_json()
        assert state["type"] == "state"
        next_ref = state["next"]
        flag_cost = state["flagCost"]
        cash = state["cash"]
        print(f"[state] cash=${cash} spinCost=${state['spinCost']} flagCost=${flag_cost}")

        rounds = 0

        while cash < flag_cost:
            rounds += 1
            combo = crack(next_ref["hash"])

            win = is_win(combo)

            if win:
                print(f"[round {rounds}] hash resolves to WIN {combo} -> spinning")
                await ws.send(json.dumps({"type": "spin", "sid": next_ref["sid"]}))
                msg = await recv_json()
                if msg["type"] == "spin" and msg.get("status") == "revealed":
                    cash = msg["cash"]
                    streak = msg["streak"]
                    win_amt = msg["result"]["win"]
                    print(f"    -> won ${win_amt}, cash=${cash}, streak={streak}")
                    next_ref = msg["next"]
                else:
                    print("    -> unexpected response:", msg)
                    next_ref = msg.get("next", next_ref)
            else:
                # discard for free by sending a garbage sid
                await ws.send(json.dumps({"type": "spin", "sid": "invalid"}))
                msg = await recv_json()
                next_ref = msg["next"]

        print(f"[+] cash=${cash} >= flagCost=${flag_cost}, redeeming...")
        await ws.send(json.dumps({"type": "redeem"}))
        msg = await recv_json()
        if msg["type"] == "flag":
            print("[+] FLAG:", msg["flag"])
        else:
            print("[!] unexpected redeem response:", msg)


if __name__ == "__main__":
    asyncio.run(main())
