from __future__ import annotations

import re
from typing import ClassVar, Tuple, List, Optional

import requests
from requests import Session
from pydantic import BaseModel

from ...utils.request_transformer import Request, RequestTransformer
from ...exception import CQUSessionIdNotExist

CQUSESSIONS_URL = "https://my.cqu.edu.cn/api/timetable/optionFinder/session?blankOption=false"
SESSION_RE = re.compile("^([0-9]{4})年?(春|秋)$")


__all__ = ['CQUSession']


class CQUSession(BaseModel):
    """重大的某一学期
    """
    id: Optional[int] = None
    """学期ID"""
    year: int
    """主要行课年份"""
    is_autumn: bool
    """是否为秋冬季学期"""

    def __str__(self):
        return str(self.year) + ('秋' if self.is_autumn else '春')

    @RequestTransformer.register()
    def _get_id(self, client: Request) -> int:
        if self.id is not None:
            return self.id
        else:
            sessions: List[CQUSession] = yield self._fetch
            res = list(filter(lambda x: x.year == self.year and x.is_autumn == self.is_autumn, sessions))
            if len(res) == 0:
                raise CQUSessionIdNotExist
            else:
                return res[0].id

    def get_id(self, client: Request) -> int:
        return self._get_id.sync_request(client)

    async def async_get_id(self, client: Request) -> int:
        return self._get_id.async_request(client)

    @staticmethod
    def from_str(string: str, id: Optional[int] = None) -> CQUSession:
        """
        从学期字符串中解析学期，如果直接调用该方法，在获取id时会自动进行一次网络请求

        >>> CQUSession.from_str("2021春")
        CQUSession(year=2021, is_autumn=False)
        >>> CQUSession.from_str("2020年秋")
        CQUSession(year=2020, is_autumn=True)

        :param string: 学期字符串，如“2021春”、“2020年秋”
        :type string: str
        :param id: 学期id，应交由CQUSession方法自动设置
        :type id: Optional[int]
        :raises ValueError: 字符串不是一个预期中的学期字符串时抛出
        :return: 对应的学期
        :rtype: CQUSession
        """
        match = SESSION_RE.match(string)
        if match:
            result = CQUSession(
                year=match[1],
                is_autumn=match[2] == "秋"
            )
            result.id = id
            return result
        else:
            raise ValueError(f"string {string} is not a session")

    @staticmethod
    @RequestTransformer.register()
    def _fetch(request: Request) -> List[CQUSession]:
        session_list = []
        for session in (yield request.get(CQUSESSIONS_URL)).json():
            session_list.append(CQUSession.from_str(session["name"], int(session["id"])))
        return session_list

    @staticmethod
    def fetch(session: Optional[Session] = None) -> List[CQUSession]:
        """从 my.cqu.edu.cn 上获取各个学期

        :return: 各个学期组成的列表
        :rtype: List[CQUSession]
        """
        return CQUSession._fetch.sync_request(requests if session is None else session)

    @staticmethod
    async def async_fetch(session: Request) -> List[CQUSession]:
        """
        异步的从 my.cqu.edu.cn 上获取各个学期

        :return: 各个学期组成的列表
        :rtype: List[CQUSession]
        """
        return await CQUSession._fetch.async_request(session)
