"""
成绩相关模块
"""
from __future__ import annotations
import requests
from requests import Session
import json
from typing import Dict, Any, Union, Optional, List
from ._lib_wrapper.dataclass import dataclass
from .course import Course, CQUSession

__all__ = ("Score",)


def get_score_raw(auth: Union[Session, str]):
    """
    获取学生原始成绩
    :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
    :type auth: Union[Session, str]
    :return: 反序列化获取的score列表
    :rtype: Dict
    """
    if isinstance(auth, requests.Session):
        res = auth.get('http://my.cqu.edu.cn/api/sam/score/student/score')
        return json.loads(res.content)['data']
    else:
        authorization = auth
        headers = {
            'Referer': 'https://my.cqu.edu.cn/sam/home',
            'User-Agent': 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
            'Authorization': authorization
        }
        res = requests.get('http://my.cqu.edu.cn/api/sam/score/student/score', headers=headers)
        return json.loads(res.content)['data']


@dataclass
class Score:
    """
    成绩对象
    """
    session: CQUSession
    """学期"""
    course: Course
    """课程"""
    score: Optional[str]
    """成绩，可能为数字，也可能为字符（优、良等）"""
    study_nature: str
    """初修/重修"""
    course_nature: str
    """必修/选修"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Score:
        """
        从反序列化的字典生成Score对象

        @param: data
        @type: dict
        @return: 返回成绩对象
        @rtype: Score
        """
        return Score(
            session=CQUSession.from_str(data["sessionName"]),
            course=Course.from_dict(data),
            score=data['effectiveScoreShow'],
            study_nature=data['studyNature'],
            course_nature=data['courseNature']
        )

    @staticmethod
    def fetch(auth: Union[str, Session]) -> List[Score]:
        """
        从网站获取成绩信息
        :param auth: 登陆后获取的authorization或者调用过mycqu.access_mycqu的session
        :type auth: Union[Session, str]
        :return: 返回成绩对象
        :rtype: List[Score]
        """
        temp = get_score_raw(auth)
        score = []
        for term, courses in temp.items():
            for course in courses:
                score.append(Score.from_dict(course))
        return score
