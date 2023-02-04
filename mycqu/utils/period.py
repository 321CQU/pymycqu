from pydantic import BaseModel


__all__ = ['Period']

class Period(BaseModel):
    start: int
    end: int
