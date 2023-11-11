from __future__ import annotations

from typing import Any, Dict, Tuple, List
from pydantic import BaseModel

from ...utils.datetimes import parse_period_str, parse_weeks_str
from ...utils.period import Period

__all__ = ['RoomActivityInfo']


class RoomActivityInfo(BaseModel):
    """教室活动的公有属性"""
    period: Period
    """占用节数"""
    weeks: List[Period]
    """行课周数，列表中每个元组 (a,b) 代表一个周数范围 a~b（包含 a, b），在单独的一周则有 b=a"""
    weekday: int
    """星期，0 为周一，6 为周日，此与 :attr:`datetime.date.day` 一致"""

    @staticmethod
    def from_dict(data: Dict[str, Any]):
        """从反序列化的一个活动信息 json 中生成RoomActivityInfo对象

        :param data: 反序列化成字典的活动 json
        :type data: Dict[str, Any]
        :return: 教室活动
        :rtype: RoomActivityInfo
        """
        return RoomActivityInfo(
            period=parse_period_str(data['periodFormat']),
            weeks=parse_weeks_str(data['teachingWeekFormat']),
            weekday=int(data['weekDay']) - 1
        )