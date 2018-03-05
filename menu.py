#!/usr/bin/python3
#coding: utf-8


import pymysql


db = pymysql.connect('localhost', 'fwwb', 'fwwb1111', 'super_menu', charset='utf8')
cursor = db.cursor()
fetch_all_menus_sql = 'select * from `menu`'
fetch_all_menu_names_sql = 'select `菜名` from `menu`'
fetch_by_name_sql = "select * from `menu` where `菜名`='{0}'"


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
    menu['easiness'] = data[2]  # 难度
    menu['need_time'] = data[3]  # 时间
    menu['flavor'] = data[4]  # 口味
    menu['method'] = data[5]  # 工艺
    menu['steps'] = data[7].strip().split('#')[:-1]  # 详细步骤
    menu['ingredients'] = data[9].strip().split('#')[:-1]  # 详细材料
    menu['ingredientsReply'] = '、'.join(data[9].strip().split('#')[:-1])
    return menu


def get_existed_menus():
    cursor.execute(fetch_all_menu_names_sql)
    menu_names = cursor.fetchall()
    return [menu_name[0] for menu_name in menu_names]

def get_menu(dish):
    cursor.execute(fetch_by_name_sql.format(dish))
    menus = cursor.fetchall()
    return _to_dict(menus[0])

def get_step_index_in_menu(dish, step):
    menu = get_menu(dish)
    if step in menu['steps']:
        return menu['steps'].index(step)
    else:
        return -1
