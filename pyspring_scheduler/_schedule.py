from functools import wraps
from typing import Callable, Any
from apscheduler.triggers.base import BaseTrigger

from loguru import logger
from pydantic import BaseModel, ConfigDict


class ScheduledJob(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    trigger: BaseTrigger
    class_name: str
    full_name: str
    func: Callable[..., Any]
    is_regular_function: bool

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ScheduledJob):
            return self.full_name == other.full_name
        return False
    
    def __hash__(self) -> int:
        return hash(self.full_name)


class JobRegistry:
    jobs: set[ScheduledJob] = set()

def Scheduled(trigger: BaseTrigger) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        func_repr = func.__qualname__.split(".")
        
        class_name = ""
        is_regular_function = True
        if len(func_repr) == 2: # class member function
            class_name = func_repr[0]
            is_regular_function = False

        logger.info(f"Scheduling job {func.__name__} with trigger {trigger}")
        job = ScheduledJob(
            trigger=trigger, 
            class_name=class_name, 
            full_name=f"{class_name}.{func.__name__}", 
            func= wrapper,
            is_regular_function=is_regular_function
        )
        if job not in JobRegistry.jobs:
            JobRegistry.jobs.add(job)
        
        return wrapper
    return decorator