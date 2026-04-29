from functools import partial
from unittest.mock import MagicMock, patch

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from py_spring_scheduler._schedule import JobRegistry, ScheduledJob
from py_spring_scheduler.pyspring_scheduler_starter import (
    PySpringSchedulerStarter,
    SchedulerProperties,
    provide_scheduler,
)


class TestSchedulerProperties:
    def test_default_values(self):
        props = SchedulerProperties()
        assert props.number_of_workers == 20
        assert props.max_instances == 3
        assert props.timezone == "UTC"
        assert props.coalesce is False

    def test_custom_values(self):
        props = SchedulerProperties(
            number_of_workers=10,
            max_instances=5,
            timezone="Asia/Taipei",
            coalesce=True,
        )
        assert props.number_of_workers == 10
        assert props.max_instances == 5
        assert props.timezone == "Asia/Taipei"
        assert props.coalesce is True

    def test_key_is_scheduler(self):
        assert SchedulerProperties.__key__ == "scheduler"

    def test_serializable_to_json(self):
        props = SchedulerProperties()
        json_str = props.model_dump_json()
        assert "number_of_workers" in json_str
        assert "max_instances" in json_str


class TestPySpringSchedulerStarter:
    def test_on_configure_registers_properties(self):
        starter = PySpringSchedulerStarter()
        starter.on_configure()
        assert SchedulerProperties in starter.properties_classes

    def test_create_scheduler_returns_background_scheduler(self):
        starter = PySpringSchedulerStarter()
        props = SchedulerProperties()
        scheduler = starter._create_scheduler(props)
        assert isinstance(scheduler, BackgroundScheduler)

    def test_bind_job_regular_function(self):
        starter = PySpringSchedulerStarter()
        starter.scheduler = MagicMock(spec=BackgroundScheduler)
        starter.component_instance_map = {}

        def my_func():
            return "hello"

        trigger = IntervalTrigger(seconds=5)
        job = ScheduledJob(
            trigger=trigger,
            class_name="",
            file_path="/test.py",
            full_name="/test.py:my_func",
            func=my_func,
            is_regular_function=True,
        )

        starter.bind_job(job)
        starter.scheduler.add_job.assert_called_once_with(my_func, trigger)

    def test_bind_job_class_method_with_instance(self):
        starter = PySpringSchedulerStarter()
        starter.scheduler = MagicMock(spec=BackgroundScheduler)

        class FakeComponent:
            def run(self):
                return "ran"

        instance = FakeComponent()
        starter.component_instance_map = {"FakeComponent": instance}

        trigger = IntervalTrigger(seconds=3)
        job = ScheduledJob(
            trigger=trigger,
            class_name="FakeComponent",
            file_path="/test.py",
            full_name="/test.py:FakeComponent.run",
            func=FakeComponent.run,
            is_regular_function=False,
        )

        starter.bind_job(job)
        starter.scheduler.add_job.assert_called_once()
        bound_func = starter.scheduler.add_job.call_args[0][0]
        assert isinstance(bound_func, partial)

    def test_bind_job_class_method_missing_component_raises(self):
        starter = PySpringSchedulerStarter()
        starter.scheduler = MagicMock(spec=BackgroundScheduler)
        starter.component_instance_map = {}

        trigger = IntervalTrigger(seconds=3)
        job = ScheduledJob(
            trigger=trigger,
            class_name="MissingComponent",
            file_path="/test.py",
            full_name="/test.py:MissingComponent.run",
            func=lambda self: None,
            is_regular_function=False,
        )

        try:
            starter.bind_job(job)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "MissingComponent" in str(e)

    def test_on_initialized_starts_scheduler(self):
        starter = PySpringSchedulerStarter()
        JobRegistry.jobs = set()

        mock_context = MagicMock()
        mock_context.get_properties.return_value = SchedulerProperties()
        mock_context.get_singleton_component_instances.return_value = []
        starter.app_context = mock_context

        starter.on_initialized()

        assert hasattr(starter, "scheduler")
        assert isinstance(starter.scheduler, BackgroundScheduler)
        assert starter.scheduler.running

        starter.scheduler.shutdown(wait=False)

    def test_on_initialized_without_context_raises(self):
        starter = PySpringSchedulerStarter()
        starter.app_context = None

        try:
            starter.on_initialized()
            assert False, "Should have raised AssertionError"
        except AssertionError:
            pass


class TestProvideScheduler:
    def test_returns_starter_instance(self):
        starter = provide_scheduler()
        assert isinstance(starter, PySpringSchedulerStarter)

    def test_returns_new_instance_each_call(self):
        a = provide_scheduler()
        b = provide_scheduler()
        assert a is not b


class TestPackageImports:
    def test_scheduled_importable(self):
        from py_spring_scheduler import Scheduled
        assert callable(Scheduled)

    def test_provide_scheduler_importable(self):
        from py_spring_scheduler import provide_scheduler
        assert callable(provide_scheduler)

    def test_starter_class_importable(self):
        from py_spring_scheduler import PySpringSchedulerStarter
        assert PySpringSchedulerStarter is not None

    def test_properties_importable(self):
        from py_spring_scheduler import SchedulerProperties
        assert SchedulerProperties is not None

    def test_interval_trigger_importable(self):
        from py_spring_scheduler import IntervalTrigger
        assert IntervalTrigger is not None

    def test_cron_trigger_importable(self):
        from py_spring_scheduler import CronTrigger
        assert CronTrigger is not None

    def test_date_trigger_importable(self):
        from py_spring_scheduler import DateTrigger
        assert DateTrigger is not None

    def test_calendar_interval_trigger_importable(self):
        from py_spring_scheduler import CalendarIntervalTrigger
        assert CalendarIntervalTrigger is not None

    def test_and_trigger_importable(self):
        from py_spring_scheduler import AndTrigger
        assert AndTrigger is not None

    def test_or_trigger_importable(self):
        from py_spring_scheduler import OrTrigger
        assert OrTrigger is not None
