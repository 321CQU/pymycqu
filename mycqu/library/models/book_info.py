from __future__ import annotations

import json
from typing import Any, Dict, Optional, List, Tuple

from pydantic import BaseModel
from requests import Session
from datetime import date, datetime

from ...utils.request_transformer import RequestTransformer, Request
from ..tools import parse_response, _get_borrow_books_raw, _renew_book
from ...utils.datetimes import date_from_str, datetime_from_str

__all__ = ['BookInfo']


class BookInfo(BaseModel):
    """
    图书馆书籍相关信息
    """
    id: Optional[int] = None
    """书籍id"""
    title: str
    """书籍名称"""
    call_no: str
    """书籍检索号"""
    library_name: str
    """所属图书馆（如虎溪图书馆自然科学阅览室等）"""
    borrow_time: datetime
    """借出时间"""
    should_return_time: Optional[date] = None
    """应归还日期"""
    is_return: bool
    """是否被归还"""
    return_time: Optional[date] = None
    """归还时间"""
    renew_count: int
    """续借次数"""
    can_renew: bool
    """是否可被续借"""

    @staticmethod
    def from_list(*data: List[str], is_curr: bool) -> List[BookInfo]:
        max_len = max(map(lambda x: len(x), data))
        standard_data = list(map(lambda x: x if len(x) == max_len else [None for i in range(max_len)], data))
        book_infos: List[Tuple] = list(zip(*standard_data))

        result: List[BookInfo] = []

        for book_info in book_infos:
            result.append(
                BookInfo(
                    id=book_info[0],
                    title=book_info[1],
                    call_no=book_info[2],
                    library_name=book_info[3],
                    borrow_time=datetime_from_str(book_info[4]),
                    should_return_time=date_from_str(book_info[5]) if book_info[5] is not None else None,
                    is_return= not is_curr,
                    return_time=date_from_str(book_info[6]) if book_info[6] is not None else None,
                    renew_count=book_info[7],
                    can_renew=book_info[8] if book_info[8] is not None else False,
                )
            )

        return result

    @staticmethod
    @RequestTransformer.register()
    def _fetch(session: Request, is_curr: bool) -> List[BookInfo]:
        res = yield _get_borrow_books_raw, {'is_curr': is_curr}
        data = res.get('columns')
        if data is None:
            return []

        ids = parse_response(data, 'bookId')
        titles = parse_response(data, 'title')
        call_nos = parse_response(data, 'indexNumber')
        library_names = parse_response(data, 'roomName')
        borrow_times = parse_response(data, 'borrowDate')
        should_return_times = parse_response(data, 'shouldReturnDate')
        return_times = parse_response(data, 'returnDate')
        renew_count = parse_response(data, 'renewalNumber')
        can_renews = parse_response(data, 'renewflag')

        return BookInfo.from_list(ids, titles, call_nos, library_names,
                                  borrow_times, should_return_times,
                                  return_times, renew_count, can_renews,
                                  is_curr=is_curr)


    @staticmethod
    def fetch(session: Session, is_curr: bool) -> List[BookInfo]:
        """
        获取当前/历史借阅书籍

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu和lib.cqu.edu.cn 进行了认证（:func:`.mycqu.access_mycqu` :func:`.library.access_library`）的 requests 会话
        :type session: Session
        :param is_curr: 是否获取当前借阅书籍（为否则获取历史借阅书籍）
        :type is_curr: bool
        :return: 图书对象组成的列表
        :rtype: List[BookInfo]
        """
        return BookInfo._fetch.sync_request(session, is_curr)

    @staticmethod
    async def async_fetch(session: Session, is_curr: bool) -> List[BookInfo]:
        """
        异步的获取当前/历史借阅书籍

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu和lib.cqu.edu.cn 进行了认证（:func:`.mycqu.access_mycqu` :func:`.library.access_library`）的 requests 会话
        :type session: Session
        :param is_curr: 是否获取当前借阅书籍（为否则获取历史借阅书籍）
        :type is_curr: bool
        :return: 图书对象组成的列表
        :rtype: List[BookInfo]
        """
        return await BookInfo._fetch.async_request(session, is_curr)

    @staticmethod
    def _parse_renew_result(res: Dict) -> str:
        if res.get('data') is not None:
            if res['data'].get('code') == 200:
                return "success"
            elif res['data'].get('message') is not None and res['data']['message'] != "":
                return res['data']['message']
        return "未知异常"

    @staticmethod
    def renew(session: Session, book_id: str) -> str:
        return BookInfo._parse_renew_result(_renew_book.sync_request(session, book_id))


    @staticmethod
    async def async_renew(session: Request, book_id: str) -> str:
        return BookInfo._parse_renew_result((await _renew_book.async_request(session, book_id)))
