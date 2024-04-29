from http3_client import *

async def send_timeout_request(url, headers = None, timeout=2):
    try:
        configuration = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)

        await asyncio.wait_for(send_request(
                                    configuration=configuration,
                                    url=url,
                                    include=True,
                                    output_dir="req_results",
                                    data=None,
                                    headers=headers
                                ), timeout)
        
        # print(f"{url} supports http3!")
        print(url)
        return url
    except asyncio.TimeoutError:
        # pass
        print(f"{url} timed out")
    except Exception as e:
        # pass
        # raise e
        print(f"{url} failed with {e}")


async def main():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 15_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; SM-G975U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.101 Mobile Safari/537.36"
    ]
    with open("website_list.txt") as f:
        urls = [f"{w.rstrip()}" for w in f.readlines()]

        # coros = [send_timeout_request(url) for url in urls]
        # await asyncio.gather(*coros)

        i = 0
        working_urls = []
        for url in urls:
            print(f"{i + 1}/{len(urls)}")
            for agent in user_agents:
                headers = {"User-Agent": agent}
                res = await send_timeout_request(url, headers=headers)

            # if res:
            #     working_urls.append(res)

            i += 1

        for url in working_urls:
            print(url)

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
