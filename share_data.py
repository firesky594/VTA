from enum import Enum


class CURRENT_STATUS(Enum):
    normal = 'normal'
    fight = 'fight'
    talk = 'talk'


SHARED_DATA_TEMPLATE = {
    'shutdown': False,
    # 显示的帧
    'display_frame': None,
    'processed_frame': None,
    'game_frame': None,
}


def update_nested_dict(shared_dict, root_key, sub_key, value):
    """
    安全更新嵌套字典的工具函数
    manager.dict 的子字典修改必须重新赋值才能跨进程同步
    """
    temp = shared_dict[root_key]
    temp[sub_key] = value
    shared_dict[root_key] = temp
