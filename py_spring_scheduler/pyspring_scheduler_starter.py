from functools import partial

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger
from py_spring_core import Properties, PySpringStarter

from py_spring_scheduler._schedule import JobRegistry, ScheduledJob


class SchedulerProperties(Properties):
    """
    Attributes:
        number_of_workers: Number of threads to use for the scheduler.
        max_instances: Prevents overlapping job execution. If a job is still running and the trigger fires again, a fourth instance is blocked.
        timezone: Timezone used for all jobs and triggers.
        coalesce: If the scheduler was down and multiple runs were missed, it will run them all upon resume.
    """

    __key__ = "scheduler"
    number_of_workers: int = 20
    max_instances: int = 3
    timezone: str = "UTC"
    coalesce: bool = False


class PySpringSchedulerStarter(PySpringStarter):
    def on_configure(self) -> None:
        self.properties_classes.append(SchedulerProperties)

    def _create_scheduler(self, props: SchedulerProperties) -> BackgroundScheduler:
        return BackgroundScheduler(
            {
                "apscheduler.executors.default": {
                    "class": "apscheduler.executors.pool:ThreadPoolExecutor",
                    "max_workers": props.number_of_workers,
                },
                "apscheduler.job_defaults.coalesce": props.coalesce,
                "apscheduler.job_defaults.max_instances": props.max_instances,
                "apscheduler.timezone": props.timezone,
            }
        )

    def on_initialized(self) -> None:
        assert self.app_context is not None, "ApplicationContext is not set"
        logger.info("Initializing scheduler...")
        props = self.app_context.get_properties(SchedulerProperties)
        assert props is not None, "SchedulerProperties not found in ApplicationContext"
        logger.info(f"Scheduler properties: {props.model_dump_json()}")

        self.scheduler = self._create_scheduler(props)
        logger.info("Scheduler created...")

        self.component_instance_map = {
            component.get_name(): component
            for component in self.app_context.get_singleton_component_instances()
        }

        for job in JobRegistry.drain_jobs():
            self.bind_job(job)

        self.scheduler.start()
        logger.info("Scheduler initialized")

    def bind_job(self, job: ScheduledJob) -> None:
        logger.info(f"Binding job {job.full_name} with trigger {job.trigger}")
        instance = self.component_instance_map.get(job.class_name)
        if not job.is_regular_function and instance is None:
            raise ValueError(f"Component {job.class_name} not found")

        if job.is_regular_function:
            job_func = job.func
        else:
            job_func = partial(job.func, instance)

        self.scheduler.add_job(job_func, job.trigger)


def provide_scheduler() -> PySpringSchedulerStarter:
    return PySpringSchedulerStarter()
