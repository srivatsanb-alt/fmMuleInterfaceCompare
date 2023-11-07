import websockets
import ssl
import asyncio
import time


async def main():
    ssl_context = ssl.SSLContext()
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    ssl_context.load_verify_locations("../fm_rev_proxy_cert.pem")
    ws_url = "wss://192.168.6.62/ws/api/v1/sherpa/"
    async with websockets.connect(
        ws_url,
        extra_headers=(
            ("X-API-Key", "9amN2j1pdW00mSc3coX-96MNlUa7IkBnMpqs5pf6Rxw_L10185JYC"),
        ),
        ssl=ssl_context,
    ) as wss:
        print("connected")
        await asyncio.sleep(1)
        t1 = time.time()
        while time.time() - t1 < 5:
            print("connected")
            time.sleep(0.5)
        pass


asyncio.get_event_loop().run_until_complete(main())
