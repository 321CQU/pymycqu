from __future__ import annotations

from typing import List

from requests import Session
from pydantic import BaseModel

from .bill import Bill
from ..tools import get_card_raw, get_bill_raw, async_get_card_raw, async_get_bill_raw
from ...utils.request_transformer import Request


__all__ = ['Card']


class Card(BaseModel):
    """
    校园卡及其账单信息
    """
    id: str
    """校园卡id"""
    amount: float
    """账户余额"""

    @staticmethod
    def fetch(session: Session) -> Card:
        """
        从card.cqu.edu.cn获取校园卡信息

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :raises CQUWebsiteError: 当网页获取状态码不为0000时抛出
        :return: 获取的校园卡信息
        :rtype: Card
        """
        card_info = get_card_raw(session)

        return Card(
            id=card_info['acctNo'],
            amount=float(card_info['acctAmt'] / 100)
        )

    @staticmethod
    async def async_fetch(session: Request) -> Card:
        """
        异步的从card.cqu.edu.cn获取校园卡信息

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :raises CQUWebsiteError: 当网页获取状态码不为0000时抛出
        :return: 获取的校园卡信息
        :rtype: Card
        """
        card_info = await async_get_card_raw(session)

        return Card(
            id=card_info['acctNo'],
            amount=float(card_info['acctAmt'] / 100)
        )

    def fetch_bills(self, session: Session) -> List[Bill]:
        """
        从card.cqu.edu.cn获取校园卡账单

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :return: 获取的校园卡账单信息
        :rtype: dict
        """
        bill_info = get_bill_raw(session, self.id, 30)
        bills = []
        for bill in bill_info:
            bills.append(Bill.from_dict(bill))

        return bills

    async def async_fetch_bills(self, session: Request) -> List[Bill]:
        """
        异步的从card.cqu.edu.cn获取校园卡账单

        :param session: 登录了统一身份认证（:func:`.auth.login`）并在 card.cqu.edu.cn 进行了认证（:func:`.card.access_card`）的 requests 会话
        :type session: Session
        :return: 获取的校园卡账单信息
        :rtype: dict
        """
        bill_info = await async_get_bill_raw(session, self.id, 30)
        bills = []
        for bill in bill_info:
            bills.append(Bill.from_dict(bill))

        return bills