"""
To store all the constants of the projects.
"""
import datetime
from enum import Enum

now = datetime.datetime.utcnow
utf8mb4_name_length = 191
name_length = 255
password_length = 255
description_length = 5000
text_length = 65535
mediumtext_length = 10485760
url_length = 2083
datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"


class TaskRunStatus(Enum):
    RUNNING = 0
    SUCCESS = 1
    FAILURE = 2


class PipelineStatus(Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    SUCCESS = "Success"
    FAILURE = "Failure"
