"""Keep expensive explanation/replay work bounded on the small web instance."""
from threading import Lock

model_task_lock = Lock()
