from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import date, time

from pydantic import BaseModel

from .invigilator import Invigilator
from ..tools import get_exam_raw, async_get_exam_raw
from ...course import Course
from ...utils.datetimes import date_from_str, time_from_str
from ...utils.request_transformer import Request


__all__ = ['Exam']


class Exam(BaseModel):
    """考试信息
    """
    course: Course
    """考试对应的课程，其中学分 :attr:`credit`、教师 :attr:`instructor`、教学班号 :attr:`course_num` 可能无法获取（其值会设置为 :obj:`None`）"""
    batch: str
    """考试批次，如 :obj:`"非集中考试周"`"""
    batch_id: int
    """选课系统中考试批次的内部id"""
    building: str
    """考场楼栋"""
    floor: Optional[int] = None
    """考场楼层"""
    room: str
    """考场地点"""
    stu_num: int
    """考场人数"""
    date: date
    """考试日期"""
    start_time: time
    """考试开始时间"""
    end_time: time
    """考试结束时间"""
    week: int
    """周次"""
    weekday: int
    """星期，0为周一，6为周日"""
    stu_id: str
    """考生学号"""
    seat_num: int
    """考生座号"""
    chief_invi: List[Invigilator]
    """监考员"""
    asst_invi: Optional[List[Invigilator]] = None
    """副监考员"""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Exam:
        """从反序列化后的 json 数据中的一次考试数据生成 :class:`Exam` 对象

        :param data: 反序列化后的 json 数据中的一次考试数据
        :type data: Dict[str, Any]
        :return: 对应的 :class:`Exam` 对象
        :rtype: [type]
        """
        course = Course.from_dict(data)
        return Exam(
            course=course,
            batch=data["batchName"],
            batch_id=data["batchId"],
            building=data["buildingName"],
            room=data["roomName"],
            floor=data["floorNum"] if data["floorNum"] != "null" else None,
            date=date_from_str(data["examDate"]),
            start_time=time_from_str(data["startTime"]),
            end_time=time_from_str(data["endTime"]),
            week=data["week"],
            weekday=int(data["weekDay"]) - 1,
            stu_id=data["studentId"],
            seat_num=data["seatNum"],
            stu_num=data["examStuNum"],
            chief_invi=[Invigilator.from_dict(invi)
                        for invi in data["simpleChiefinvigilatorVOS"]]
            if data['simpleChiefinvigilatorVOS'] is not None else [],
            asst_invi=data["simpleAssistantInviVOS"] and ([Invigilator.from_dict(invi)
                                                           for invi in data["simpleAssistantInviVOS"]]
                                                          if data['simpleAssistantInviVOS'] is not None else [])
        )

    @staticmethod
    def fetch(session: Request, student_id: str) -> List[Exam]:
        """从 my.cqu.edu.cn 上获取指定学生的考表

        :param session: 登陆后获取的 authorization 或者调用过 :func:`.mycqu.access_mycqu` 的 Session
        :type session: Request
        :param student_id: 学生学号
        :type student_id: str
        :return: 本学期的考表
        :rtype: List[Exam]
        """
        return [Exam.from_dict(exam)
                for exam in get_exam_raw(student_id, session)["data"]]

    @staticmethod
    async def async_fetch(session: Request, student_id: str) -> List[Exam]:
        """从 my.cqu.edu.cn 上获取指定学生的考表

        :param session: 登陆后获取的 authorization 或者调用过 :func:`.mycqu.access_mycqu` 的 Session
        :type session: Request
        :param student_id: 学生学号
        :type student_id: str
        :return: 本学期的考表
        :rtype: List[Exam]
        """
        return [Exam.from_dict(exam)
                for exam in (await async_get_exam_raw(session, student_id))["data"]]
