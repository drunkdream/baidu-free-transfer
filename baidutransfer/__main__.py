# -*- coding: utf-8 -*-

import argparse
import asyncio
import logging
import os
import sys
import urllib.parse

import yaml

from . import apis, transfer, utils


async def main():
    parser = argparse.ArgumentParser(
        prog="baidutransfer", description="Baidu yunpan free transfer tool"
    )
    parser.add_argument(
        "url",
        help="baidu pan url, e.g. https://pan.baidu.com/s/1yQ7wutp3m1XtEhsigf_X6A or https://pan.baidu.com/share/init?surl=yQ7wutp3m1XtEhsigf_X6A",
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="config yaml file path"
    )
    parser.add_argument("-C", "--cookie", help="cookie of pan.baidu.com")
    parser.add_argument("-p", "--password", help="share password")

    args = parser.parse_args()
    url = urllib.parse.urlparse(args.url)
    share_key = ""
    if url.hostname == "pan.baidu.com":
        if url.path.startswith("/s/1"):
            share_key = url.path.split("/")[-1][1:]
        elif url.path == "/share/init":
            share_key = url.query.split("=", 1)[1]
    if not share_key:
        print("Invalid url %s" % args.url, file=sys.stderr)
        return -1

    cookie = None
    if os.path.isfile(args.config):
        with open(args.config) as fp:
            config = yaml.safe_load(fp.read())
            if "cookie" in config:
                cookie = config["cookie"]
    if args.cookie:
        cookie = args.cookie
    if not cookie:
        print(
            "Please provide pan.baidu.com cookie from `-c config.yaml` or `-C cookie` argument",
            file=sys.stderr,
        )
        return -1

    utils.logger.level = logging.INFO
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s][%(levelname)s]%(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    utils.logger.propagate = 0
    utils.logger.addHandler(handler)

    api = apis.BaiduYunPanAPI(cookie)
    bft = transfer.BaiduFileTransfer(api, share_key, args.password)
    await bft.init_share_data()

    await bft.transfer()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
