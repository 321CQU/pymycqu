"""图书馆相关模块"""

from __future__ import annotations

from typing import Any, Dict, List

from requests import Session

from ..auth import access_service, async_access_service
from ..utils.request_transformer import RequestTransformer, Request

__all__ = ['access_library', 'async_access_library',
           'get_curr_books_raw', 'get_history_books_raw', 'async_get_borrow_books_raw',
           'parse_response']

ACCESS_URL = "http://lib.cqu.edu.cn:8002/api/Auth/AccessToken"
AUTHORIZE_URL = "http://lib.cqu.edu.cn:8000/useridentify/api/third-part-auth/token-by-cas-for-verify-first-login"
CURR_BOOKS_URL = "http://lib.cqu.edu.cn:8000/opac/api/user-opac-center/loan-list"
HISTORY_BOOKS_URL = "http://lib.cqu.edu.cn:8000/opac/api/user-opac-center/history-loan-list"
BOOK_SEARCH_URL = "http://lib.cqu.edu.cn:8000/articlesearch/api/search/asset-search"
RENEW_BOOK_URL = "http://lib.cqu.edu.cn:8000/opac/api/user-opac-center/renew"
GET_BOOK_POS_URL = "http://lib.cqu.edu.cn:8000/opac/api/search-collection-status/collection-status-by-id"


@RequestTransformer.register()
def _access_library(request: Request, ticket: str) -> str:
    res1 = yield request.post(ACCESS_URL, json={
        "orgCode": "cqu",
        "OrgTokenLink": ACCESS_URL
    })
    token1 = res1.json()["data"]["token"]
    res2 = yield request.get(
        AUTHORIZE_URL,
        params={'service': "http://lib.cqu.edu.cn/", "ticket": ticket}, headers={'Authorization': "Bearer " + token1})
    token2 = res2.json()["data"]["token"]
    return "Bearer " + token2



def access_library(session: Session):
    """
    通过统一身份认证登陆图书馆页面，返回UserID和UserKey用于查询

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    """
    res = access_service(session, "http://lib.cqu.edu.cn/")
    ticket = res.url[30:]
    token = _access_library.sync_request(session, ticket)
    session.headers["Authorization"] = token

async def async_access_library(session: Request):
    """
    异步的通过统一身份认证登陆图书馆页面，返回UserID和UserKey用于查询

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    """
    res = await async_access_service(session, "http://lib.cqu.edu.cn/")
    ticket = str(res.url)[30:]
    token = await _access_library.async_request(session, ticket)
    session.headers["Authorization"] = token


@RequestTransformer.register()
def _get_borrow_books_raw(request: Request, is_curr: bool):
    res = yield request.get(CURR_BOOKS_URL if is_curr else HISTORY_BOOKS_URL)
    return res.json()['data']['data']


def get_curr_books_raw(session: Session) -> Dict:
    """
    获取当前借阅书籍

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :return: 反序列化的书籍信息json
    :rtype: Dict
    """
    return _get_borrow_books_raw.sync_request(session, True)


def get_history_books_raw(session: Session) -> Dict:
    """
    获取历史借阅书籍

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :return: 反序列化的书籍信息json
    :rtype: Dict
    """
    return _get_borrow_books_raw.sync_request(session, False)

async def async_get_borrow_books_raw(session: Request, is_curr: bool) -> Dict:
    """
    异步的获取当前书籍借阅信息

    :param session: 登录了统一身份认证（:func:`.auth.login`）并在 mycqu 进行了认证（:func:`.mycqu.access_mycqu`）的 requests 会话
    :type session: Session
    :param is_curr: 是否为当前借阅信息（为False回传历史借阅信息
    :return: 反序列化的书籍信息json
    :rtype: Dict
    """
    return await _get_borrow_books_raw.async_request(session, is_curr)

@RequestTransformer.register()
def _renew_book(request: Request, book_id: int) -> Dict:
    res = yield request.post(RENEW_BOOK_URL, json={
        'data': str(book_id)
    })

    return res.json()

@RequestTransformer.register()
def _get_book_pos(request: Request, book_id: int):
    res = yield request.get(params={'bookid': book_id})
    return res.json().get('data')

def parse_response(target: List[Dict], field_name: str) -> List[str]:
    result = list(filter(lambda x: x['fieldName'] == field_name, target))
    return result[0].get('values') if len(result) != 0 else []
