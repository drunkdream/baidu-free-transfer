# -*- coding: utf-8 -*-

import logging

from . import utils


class BaiduFileTransfer(object):
    """Baidu File Transfer"""

    def __init__(self, api, share_key, pwd=None, root_path=None):
        self._api = api
        self._share_key = share_key
        self._pwd = pwd
        self._root_path = root_path or ""
        self._share_root = ""
        self._user_id = None
        self._share_id = None
        self._dir_list = []
        self._file_list = []

    async def init_share_data(self):
        if self._pwd:
            await self._api.update_randsk(self._share_key, self._pwd)
        try:
            share_data = await self._api.get_share_data(self._share_key, self._pwd)
        except utils.BaiduYunPanRedirectError as ex:
            if ex.url.startswith("/share/init"):
                if not self._pwd:
                    raise ValueError("Password not specified")
                else:
                    raise ValueError("Wrong password: %s" % self._pwd)
        self._user_id = share_data["user_id"]
        self._share_id = share_data["share_id"]
        self._api.bdstoken = share_data["bdstoken"]
        self._share_root = share_data["root_path"]
        self._dir_list = share_data["dir_list"]
        self._file_list = share_data["file_list"]

    async def list_share_dir_tree(self, path):
        dir_list, file_list = await self._api.list_share_dir(
            self._user_id, self._share_id, path
        )
        for dir in dir_list:
            dir["dir_list"], dir["file_list"] = await self.list_share_dir_tree(
                path + "/" + dir["name"]
            )
        return dir_list, file_list

    async def transfer_files(self, file_list, target_path):
        max_transfer_count = 500
        offset = 0
        while offset < len(file_list):
            await self._api.transfer(
                self._user_id,
                self._share_id,
                [it["id"] for it in file_list[offset : offset + max_transfer_count]],
                target_path,
            )
            offset += max_transfer_count
        utils.logger.info(
            "[%s] Transfer %d files under directory %s success"
            % (self.__class__.__name__, len(file_list), target_path)
        )

    async def transfer_dirs(self, dir_list, target_path):
        if target_path:
            await self._api.create_directory(target_path)
        if not dir_list:
            return
        dir_paths = ["%s/%s" % (target_path, it["name"]) for it in dir_list]
        try:
            await self._api.transfer(
                self._user_id,
                self._share_id,
                [dir["id"] for dir in dir_list],
                target_path,
            )
        except utils.TransferLimitExceededError as ex:
            utils.logger.warning(
                "[%s] Directory %s %s"
                % (self.__class__.__name__, ",".join(dir_paths), ex)
            )
            if len(dir_list) >= 2:
                mid = len(dir_list) // 2
                await self.transfer_dirs(dir_list[:mid], target_path)
                await self.transfer_dirs(dir_list[mid:], target_path)
            else:
                # transfer subdirs and files
                dir = dir_list[0]
                dir_path = self._share_root
                if target_path[len(self._root_path) :]:
                    dir_path += target_path[len(self._root_path) :]
                dir_path += "/" + dir["name"]
                dir_list, file_list = await self._api.list_share_dir(
                    self._user_id,
                    self._share_id,
                    dir_path,
                )
                if dir_list:
                    await self.transfer_dirs(dir_list, target_path + "/" + dir["name"])
                if file_list:
                    await self.transfer_files(
                        file_list, target_path + "/" + dir["name"]
                    )
        else:
            utils.logger.info(
                "[%s] Transfer directory %s success"
                % (self.__class__.__name__, ",".join(dir_paths))
            )

    async def transfer(self):
        if self._dir_list:
            await self.transfer_dirs(self._dir_list, self._root_path)
        if self._file_list:
            await self.transfer_files(self._file_list, self._root_path)
