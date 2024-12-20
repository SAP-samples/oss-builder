from enum import Enum
from vuln_stream import vuln_stream
import os
import time

# Make sure that there is no '-' in any of the names
class Event(Enum):
    AFFECTED_NOT_SIZE_ONE = 1
    NO_RANGE = 2
    MULTIPLE_RANGES = 3
    MULTIPLE_FIXED = 4
    NOT_FIXED = 5
    NOT_GIT = 6
    NO_SOURCE_CHANGE = 7
    MULTIPLE_CHANGES = 8
    GIT_EXTRACTION_ERROR = 9
    BUILD_ERROR = 10


def record_event(event: Event, report_id: str) -> None:
    log_file = os.path.join(vuln_stream.vulnerability_dir, '../', 'events/',
                            event.name + '-' + report_id + '.txt')
    print(f'Event {event.name} for report {report_id}')
    with open (log_file, 'w') as f:
        f.write(f'{time.time()}\n')
        f.write(f'{event.name}\n')


def has_previous_error(report_id: str) -> bool:
    log_path = os.path.join(vuln_stream.vulnerability_dir, '../', 'events/') 
    os.listdir(log_path)
    return any(report_id in log for log in os.listdir(log_path))
