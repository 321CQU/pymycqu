from __future__ import annotations

import re
from typing import List, Optional, ClassVar, Tuple

from pydantic import BaseModel

from ...course import CourseDayTime
from ...utils.datetimes import parse_weekday_str, parse_period_str, parse_weeks_str
from ...utils.period import Period


__all__ = ['EnrollCourseTimetable']

WEEKS_RE = re.compile("^(.*)周")
PERIOD_RE = re.compile("星期. [0-9]-[0-9]小节")
POS_RE = re.compile("&(.*)$")


class EnrollCourseTimetable(BaseModel):
    """
    可选具体课程上课时间、上课地点信息
    """
    weeks: List[Period]
    """上课周数"""
    time: Optional[CourseDayTime] = None
    """上课时间"""
    pos: Optional[str] = None
    """上课地点"""

    @staticmethod
    def from_str(data: str) -> List[EnrollCourseTimetable]:
        """从字符串中生成具体待选课程上课时间信息
        示例字符串"1-5,7-9周 星期二 6-7小节 &D1144 ;1-5,7-9周 星期五 3-4小节 &D1143 "

        :param data: 需提取信息的字符串
        :type data: str
        :return: 返回待选课程上课时间信息当列表
        :rtype: List[EnrollCourseTimetable]
        """
        items = data.split(';')
        result = []

        for item in items:
            pos_str = POS_RE.search(item)
            pos = None
            if pos_str:
                pos = pos_str.group().strip()[1:]

            period_str = PERIOD_RE.search(item)
            timetable = None
            if period_str:
                period_str = period_str.group()
                timetable = CourseDayTime(
                    weekday=parse_weekday_str(period_str[:3]),
                    period=parse_period_str(period_str[4:-2])
                )

            result.append(
                EnrollCourseTimetable(
                    weeks=parse_weeks_str(WEEKS_RE.search(item).group()[:-1]),
                    time=timetable,
                    pos=pos
                )
            )

        return result