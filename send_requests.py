from http3_client import *

async def send_timeout_request(url, timeout=1):
    try:
        configuration = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)

        await asyncio.wait_for(send_request(
                                    configuration=configuration,
                                    url=url,
                                    include=True,
                                    output_dir="req_results",
                                    data=None,
                                ), timeout)
    except asyncio.TimeoutError:
        print(f"{url} timed out")
    except Exception as e:
        print(f"{url} failed with {e}")


async def main():
    with open("website_list.txt") as f:
        urls = [f"https://{w.rstrip()}" for w in f.readlines()]

        # coros = [send_timeout_request(url) for url in urls]
        # await asyncio.gather(*coros)

        i = 0
        for url in urls:
            print(f"{i + 1}/300")
            await send_timeout_request(url)
            i += 1

        # await send_request(
        #     configuration=configuration,
        #     urls=urls,
        #     include=True,
        #     output_dir=".",
        #     data=None,
        #     local_port=0,
        #     zero_rtt=True
        # )


if __name__ == "__main__":
    asyncio.run(main())
