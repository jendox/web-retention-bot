import uuid
from datetime import time

from app.use_cases.register_master import default_weekly_schedule_rules


def test_default_weekly_schedule_rules_are_weekdays_10_to_18():
    master_id = uuid.uuid4()

    rules = default_weekly_schedule_rules(master_id)

    assert [(rule.weekday, rule.start_time, rule.end_time) for rule in rules] == [
        (0, time(10, 0), time(18, 0)),
        (1, time(10, 0), time(18, 0)),
        (2, time(10, 0), time(18, 0)),
        (3, time(10, 0), time(18, 0)),
        (4, time(10, 0), time(18, 0)),
    ]
    assert {rule.master_id for rule in rules} == {master_id}
