#!/usr/bin/python3
#coding: utf-8


import pymysql
from web.modules import DataBase


db = DataBase()
fetch_all_menus_sql = 'select * from `menus`'
fetch_all_menu_names_sql = 'select `name` from `menus`'
fetch_by_name_sql = "select * from `menus` where `name`='{0}'"


menu_dict_example = {
    'name': 'dish_name',
    'ingredients': 'dish_ingredients',
    'ingredientsReply': 'reply sentence of ingredients',
    'steps': {'stepA': 'this is step A'}
}


def _to_dict(data):

    """ pack data from database as a dict like `menu_dict_example` """

    menu = {}
    menu['name'] = data[1]  # 菜名
    menu['flavor'] = data[2]  # 口味
    menu['method'] = data[3]  # 工艺
    menu['need_time'] = data[4]  # 时间
    menu['easiness'] = data[5]  # 难度
    menu['steps'] = data[6].strip().split('#')  # 详细步骤
    menu['ingredients'] = data[7].strip().split('#')  # 详细材料
    menu['ingredients'] = {
        one.split(':')[0]: one.split(':')[1]
        for one in menu['ingredients']
    }
    menu['ingredientsReply'] = '、'.join(data[7].strip().split('#'))
    return menu


def get_existed_menus():
    menu_names = db.query_all(fetch_all_menu_names_sql)
    return [menu_name[0] for menu_name in menu_names]

def get_menu(dish):
    menus = db.query_all(fetch_by_name_sql.format(dish))
    return _to_dict(menus[0])

def get_step_index_in_menu(dish, step):
    menu = get_menu(dish)
    if step in menu['steps']:
        return menu['steps'].index(step)
    else:
        return -1
