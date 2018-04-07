#!/usr/bin/python3
#coding: utf-8


import pymysql
from web.modules import DataBase


db = DataBase()
fetch_all_menus_sql = 'select * from `menus`'
fetch_all_menu_names_sql = 'select `name` from `menus`'
fetch_by_key_sql = "select * from `menus` where `{key}` = '{value}'"
fetch_by_keys_sql = "select * from `menus` where `flavor` like '{flavor_value}' \
                    and `need_time` like '{need_time_value}' and `easiness` like '{easiness_value}'"

menu_dict_example = {
    'name': 'dish_name',
    'ingredients': 'dish_ingredients',
    'ingredientsReply': 'reply sentence of ingredients',
    'steps': {'stepA': 'this is step A'},
    'energy': 'energy',
    'protein': 'protein',
    'axunge': 'axunge',
    'pungency': 'pungency',
    'salt': 'salt',
    'vegetable': 'vegetable'
}


def _to_dict(data):

    """ pack data from database as a dict like `menu_dict_example` """

    menu = {}
    menu['name'] = data[1]  # 菜名
    menu['flavor'] = data[2]  # 口味
    menu['method'] = data[3]  # 工艺
    menu['need_time'] = data[4]  # 时间
    menu['easiness'] = data[5]  # 难度
    menu['steps'] = data[6][1:].strip().split('#')  # 详细步骤
    menu['ingredients'] = data[7].strip().split('#')  # 详细材料
    menu['ingredients'] = {
        one.split(':')[0]: one.split(':')[1]
        for one in menu['ingredients'] if one
    }
    menu['ingredientsReply'] = '、'.join(data[7].strip().split('#'))
    menu['energy'] = data[8] #能量
    menu['protein'] = data[9] #蛋白质
    menu['axunge'] = data[10] #脂肪
    menu['pungency'] = data[11] #辛辣
    menu['salt'] = data[12] #咸味
    menu['vegetable'] = data[13] #蔬果
    return menu


def get_existed_menus():
    menu_names = db.query_all(fetch_all_menu_names_sql)
    return [menu_name[0] for menu_name in menu_names]

def get_menu(dish):
    menus = db.query_all(fetch_by_key_sql.format(key = 'name',value = dish))
    return _to_dict(menus[0])

def get_step_index_in_menu(dish, step):
    menu = get_menu(dish)
    if step in menu['steps']:
        return menu['steps'].index(step)
    else:
        return -1

def get_attributes(flavor_value = '%',need_time_value = '%',easiness_value = '%'):
    fetch_menus = db.query_all(fetch_by_keys_sql.format(flavor_value = flavor_value,need_time_value =\
                                                    need_time_value,easiness_value = easiness_value))
    menus = []
    for fetch_menu in fetch_menus:      
        menu = {'dish':'','flavor':'',  'need_time':'',  'easiness':''}
        menu['dish'] = _to_dict(fetch_menu)['name']
        menu['flavor'] = _to_dict(fetch_menu)['flavor']
        menu['need_time'] = _to_dict(fetch_menu)['need_time']
        menu['easiness'] = _to_dict(fetch_menu)['easiness']
        menus.append(menu)
    return menus
