# -*- coding: utf-8 -*-

import json
import logging
import os

import aiohttp

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"

logger = logging.getLogger("baidutransfer")


class BaiduYunPanResourceNotFoundError(RuntimeError):
    """Baidu YunPan Resource Not Found Error"""

    pass


class BaiduYunPanRedirectError(RuntimeError):
    """Baidu YunPan Redirect Error"""

    def __init__(self, url):
        self._url = url
    
    @property
    def url(self):
        return self._url

    def __str__(self):
        return "Redirect to %s" % self._url


class BaiduYunPanAPIError(RuntimeError):
    """Baidu YunPan API Error"""

    def __init__(self, code, errmsg):
        self._code = code
        self._errmsg = errmsg

    def __str__(self):
        return "BaiduYunPanAPIError: [%d] %s" % (self._code, self._errmsg)

    @property
    def code(self):
        return self._code

    @property
    def errmsg(self):
        return self._errmsg


class BaiduYunPanAPIParameterError(BaiduYunPanAPIError):
    """API Parameter Error"""

    def __init__(self, url, params):
        self._url = url
        self._params = params

    def __str__(self):
        return "APIParameterError: url=%s param=%s" % (self._url, json.dumps(self._params))


class TransferLimitExceededError(RuntimeError):
    """Transfer Limit Exceeded Error"""

    def __init__(self, limit, count):
        self._limit = limit
        self._count = count

    def __str__(self):
        return "TransferLimitExceededError: limit=%d count=%d" % (
            self._limit,
            self._count,
        )


async def http_request(
    url,
    method="get",
    referer=None,
    cookie=None,
    headers=None,
    params=None,
    data=None,
    raise_for_status=True,
):
    headers = headers or {}
    headers["User-Agent"] = USER_AGENT
    headers["X-Requested-With"] = "XMLHttpRequest"
    headers["Referer"] = referer or url
    if cookie:
        headers["Cookie"] = cookie
    proxy = os.environ.get("https_proxy")
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(verify_ssl=False)
    ) as session:
        func = getattr(session, method)
        async with func(
            url,
            headers=headers,
            params=params,
            data=data,
            proxy=proxy,
            allow_redirects=False,
        ) as response:
            if raise_for_status:
                response.raise_for_status()
            body = await response.text()
            if response.headers.get("Content-Type", "").startswith("application/json"):
                body = json.loads(body)
            return response.status, response.headers, body
