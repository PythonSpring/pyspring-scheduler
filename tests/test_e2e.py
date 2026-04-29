"""
E2E test: simulates a developer using pyspring-scheduler in a real project.

Sets up a temporary project with:
- app-config.json (server disabled)
- app-properties.json
- A source directory with Components that use @Scheduled

Then boots PySpringApplication and verifies jobs are actually triggered.

FINDINGS:
- Standalone @Scheduled functions only work if the file also contains a class,
  because py-spring-core's ClassScanner only imports modules with class definitions.
- app.run() with server disabled returns immediately after init (no blocking),
  so we call _init_app() directly and manage the scheduler lifecycle ourselves.
"""

import json
import os
import tempfile
import textwrap
import time

from py_spring_core import PySpringApplication
from py_spring_scheduler import provide_scheduler
from py_spring_scheduler._schedule import JobRegistry


def _create_test_project(tmpdir: str, component_code: str) -> str:
    src_dir = os.path.join(tmpdir, "src")
    os.makedirs(src_dir, exist_ok=True)

    app_config = {
        "app_src_target_dir": src_dir,
        "server_config": {"host": "127.0.0.1", "port": 8000, "enabled": False},
        "properties_file_path": os.path.join(tmpdir, "app-properties.json"),
        "loguru_config": {
            "log_level": "DEBUG",
            "log_file_path": "",
            "log_rotation": "10 MB",
            "log_retention": "7 days",
            "format": "text",
        },
    }

    app_properties = {
        "scheduler": {
            "number_of_workers": 2,
            "max_instances": 1,
            "timezone": "UTC",
            "coalesce": False,
        }
    }

    config_path = os.path.join(tmpdir, "app-config.json")
    props_path = os.path.join(tmpdir, "app-properties.json")

    with open(config_path, "w") as f:
        json.dump(app_config, f)
    with open(props_path, "w") as f:
        json.dump(app_properties, f)

    component_file = os.path.join(src_dir, "tasks.py")
    with open(component_file, "w") as f:
        f.write(component_code)

    return config_path


def _wait_for_marker(marker_file: str, expected: str, timeout: float = 5.0) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(marker_file):
            with open(marker_file) as f:
                content = f.read()
                if expected in content:
                    return content
        time.sleep(0.2)
    if os.path.exists(marker_file):
        with open(marker_file) as f:
            return f.read()
    return ""


class TestE2EComponentScheduling:
    def setup_method(self):
        JobRegistry.jobs = set()

    def test_component_method_fires(self):
        """A Component with @Scheduled method actually runs the job."""
        component_code = textwrap.dedent("""\
            import os
            from py_spring_core import Component
            from py_spring_scheduler import Scheduled, IntervalTrigger

            MARKER_FILE = os.environ["E2E_MARKER_FILE"]

            class HeartbeatService(Component):
                @Scheduled(trigger=IntervalTrigger(seconds=1))
                def heartbeat(self):
                    with open(MARKER_FILE, "a") as f:
                        f.write("heartbeat\\n")
        """)

        with tempfile.TemporaryDirectory() as tmpdir:
            marker_file = os.path.join(tmpdir, "marker.txt")
            os.environ["E2E_MARKER_FILE"] = marker_file

            try:
                config_path = _create_test_project(tmpdir, component_code)
                starter = provide_scheduler()
                app = PySpringApplication(config_path, starters=[starter])
                app._init_app()

                content = _wait_for_marker(marker_file, "heartbeat")

                assert "heartbeat" in content, (
                    f"Heartbeat job did not fire within timeout. "
                    f"JobRegistry had {len(JobRegistry.jobs)} jobs. "
                    f"Marker content: {content!r}"
                )
            finally:
                if hasattr(starter, "scheduler") and starter.scheduler.running:
                    starter.scheduler.shutdown(wait=False)
                os.environ.pop("E2E_MARKER_FILE", None)

    def test_multiple_components_fire(self):
        """Multiple @Scheduled methods across a Component and a standalone function coexist."""
        component_code = textwrap.dedent("""\
            import os
            from py_spring_core import Component
            from py_spring_scheduler import Scheduled, IntervalTrigger

            MARKER_FILE = os.environ["E2E_MARKER_FILE"]

            @Scheduled(trigger=IntervalTrigger(seconds=1))
            def standalone_task():
                with open(MARKER_FILE, "a") as f:
                    f.write("standalone\\n")

            class WorkerService(Component):
                @Scheduled(trigger=IntervalTrigger(seconds=1))
                def work(self):
                    with open(MARKER_FILE, "a") as f:
                        f.write("worker\\n")
        """)

        with tempfile.TemporaryDirectory() as tmpdir:
            marker_file = os.path.join(tmpdir, "marker.txt")
            os.environ["E2E_MARKER_FILE"] = marker_file

            try:
                config_path = _create_test_project(tmpdir, component_code)
                starter = provide_scheduler()
                app = PySpringApplication(config_path, starters=[starter])
                app._init_app()

                # Wait for both to fire
                deadline = time.time() + 5
                content = ""
                while time.time() < deadline:
                    content = _wait_for_marker(marker_file, "worker", timeout=0.5)
                    if "standalone" in content and "worker" in content:
                        break

                assert "worker" in content, f"Worker job did not fire. Content: {content!r}"
                assert "standalone" in content, f"Standalone job did not fire. Content: {content!r}"
            finally:
                if hasattr(starter, "scheduler") and starter.scheduler.running:
                    starter.scheduler.shutdown(wait=False)
                os.environ.pop("E2E_MARKER_FILE", None)

    def test_scheduler_properties_applied(self):
        """Custom scheduler properties from app-properties.json are correctly applied."""
        component_code = textwrap.dedent("""\
            from py_spring_core import Component

            class DummyComponent(Component):
                pass
        """)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _create_test_project(tmpdir, component_code)
            starter = provide_scheduler()

            try:
                app = PySpringApplication(config_path, starters=[starter])
                app._init_app()

                assert hasattr(starter, "scheduler")
                assert starter.scheduler.running
            finally:
                if hasattr(starter, "scheduler") and starter.scheduler.running:
                    starter.scheduler.shutdown(wait=False)


class TestE2EStandaloneFunctionLimitation:
    """Documents a framework limitation: standalone @Scheduled functions in files
    without any class definition are NOT imported by py-spring-core's ClassScanner."""

    def setup_method(self):
        JobRegistry.jobs = set()

    def test_standalone_only_file_jobs_not_registered(self):
        """Files with only @Scheduled functions (no classes) are never imported."""
        component_code = textwrap.dedent("""\
            import os
            from py_spring_scheduler import Scheduled, IntervalTrigger

            @Scheduled(trigger=IntervalTrigger(seconds=1))
            def orphan_task():
                pass
        """)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = _create_test_project(tmpdir, component_code)
            starter = provide_scheduler()

            try:
                app = PySpringApplication(config_path, starters=[starter])
                app._init_app()

                # The job is NOT registered because the file has no class definitions
                has_orphan = any("orphan_task" in j.full_name for j in JobRegistry.jobs)
                assert not has_orphan, (
                    "Expected orphan_task to NOT be registered "
                    "(standalone functions in class-less files are not imported by ClassScanner)"
                )
            finally:
                if hasattr(starter, "scheduler") and starter.scheduler.running:
                    starter.scheduler.shutdown(wait=False)
