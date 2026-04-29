from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from py_spring_scheduler._schedule import JobRegistry, ScheduledJob, Scheduled


# Capture the module-level job before any test clears the registry
class _ModuleLevelComponent:
    @Scheduled(trigger=IntervalTrigger(seconds=3))
    def run_job(self):
        return "component_result"


_MODULE_LEVEL_JOB = next(
    (j for j in JobRegistry.jobs if "ModuleLevelComponent" in j.full_name), None
)


class TestScheduledDecoratorOnRegularFunction:
    def setup_method(self):
        JobRegistry.jobs = set()

    def test_registers_job_in_registry(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            pass

        assert len(JobRegistry.jobs) == 1

    def test_job_has_correct_function_name(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert "my_task" in job.full_name

    def test_job_is_marked_as_regular_function(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert job.is_regular_function is True

    def test_job_has_empty_class_name(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert job.class_name == ""

    def test_decorated_function_still_callable(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            return 42

        assert my_task() == 42

    def test_preserves_function_name(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            pass

        assert my_task.__name__ == "my_task"

    def test_job_stores_trigger(self):
        trigger = IntervalTrigger(seconds=10)

        @Scheduled(trigger=trigger)
        def my_task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert job.trigger is trigger

    def test_job_has_file_path(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def my_task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert job.file_path.endswith(".py")


class TestScheduledDecoratorOnClassMethod:
    """Tests class method detection via module-level class.

    FINDING: The decorator uses func.__qualname__.split(".") and checks
    len == 2 to detect class methods. This only works for module-level
    classes. Classes inside functions produce longer qualnames and are
    treated as regular functions.
    """

    def test_detects_class_name_for_module_level_class(self):
        assert _MODULE_LEVEL_JOB is not None
        assert _MODULE_LEVEL_JOB.class_name == "_ModuleLevelComponent"

    def test_module_level_class_not_marked_as_regular_function(self):
        assert _MODULE_LEVEL_JOB is not None
        assert _MODULE_LEVEL_JOB.is_regular_function is False

    def test_full_name_contains_class_and_method(self):
        assert _MODULE_LEVEL_JOB is not None
        assert "_ModuleLevelComponent.run_job" in _MODULE_LEVEL_JOB.full_name

    def test_nested_class_method_treated_as_regular_function(self):
        """Known limitation: classes inside functions are not detected."""
        JobRegistry.jobs = set()

        class NestedComponent:
            @Scheduled(trigger=IntervalTrigger(seconds=3))
            def run_job(self):
                pass

        job = next(iter(JobRegistry.jobs))
        assert job.is_regular_function is True
        assert job.class_name == ""


class TestScheduledWithDifferentTriggers:
    def setup_method(self):
        JobRegistry.jobs = set()

    def test_interval_trigger(self):
        @Scheduled(trigger=IntervalTrigger(seconds=5))
        def task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert isinstance(job.trigger, IntervalTrigger)

    def test_cron_trigger(self):
        @Scheduled(trigger=CronTrigger(hour=0, minute=0))
        def task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert isinstance(job.trigger, CronTrigger)

    def test_date_trigger(self):
        @Scheduled(trigger=DateTrigger(run_date="2030-01-01"))
        def task():
            pass

        job = next(iter(JobRegistry.jobs))
        assert isinstance(job.trigger, DateTrigger)
