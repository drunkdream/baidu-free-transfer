# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import urllib.parse

from . import utils


class BaiduYunPanAPI(object):
    """Baidu YunPan API"""

    root_url = "https://pan.baidu.com"

    def __init__(self, cookie):
        self._cookie = self._process_cookie(cookie)
        self._bdstoken = None
        self._randsk = None

    def _process_cookie(self, cookie):
        pos = cookie.find("BDCLND=")
        if pos < 0:
            return cookie
        pos2 = cookie.find(";", pos)
        if pos2 < 0:
            pos2 = len(cookie)
        return cookie[:pos] + cookie[pos2:]

    async def request(
        self, path, method="get", headers=None, params=None, data=None, check_errno=True
    ):
        url = self.root_url + path
        status_code, headers, body = await utils.http_request(
            url,
            method=method,
            referer=self.root_url,
            cookie=self._cookie,
            headers=headers,
            params=params,
            data=data,
            raise_for_status=True,
        )
        if status_code > 300 and status_code < 400:
            raise utils.BaiduYunPanRedirectError(headers["Location"])
        if check_errno and body["errno"]:
            raise utils.BaiduYunPanAPIError(body["errno"], body.get("show_msg"))
        return body

    @property
    def bdstoken(self):
        if not self._bdstoken:
            raise ValueError("bdstoken is None")
        return self._bdstoken

    @bdstoken.setter
    def bdstoken(self, value):
        self._bdstoken = value

    async def get_bdstoken(self):
        path = "/api/gettemplatevariable"
        params = {
            "fields": '["bdstoken"]',
        }
        rsp = await self.request(path, params=params)
        return rsp["result"]["bdstoken"]

    async def create_directory(self, dirpath):
        try:
            await self.list_dir(dirpath)
        except utils.BaiduYunPanAPIError as ex:
            if ex.code != -9:
                raise ex
        else:
            # directory already exist
            return

        path = "/api/create"
        params = {
            "a": "commit",
            "bdstoken": self.bdstoken,
        }
        data = {
            "path": dirpath,
            "isdir": "1",
            "block_list": "[]",
        }
        await self.request(path, "post", params=params, data=data)

    async def get_randsk(self, share_key, pwd):
        path = "/share/verify"
        params = {
            "surl": share_key,
            "bdstoken": self.bdstoken,
        }
        data = {
            "pwd": pwd,
        }
        rsp = await self.request(path, "post", params=params, data=data)
        return rsp["randsk"]

    def _process_dir_file_list(self, dir_file_list):
        dir_list = []
        file_list = []
        for it in dir_file_list:
            if it["isdir"]:
                dir_list.append(
                    {
                        "id": it["fs_id"],
                        "name": it["server_filename"],
                    }
                )
            else:
                file_list.append(
                    {
                        "id": it["fs_id"],
                        "name": it["server_filename"],
                    }
                )
        return dir_list, file_list

    async def get_share_data(self, share_key, pwd=None):
        path = "/s/1%s" % share_key
        body = await self.request(path, check_errno=False)
        pos = body.find("locals.mset(")
        if pos <= 0:
            raise RuntimeError("Invalid body: %s" % body)
        pos2 = body.find("});", pos)
        data = json.loads(body[pos + 12 : pos2 + 1])
        root_path = urllib.parse.unquote(data["file_list"][0]["parent_path"])
        dir_list, file_list = self._process_dir_file_list(data["file_list"])
        return {
            "user_id": data["share_uk"],
            "share_id": data["shareid"],
            "bdstoken": data["bdstoken"],
            "root_path": root_path,
            "dir_list": dir_list,
            "file_list": file_list,
        }

    async def list_share_dir(self, user_id, share_id, dir_path):
        path = "/share/list"
        params = {
            "uk": user_id,
            "shareid": share_id,
            "page": "1",
            "num": "1000",
            "dir": dir_path,
        }
        rsp = await self.request(path, params=params)
        return self._process_dir_file_list(rsp["list"])

    async def list_dir(self, dir_path):
        path = "/api/list"
        params = {
            "order": "time",
            "desc": "1",
            "showempty": "0",
            "page": "1",
            "num": "1000",
            "dir": dir_path,
            "bdstoken": self.bdstoken,
        }
        rsp = await self.request(path, params=params)
        return rsp["list"]

    async def transfer(self, user_id, share_id, fsid_list, transfer_path):
        path = "/share/transfer"
        params = {
            "shareid": share_id,
            "from": user_id,
            "ondup": "newcopy",
            "channel": "chunlei",
            # "web": "1",
            "bdstoken": self.bdstoken,
        }
        data = {
            "fsidlist": "[%s]" % ",".join([str(it) for it in fsid_list]),
            "path": transfer_path or "/",
        }

        rsp = await self.request(
            path, "post", params=params, data=data, check_errno=False
        )
        if rsp["errno"] == 12:
            raise utils.TransferLimitExceededError(
                rsp["target_file_nums_limit"], rsp["target_file_nums"]
            )
        elif rsp["errno"] == 1504:
            # request exceeds deadline
            logging.warning(
                "[%s] Transfer path %s exceeds deadline, retry later..."
                % (self.__class__.__name__, transfer_path)
            )
            await asyncio.sleep(1)
            return await self.transfer(user_id, share_id, fsid_list, transfer_path)
        elif rsp["errno"]:
            raise utils.BaiduYunPanAPIError(rsp["errno"], rsp["show_msg"])

    async def update_randsk(self, share_key, pwd):
        if not self._bdstoken:
            self._bdstoken = await self.get_bdstoken()
        randsk = await self.get_randsk(share_key, pwd)
        self._cookie += ";BDCLND=%s" % randsk
