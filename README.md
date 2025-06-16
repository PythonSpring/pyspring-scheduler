# PySpring Scheduler

A Python-based scheduling library that integrates with the PySpring framework, providing a robust and flexible way to manage scheduled tasks in your applications.

## Features

- Seamless integration with PySpring framework
- Background task scheduling using APScheduler
- Configurable thread pool for job execution
- Support for timezone-aware scheduling
- Job coalescing to handle missed executions
- Maximum instance limits to prevent overlapping executions
- Component-based job registration and management
- Multiple trigger types (Interval, Cron, Date)

## Requirements

- Python >= 3.11, < 3.13
- py-spring-core >= 0.0.10
- apscheduler >= 3.11.0

## Installation

```bash
pip install pyspring-scheduler
```

## Configuration

The scheduler can be configured through the application properties. Here's an example configuration:

```json
{
    "scheduler": {
        "number_of_workers": 20,
        "max_instances": 3,
        "timezone": "UTC",
        "coalesce": false
    }
}
```

### Configuration Options

- `number_of_workers`: Number of threads to use for the scheduler
- `max_instances`: Prevents overlapping job execution. If a job is still running and the trigger fires again, additional instances are blocked
- `timezone`: Timezone used for all jobs and triggers
- `coalesce`: If the scheduler was down and multiple runs were missed, it will run them all upon resume

## Usage

1. Initialize the scheduler in your application:

```python
from py_spring_core import PySpringApplication
from pyspring_scheduler.pyspring_scheduler_provider import provide_scheduler

def main():
    app = PySpringApplication("./app-config.json", entity_providers=[provide_scheduler()])
    app.run()

if __name__ == "__main__":
    main()
```

2. Define scheduled jobs using the `@Scheduled` decorator with different trigger types:

### Interval Trigger
Run a task at fixed intervals:

```python
from pyspring_scheduler import Scheduled, IntervalTrigger

@Scheduled(trigger=IntervalTrigger(seconds=5))
def my_interval_task():
    # Runs every 5 seconds
    pass
```

### Cron Trigger
Run a task based on cron expressions:

```python
from pyspring_scheduler import Scheduled, CronTrigger

@Scheduled(trigger=CronTrigger(cron="0 0 * * *"))
def my_cron_task():
    # Runs daily at midnight
    pass
```

### Component-based Scheduling
You can also schedule methods within components:

```python
from py_spring_core import Component
from pyspring_scheduler import Scheduled, IntervalTrigger

class MyComponent(Component):
    @Scheduled(trigger=IntervalTrigger(seconds=3))
    def scheduled_method(self):
        # Runs every 3 seconds
        pass
```

### Component Dependencies
Components can be injected and used within scheduled tasks:

```python
from py_spring_core import Component
from pyspring_scheduler import Scheduled, IntervalTrigger

class Service(Component):
    def do_something(self):
        print("Service method called")

class TaskComponent(Component):
    service: Service  # Dependency injection

    @Scheduled(trigger=IntervalTrigger(seconds=5))
    def scheduled_task(self):
        self.service.do_something()
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.