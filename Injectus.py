#!/usr/bin/env python3.7

import argparse
import asyncio
import logging
import re
import sys
import signal
import time

from multiprocessing import Pool, Process, JoinableQueue
from urllib.parse import urlsplit, urlunsplit, unquote
from pathlib import Path

from utils import build_crlf_list, build_openredirect_list

import aiohttp
import aiofiles

class bcolors:
    HEADER       = "\033[95m"
    OKBLUE       = "\033[94m"
    OKGREEN      = "\033[92m"
    RED          = "\033[31m"
    WARNING      = "\033[93m"
    FAIL         = "\033[91m"
    ENDC         = "\033[0m"
    BOLD         = "\033[1m"
    UNDERLINE    = "\033[4m"

banner = f'''
{bcolors.OKGREEN}
    ▪   ▐ ▄  ▐▄▄▄▄▄▄ . ▄▄· ▄▄▄▄▄▄• ▄▌.▄▄ · 
    ██ •█▌▐█  ·██▀▄.▀·▐█ ▌▪•██  █▪██▌▐█ ▀. 
    ▐█·▐█▐▐▌▪▄ ██▐▀▀▪▄██ ▄▄ ▐█.▪█▌▐█▌▄▀▀▀█▄
    ▐█▌██▐█▌▐▌▐█▌▐█▄▄▌▐███▌ ▐█▌·▐█▄█▌▐█▄▪▐█
    ▀▀▀▀▀ █▪ ▀▀▀• ▀▀▀ ·▀▀▀  ▀▀▀  ▀▀▀  ▀▀▀▀ {bcolors.ENDC}
               {bcolors.UNDERLINE}{bcolors.FAIL}~ BOUNTYSTRIKE ~{bcolors.ENDC}
'''


class SigHandler:
    def __init__(self, async_queue):
        self.queue = async_queue
    def __call__(self, signo, frame):
        print("\n[-] CTRL-C Detected, attempting graceful shutdown...")
        print("[-] Notifying workers to shutdown...")

        self.queue._queue.clear()
        self.queue._finished.set()
        self.queue._unfinished_tasks = 0

async def worker(name: str, queue, session, delay):
    while True:
        try:
            url_dict = await queue.get()
        except asyncio.QueueEmpty:
            break

        if url_dict is None:
            break

        u = url_dict

        try:
            async with session.get(u.get("url"), allow_redirects=False) as resp:

                if u.get("type") == "crlf":
                    if "bounty" in resp.headers.keys():
                        print(f"{bcolors.OKGREEN}[{name}] CRLF Injection detected: {u.get('url')}{bcolors.ENDC}")
                    else:
                        print(f'[{name}] injecting crlf payloads {u.get("url")} {bcolors.FAIL}[FAILED]{bcolors.ENDC}')

                if u.get("type") == "openredirect":
                    # This comparison is un ugly hack because aiohttp only support scheme to be
                    # either https|http|''. Need to set redirect=False because of this.
                    if "Location" in resp.headers.keys() and resp.headers["Location"].startswith(unquote(u["payload"])):
                        print(f"{bcolors.OKGREEN}[{name}] Open redirect detected: {u.get('url')}{bcolors.ENDC}")
                    else:
                        print(f'[{name}] injecting open redirect payloads {u.get("url")} {bcolors.FAIL}[FAILED]{bcolors.ENDC}')

                await asyncio.sleep(delay)

        except asyncio.TimeoutError:
            print(f"{bcolors.WARNING}[ERROR][{name}] timed out when attacking {u.get('url')}...{bcolors.ENDC}")
            queue.task_done()
            continue
        except Exception as e:
            print(f"[ERROR] Something went wrong: {e}")
            queue.task_done()
            break
  
        queue.task_done()


async def start(args):
    started_at = time.time()
    filename = args.file
    workers = args.workers
    url = args.url
    async_queue = asyncio.Queue()
    delay = args.delay

    signal.signal(signal.SIGINT, SigHandler(async_queue))

    if url:
        if args.crlf:
            for payload in build_crlf_list(url):
                if args.no_request:
                    print(payload)
                else:
                    await async_queue.put(payload)

        if args.openredirect:
            for payload in build_openredirect_list(url):
                if args.no_request:
                    print(payload)
                else:
                    await async_queue.put(payload)
    else:
        async with aiofiles.open(f"{filename}", "r") as f:
            async for domain in f:
                domain = domain.replace("\n", "")

                if args.crlf:
                    for inject in build_crlf_list(domain):
                        if args.no_request:
                            print(f"[{inject['type']}] {inject['url']}")
                        else:
                           await async_queue.put(inject)

                if args.openredirect:
                    for inject in build_openredirect_list(domain):
                        if args.no_request:
                            print(f"[{inject['type']}] {inject['url']}")
                        else:
                           await async_queue.put(inject)

    if not args.no_request:
        # Create workers
        tasks = []
        size = async_queue.qsize()
        connector = aiohttp.TCPConnector(
            ssl=False,
            limit=50,
        )
        session = aiohttp.ClientSession(connector=connector,timeout=aiohttp.ClientTimeout(total=args.timeout))
        for i in range(workers):
            task = asyncio.create_task(worker(f'worker-{i}', async_queue, session, delay))
            tasks.append(task)

        # Wait until the queue is fully processed.
        await async_queue.join()

        # Cancel our worker tasks.
        for task in tasks:
            task.cancel()
        await session.close()
        # Wait until all worker tasks are cancelled.
        await asyncio.gather(*tasks, return_exceptions=True)
        time_ended = time.time() - started_at

        print('=====================================')
        print(f"[+] Processing time: {time_ended} seconds")
        print(f"[+] Total URLs {size}")


def main():
    parser = argparse.ArgumentParser(prog="Injectus", description="CRLF and open redirect fuzzer. Crafted by @dubs3c.")
    parser.add_argument("-f", "--file", action="store", dest="file", help="File containing URLs")
    parser.add_argument("-u", "--url", action="store", dest="url", help="Single URL to test")
    parser.add_argument("-r", "--no-request", action="store_true", dest="no_request", help="Only build attack list, do not perform any requests")
    parser.add_argument("-w", "--workers", type=int, default=10, dest="workers", action="store", help="Amount of asyncio workers, default is 10")
    parser.add_argument("-t", "--timeout", type=int, default=6, dest="timeout", action="store", help="HTTP request timeout, default is 6 seconds")
    parser.add_argument("-d", "--delay", type=int, default=1, dest="delay", action="store", help="The delay between requests, default is 1 second")
    parser.add_argument("-c", "--crlf", action="store_true", dest="crlf", help="Only perform crlf attacks")
    parser.add_argument("-op", "--openredirect", action="store_true", dest="openredirect", help="Only perform open redirect attacks")
    args = parser.parse_args()

    if len(sys.argv) == 1:
        print(banner)
        parser.print_help()
        quit()

    if not args.url and not Path.exists(Path(args.file).resolve()):
        print(f"{args.file} does not exist")
        quit()

    if args.url and args.file:
        print("Can't specify both -u and -f, choose one!")
        quit()

    if args.crlf and not args.openredirect:
        args.openredirect = False

    if args.openredirect and not args.crlf:
        args.crlf = False

    if not args.openredirect and not args.crlf:
        args.crlf = True
        args.openredirect = True


    asyncio.run(start(args))

if __name__ == "__main__":
    main()