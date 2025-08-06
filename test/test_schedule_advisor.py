import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from core.agents import ScheduleAdvisor

def test_advise_schedule_thu7_9h():
    advisor = ScheduleAdvisor()
    result = advisor.advise_schedule('tôi muốn hẹn vào 9h thứ 7 tuần này')
    assert result['status'] == 'success'
    assert 'Saturday' in result['main_suggestion']
    assert '09:00' in result['main_suggestion']

def test_advise_schedule_thu2_14h():
    advisor = ScheduleAdvisor()
    result = advisor.advise_schedule('họp vào thứ 2 lúc 14h')
    # Nếu ngày là quá khứ thì phải trả về need_more_info
    if result['status'] == 'success':
        assert 'Monday' in result['main_suggestion']
        assert '14:00' in result['main_suggestion']
    else:
        assert result['status'] == 'need_more_info'
        assert 'Không nhận diện được thời gian cụ thể' in result['main_suggestion']

def test_advise_schedule_no_time():
    advisor = ScheduleAdvisor()
    result = advisor.advise_schedule('họp với lập trình viên Long')
    assert result['status'] == 'need_more_info'
    assert 'Không nhận diện được thời gian cụ thể' in result['main_suggestion']
