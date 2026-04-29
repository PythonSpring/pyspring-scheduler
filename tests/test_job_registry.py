from apscheduler.triggers.interval import IntervalTrigger

from py_spring_scheduler._schedule import JobRegistry, ScheduledJob, Scheduled


class TestJobRegistry:
    def setup_method(self):
        JobRegistry.jobs = set()

    def test_starts_empty_after_clear(self):
        assert len(JobRegistry.jobs) == 0

    def test_accumulates_multiple_jobs(self):
        @Scheduled(trigger=IntervalTrigger(seconds=1))
        def task_a():
            pass

        @Scheduled(trigger=IntervalTrigger(seconds=2))
        def task_b():
            pass

        assert len(JobRegistry.jobs) == 2

    def test_deduplicates_same_function(self):
        trigger = IntervalTrigger(seconds=5)

        def my_task():
            pass

        job = ScheduledJob(
            trigger=trigger,
            class_name="",
            file_path="/fake/path.py",
            full_name="/fake/path.py:my_task",
            func=my_task,
            is_regular_function=True,
        )
        JobRegistry.jobs.add(job)
        JobRegistry.jobs.add(job)

        assert len(JobRegistry.jobs) == 1

    def test_two_jobs_with_same_full_name_are_equal(self):
        def func_a():
            pass

        def func_b():
            pass

        job_a = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="",
            file_path="/a.py",
            full_name="/shared:task",
            func=func_a,
            is_regular_function=True,
        )
        job_b = ScheduledJob(
            trigger=IntervalTrigger(seconds=2),
            class_name="",
            file_path="/b.py",
            full_name="/shared:task",
            func=func_b,
            is_regular_function=True,
        )
        assert job_a == job_b

    def test_two_jobs_with_different_full_name_are_not_equal(self):
        def func():
            pass

        job_a = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="",
            file_path="/a.py",
            full_name="/a.py:task_a",
            func=func,
            is_regular_function=True,
        )
        job_b = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="",
            file_path="/a.py",
            full_name="/a.py:task_b",
            func=func,
            is_regular_function=True,
        )
        assert job_a != job_b

    def test_jobs_is_a_set(self):
        assert isinstance(JobRegistry.jobs, set)

    def test_drain_jobs_returns_all_and_clears(self):
        @Scheduled(trigger=IntervalTrigger(seconds=1))
        def task_a():
            pass

        @Scheduled(trigger=IntervalTrigger(seconds=2))
        def task_b():
            pass

        assert len(JobRegistry.jobs) == 2
        drained = JobRegistry.drain_jobs()
        assert len(drained) == 2
        assert len(JobRegistry.jobs) == 0

    def test_drain_jobs_on_empty_registry(self):
        drained = JobRegistry.drain_jobs()
        assert len(drained) == 0
        assert len(JobRegistry.jobs) == 0


class TestScheduledJobModel:
    def test_equality_based_on_full_name(self):
        def func():
            pass

        job_a = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="A",
            file_path="/a.py",
            full_name="same_name",
            func=func,
            is_regular_function=True,
        )
        job_b = ScheduledJob(
            trigger=IntervalTrigger(seconds=99),
            class_name="B",
            file_path="/b.py",
            full_name="same_name",
            func=func,
            is_regular_function=False,
        )
        assert job_a == job_b

    def test_not_equal_to_non_scheduled_job(self):
        def func():
            pass

        job = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="",
            file_path="/a.py",
            full_name="test",
            func=func,
            is_regular_function=True,
        )
        assert job != "not a job"
        assert job != 42

    def test_hash_based_on_full_name(self):
        def func():
            pass

        job_a = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="",
            file_path="/a.py",
            full_name="same_name",
            func=func,
            is_regular_function=True,
        )
        job_b = ScheduledJob(
            trigger=IntervalTrigger(seconds=2),
            class_name="X",
            file_path="/b.py",
            full_name="same_name",
            func=func,
            is_regular_function=False,
        )
        assert hash(job_a) == hash(job_b)

    def test_model_is_frozen(self):
        def func():
            pass

        job = ScheduledJob(
            trigger=IntervalTrigger(seconds=1),
            class_name="",
            file_path="/a.py",
            full_name="test",
            func=func,
            is_regular_function=True,
        )
        try:
            job.class_name = "changed"
            assert False, "Should have raised ValidationError"
        except Exception:
            pass
