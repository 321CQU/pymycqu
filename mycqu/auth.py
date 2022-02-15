"""统一身份认证相关的模块
"""
from typing import Dict, Optional, Callable
import random
import re
from base64 import b64encode
from html.parser import HTMLParser
from requests import Session, Response
from ._lib_wrapper.encrypt import pad, aes_cbc_encryptor

__all__ = ("NotAllowedService", "NeedCaptcha", "InvaildCaptcha",
           "IncorrectLoginCredentials", "UnknownAuthserverException", "NotLogined",
           "is_logined", "logout", "access_service", "login")

AUTHSERVER_URL = "http://authserver.cqu.edu.cn/authserver/login"
AUTHSERVER_CAPTCHA_DETERMINE_URL = "http://authserver.cqu.edu.cn/authserver/needCaptcha.html"
AUTHSERVER_CAPTCHA_IMAGE_URL = "http://authserver.cqu.edu.cn/authserver/captcha.html"
AUTHSERVER_LOGOUT_URL = "http://authserver.cqu.edu.cn/authserver/logout"
_CHAR_SET = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'


def _random_str(length: int):
    return ''.join(random.choices(_CHAR_SET, k=length))


class NotAllowedService(Exception):
    """试图认证不允许的服务时抛出
    """


class NeedCaptcha(Exception):
    """登录统一身份认证时需要输入验证码时拋出
    """

    def __init__(self, image: bytes, image_type: str, after_captcha: Callable[[str], Response]):
        super().__init__("captcha is needed")
        self.image: bytes = image
        """验证码图片文件数据"""
        self.image_type: str = image_type
        """验证码图片 MIME 类型"""
        self.after_captcha: Callable[[str], Response] = after_captcha
        """将验证码传入，调用以继续进行登陆"""


class InvaildCaptcha(Exception):
    """登录统一身份认证输入了无效验证码时抛出
    """

    def __init__(self):
        super().__init__("invaild captcha")


class IncorrectLoginCredentials(Exception):
    """使用无效的的登录凭据（如错误的用户、密码）
    """

    def __init__(self):
        super().__init__("incorrect username or password")


class UnknownAuthserverException(Exception):
    """登录或认证服务过程中未知错误
    """


class NotLogined(Exception):
    """未登陆或登陆过期的会话被用于进行需要统一身份认证登陆的操作
    """

    def __init__(self):
        super().__init__("not in logined status")


class MultiSessionConflict(Exception):
    """当前用户启用单处登录，并且存在其他登录会话时抛出"""

    def __init__(self, kick: Callable[[], Response], cancel: Callable[[], Response]):
        super().__init__("单处登录 enabled, kick other sessions of the user or cancel")
        self.kick: Callable[[], Response] = kick
        """踢掉其他会话并登录"""
        self.cancel: Callable[[], Response] = cancel
        """取消登录"""


class AuthPageParser(HTMLParser):
    _SALT_RE: re.Pattern = re.compile('var pwdDefaultEncryptSalt = "([^"]+)"')

    def __init__(self):
        super().__init__()
        self.input_data: Dict[str, Optional[str]] = \
            {'lt': None, 'dllt': None,
                'execution': None, '_eventId': None, 'rmShown': None}
        """几个关键的标签数据"""
        self.salt: Optional[str] = None
        """加密所用的盐"""
        self._js_start: bool = False
        self._js_end: bool = False
        self._error: bool = False
        self._error_head: bool = False

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            name: Optional[str] = None
            value: Optional[str] = None
            for attr in attrs:
                if attr[0] == 'name':
                    if attr[1] in self.input_data:
                        name = attr[1]
                    else:
                        break
                elif attr[0] == 'value':
                    value = attr[1]
            if name:
                self.input_data[name] = value
        elif tag == 'script' and attrs and attrs[0] == ("type", "text/javascript"):
            self._js_start = True
        elif tag == "div" and attrs == [("id", "msg"), ("class", "errors")]:
            self._error = True
        elif tag == 'h2' and self._error:
            self._error_head = True

    def handle_data(self, data):
        if self._js_start and not self._js_end:
            match = self._SALT_RE.search(data)
            if match:
                self.salt = match[1]
            self._js_end = True
        elif self._error_head:
            error_str = data.strip()
            if error_str == "应用未注册":
                raise NotAllowedService(error_str)
            raise UnknownAuthserverException(
                "Error message before login: "+error_str)


class LoginedPageParser(HTMLParser):  # pylint: ignore disable=missing-class-docstring
    MSG_ATTRS = [("id", "msg"), ("class", "login_auth_error")]
    KICK_TABLE_ATTRS = [("class", "kick_table")]
    KICK_POST_ATTRS = [('method', 'post'), ('id', 'continue')]
    CANCEL_POST_ATTRS = [('method', 'post'), ('id', 'cancel')]

    def __init__(self, status_code: int):
        super().__init__()
        self._msg: bool = False
        self._kick: bool = False
        self._waiting_kick_excution: bool = False
        self._kick_execution: str = ""
        self._waiting_cancel_excution: bool = False
        self._cancel_execution: str = ""
        self.status_code: int = status_code

    def handle_starttag(self, tag, attrs):
        if tag == "span" and attrs == self.MSG_ATTRS:
            self._msg = True
        elif tag == "table" and attrs == self.KICK_TABLE_ATTRS:
            self._kick = True
        elif tag == "form" and attrs == self.CANCEL_POST_ATTRS:
            self._waiting_cancel_excution = True
        elif tag == "form" and attrs == self.KICK_POST_ATTRS:
            self._waiting_kick_excution = True
        elif tag == "input" and ("name", "execution") in attrs:
            if self._waiting_kick_excution:
                for key, value in attrs:
                    if key == "value":
                        self._kick_execution = value
                        self._waiting_kick_excution = False
            elif self._waiting_cancel_excution:
                for key, value in attrs:
                    if key == "value":
                        self._cancel_execution = value
                        self._waiting_cancel_excution = False

    def handle_data(self, data):
        if self._msg:
            error_str = data.strip()
            if error_str == "无效的验证码":
                raise InvaildCaptcha()
            elif error_str == "您提供的用户名或者密码有误":
                raise IncorrectLoginCredentials()
            else:
                raise UnknownAuthserverException(
                    f"status code {self.status_code} is got (302 expected)"
                    f" when sending login post, {error_str}"
                )


def get_formdata(html: str, username: str, password: str) -> Dict[str, Optional[str]]:
    # from https://github.com/CQULHW/CQUQueryGrade
    parser = AuthPageParser()
    parser.feed(html)
    if not parser.salt:
        ValueError("无法获取盐")
    passwd_pkcs7 = pad((_random_str(64)+str(password)).encode())
    encryptor = aes_cbc_encryptor(
        parser.salt.encode(), _random_str(16).encode())
    passwd_encrypted = b64encode(encryptor(passwd_pkcs7)).decode()
    parser.input_data['username'] = username
    parser.input_data['password'] = passwd_encrypted
    return parser.input_data


def is_logined(session: Session) -> bool:
    """判断是否处于统一身份认证登陆状态

    :param session: 会话
    :type session: Session
    :return: :obj:`True` 如果处于登陆状态，:obj:`False` 如果处于未登陆或登陆过期状态
    :rtype: bool
    """
    return session.get(AUTHSERVER_URL, allow_redirects=False).status_code == 302


def logout(session: Session) -> None:
    """注销统一身份认证登录状态

    :param session: 进行过登录的会话
    :type session: Session
    """
    session.get("http://authserver.cqu.edu.cn/authserver/logout")


def access_service(session: Session, service: str) -> Response:
    resp = session.get(AUTHSERVER_URL,
                       params={"service": service},
                       allow_redirects=False)
    if resp.status_code != 302:
        AuthPageParser().feed(resp.text)
        raise NotLogined()
    return session.get(url=resp.headers['Location'], allow_redirects=False)


def login(session: Session,
          username: str,
          password: str,
          service: Optional[str] = None,
          timeout: int = 10,
          force_relogin: bool = False,
          captcha_callback: Optional[
              Callable[[bytes, str], Optional[str]]] = None,
          keep_longer: bool = False,
          kick_others: bool = False
          ) -> Response:
    """登录统一身份认证

    :param session: 用于登录统一身份认证的会话
    :type session: Session
    :param username: 统一身份认证号或学工号
    :type username: str
    :param password: 统一身份认证密码
    :type password: str
    :param service: 需要登录的服务，默认（:obj:`None`）则先不登陆任何服务
    :type service: Optional[str], optional
    :param timeout: 连接超时时限，默认为 10（单位秒）
    :type timeout: int, optional
    :param force_relogin: 强制重登，当会话中已经有有效的登陆 cookies 时依然重新登录，默认为 :obj:`False`
    :type force_relogin: bool, optional
    :param captcha_callback: 需要输入验证码时调用的回调函数，默认为 :obj:`None` 即不设置回调；
                             当需要输入验证码，但回调没有设置或回调返回 :obj:`None` 时，抛出异常 :class:`NeedCaptcha`；
                             该函数接受一个 :class:`bytes` 型参数为验证码图片的文件数据，一个 :class:`str` 型参数为图片的 MIME 类型，
                             返回验证码文本或 :obj:`None`。
    :type captcha_callback: Optional[Callable[[bytes, str], Optional[str]]], optional
    :param keep_longer: 保持更长时间的登录状态（保持一周）
    :type keep_longer: bool
    :param kick_others: 当目标用户开启了“单处登录”并有其他登录会话时，踢出其他会话并登录单前会话；若该参数为 :obj:`False` 则抛出
                       :class:`MultiSessionConflict`
    :type kick_others: bool
    :raises UnknownAuthserverException: 未知认证错误
    :raises InvaildCaptcha: 无效的验证码
    :raises IncorrectLoginCredentials: 错误的登陆凭据（如错误的密码、用户名）
    :raises NeedCaptcha: 需要提供验证码，获得验证码文本之后可调用所抛出异常的 :func:`NeedCaptcha.after_captcha` 函数来继续登陆
    :raises MultiSessionConflict: 和其他会话冲突
    :return: 登陆了统一身份认证后所跳转到的地址的 :class:`Response`
    :rtype: Response
    """
    def get_login_page():
        return session.get(
            url=AUTHSERVER_URL,
            params=None if service is None else {"service": service},
            allow_redirects=False,
            timeout=timeout)
    login_page = get_login_page()
    if login_page.status_code == 302:
        if not force_relogin:
            return login_page
        else:
            logout(session)
            login_page = get_login_page()
    elif login_page.status_code != 200:
        raise UnknownAuthserverException()
    try:
        formdata = get_formdata(login_page.text, username, password)
    except ValueError:
        logout(session)
        formdata = get_formdata(get_login_page().text, username, password)
    if keep_longer:
        formdata['rememberMe'] = 'on'

    def after_captcha(captcha_str: Optional[str]):
        if captcha_str is None:
            if "captchaResponse" in formdata:
                del formdata["captchaResponse"]
        else:
            formdata["captchaResponse"] = captcha_str
        login_resp = session.post(
            url=AUTHSERVER_URL, data=formdata, allow_redirects=False)

        def redirect_to_service():
            return session.get(url=login_resp.headers['Location'], allow_redirects=False)

        if login_resp.status_code != 302:
            parser = LoginedPageParser(login_resp.status_code)
            parser.feed(login_resp.text)

            if parser._kick:  # pylint: ignore disable=protected-access
                def kick():
                    nonlocal login_resp
                    # pylint: ignore disable=protected-access
                    login_resp = session.post(
                        url=AUTHSERVER_URL,
                        data={"execution": parser._kick_execution,
                              "_eventId": "continue"},
                        allow_redirects=False,
                        timeout=timeout)
                    return redirect_to_service()

                if kick_others:
                    return kick()
                else:
                    def cancel():
                        # pylint: ignore disable=protected-access
                        return session.post(
                            url=AUTHSERVER_URL,
                            data={"execution": parser._cancel_execution,
                                  "_eventId": "cancel"},
                            allow_redirects=False,
                            timeout=timeout)
                    raise MultiSessionConflict(kick=kick, cancel=cancel)
            raise UnknownAuthserverException(
                f"status code {login_resp.status_code} is got (302 expected) when sending login post, "
                "but can not find the element span.login_auth_error#msg")
        return redirect_to_service()

    captcha_str = None
    if session.get(AUTHSERVER_CAPTCHA_DETERMINE_URL, params={"username": username}).text == "true":
        captcha_img_resp = session.get(AUTHSERVER_CAPTCHA_IMAGE_URL)
        if captcha_callback is None:
            raise NeedCaptcha(captcha_img_resp.content,
                              captcha_img_resp.headers["Content-Type"],
                              after_captcha)
        captcha_str = captcha_callback(
            captcha_img_resp.content, captcha_img_resp.headers["Content-Type"])
        if captcha_str is None:
            raise NeedCaptcha(captcha_img_resp.content,
                              captcha_img_resp.headers["Content-Type"],
                              after_captcha)
    return after_captcha(captcha_str)
