#!/usr/bin/env python3.7

import argparse
import asyncio
import logging
import re
import sys
import time

from multiprocessing import Pool, Process, JoinableQueue
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path

from utils import build_crlf_list, build_openredirect_list

try:
    import aiohttp
except ImportError:
    print("aiohttp is required, run pip3 install aiohttp --user")
    print("aiodns is required, run pip3 install aiodns --user")
    quit()

banner = '''

    ▪   ▐ ▄  ▐▄▄▄▄▄▄ . ▄▄· ▄▄▄▄▄▄• ▄▌.▄▄ · 
    ██ •█▌▐█  ·██▀▄.▀·▐█ ▌▪•██  █▪██▌▐█ ▀. 
    ▐█·▐█▐▐▌▪▄ ██▐▀▀▪▄██ ▄▄ ▐█.▪█▌▐█▌▄▀▀▀█▄
    ▐█▌██▐█▌▐▌▐█▌▐█▄▄▌▐███▌ ▐█▌·▐█▄█▌▐█▄▪▐█
    ▀▀▀▀▀ █▪ ▀▀▀• ▀▀▀ ·▀▀▀  ▀▀▀  ▀▀▀  ▀▀▀▀ 
              ~ BOUNTYSTRIKE ~
'''

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


async def worker(name: str, queue, session):
    while True:
        try:
            url_dict = await queue.get()
        except asyncio.QueueEmpty:
            break

        if url_dict is None:
            break

        u = url_dict

        try:
            async with session.get(u.get("url")) as resp:
                if u.get("type") == "crlf":
                    if "bounty" in resp.headers.keys():
                        print(f"{bcolors.OKGREEN}[{name}] CRLF Injection detected: {u.get('url')}{bcolors.ENDC}")
                    else:
                        print(f'[{name}] injecting crlf payloads {u.get("url")} {bcolors.FAIL}[FAILED]{bcolors.ENDC}')

                if u.get("type") == "openredirect":
                    if "Location" in resp.headers.keys() and "bountystrike.io" in resp.headers["Location"]:
                        print(f"{bcolors.OKGREEN}[{name}] Open redirect detected: {u.get('url')}{bcolors.ENDC}")
                    else:
                        print(f'[{name}] injecting open redirect payloads {u.get("url")} {bcolors.FAIL}[FAILED]{bcolors.ENDC}')
        except asyncio.TimeoutError:
            print(f"{bcolors.WARNING}[ERROR][{name}] timed out when attacking {u.get('url')}...{bcolors.ENDC}")
            queue.task_done()
            continue
        except Exception as e:
            print("[ERROR] Something went wrong...")
            print(e)
            queue.task_done()
            continue
  
        queue.task_done()


async def start(args):
    started_at = time.time()
    filename = args.file
    workers = args.workers
    url = args.url
    async_queue = asyncio.Queue()

    if url:
        if args.crlf:
            for payload in build_crlf_list(url):
                if args.no_request:
                    print(payload)
                else:
                    async_queue.put_nowait(payload)

        if args.openredirect:
            for payload in build_openredirect_list(url):
                if args.no_request:
                    print(payload)
                else:
                    async_queue.put_nowait(payload)
    else:
        with open(f"{filename}", "r") as f:

            for domain in f.readlines():
                domain = domain.replace("\n", "")

                if args.crlf:
                    for inject in build_crlf_list(domain):
                        if args.no_request:
                            print(f"[{inject['type']}] {inject['url']}")
                        else:
                            async_queue.put_nowait(inject)

                if args.openredirect:
                    for inject in build_openredirect_list(domain):
                        if args.no_request:
                            print(f"[{inject['type']}] {inject['url']}")
                        else:
                            async_queue.put_nowait(inject)

    if not args.no_request:
        # Create workers
        size = async_queue.qsize()
        tasks = []
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=args.timeout))
        for i in range(workers):
            task = asyncio.create_task(worker(f'worker-{i}', async_queue, session))
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
        print(f"Processing time: {time_ended} seconds")
        print(f"Total URLs proccessed {size}")


def main():
    parser = argparse.ArgumentParser(prog="Injectus", description="Brute force CRLF and open redirect payloads for a given target. Crafted by @dubs3c.")
    parser.add_argument("-f", "--file", action="store", dest="file", help="File containing URLs")
    parser.add_argument("-u", "--url", action="store", dest="url", help="Single URL to test")
    parser.add_argument("-r", "--no-request", action="store_true", dest="no_request", help="Only build attack list, do not perform any requests")
    parser.add_argument("-w", "--workers", type=int, default=20, dest="workers", action="store", help="Amount of asyncio workers, default is 20")
    parser.add_argument("-t", "--timeout", type=int, default=6, dest="timeout", action="store", help="HTTP request timeout, default is 6 seconds")
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