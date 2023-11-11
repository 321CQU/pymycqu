from __future__ import annotations

from typing import Generic, Optional

from requests import Session

from ...exception import MycquUnauthorized
from ...utils.request_transformer import Request
from pydantic import BaseModel

__all__ = ["User",]


class User(BaseModel, Generic[Request]):
    """用户信息"""

    name: str
    """姓名"""
    id: str
    """统一身份认证号"""
    code: str
    """学工号"""
    role: str
    """身份，已知取值有学生 :obj:`"student"`、教师 :obj:`"instructor`"`"""
    email: Optional[str]
    "电子邮箱"
    phone_number: Optional[str]
    "电话号码"

    @staticmethod
    def fetch_self(session: Session) -> User:
        """从在 mycqu 认证了的会话获取当前登录用户的信息

        :param session: 登陆了统一身份认证的会话
        :type session: Session
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :return: 当前用户信息
        :rtype: User
        """
        resp = session.get("https://my.cqu.edu.cn/authserver/simple-user")
        if resp.status_code == 401:
            raise MycquUnauthorized()
        data = resp.json()
        return User(
            name=data["name"],
            code=data["code"],
            id=data["username"],
            role=data["type"],
            email=data["email"],
            phone_number=data["phoneNumber"]
        )

    @staticmethod
    async def async_fetch_self(session: Request) -> User:
        """
        异步的从在 mycqu 认证了的会话获取当前登录用户的信息

        :param session: 登陆了统一身份认证的会话
        :type session: Session
        :raises MycquUnauthorized: 若会话未在 my.cqu.edu.cn 进行认证
        :return: 当前用户信息
        :rtype: User
        """
        resp = await session.get("https://my.cqu.edu.cn/authserver/simple-user")
        if resp.status_code == 401:
            raise MycquUnauthorized()
        data = resp.json()
        return User(
            name=data["name"],
            code=data["code"],
            id=data["username"],
            role=data["type"],
            email=data["email"],
            phone_number=data["phoneNumber"]
        )