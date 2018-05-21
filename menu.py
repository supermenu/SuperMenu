#!/usr/bin/python3
#coding: utf-8


import pymysql
from web.modules import DataBase
from bs4 import BeautifulSoup
import requests
import os
import urllib.request
import re

db = DataBase()
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/20100101 Firefox/23.0'}
fetch_all_menus_sql = 'select * from `menus`'
fetch_all_menu_names_sql = 'select `name` from `menus`'
fetch_by_key_sql = "select * from `menus` where `{key}` = '{value}'"
fetch_by_keys_sql = "select * from `menus` where `flavor` like '{flavor_value}' \
                    and `need_time` like '{need_time_value}' and `easiness` like '{easiness_value}'"
add_menu_sql =  "INSERT INTO `menus` (`name`, `need_time`, `easiness`, `steps`,`ingredients`) " \
                "VALUES ('{}', '{}', '{}', '{}','{}');"
update_score_sql = 'UPDATE `menus` SET `score` = `score` + {} WHERE `name` = {}'
update_numbers_sql = 'UPDATE `menus` SET `numbers` = `numbers` + 1 WHERE `name` = {}'


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

def tansform_time(need_time_value):
    time_10 = ['时间花费短', '时间消耗短', '时间短']
    time_20 = ['时间花费较短', '时间消耗较短', '速度较快', '速度快', '时间比较快']
    time_30 = ['时间花费适中', '时间消耗适中', '速度适中']
    time_40 = ['时间较多', '时间花费较多', '时间消耗较多', '时间花费比较多', '时间消耗比较多']
    time_60 = ['时间花费长', '时间消耗长', '时间久', '时间花费久', '时间消耗久']
    if need_time_value in time_10:
        return '十分钟'
    if need_time_value in time_20:
        return '二十分钟'
    if need_time_value in time_30:
        return '半小时'
    if need_time_value in time_40:
        return '四十分钟'
    if need_time_value in time_60:
        return '一个小时'
    return need_time_value

def get_attributes(flavor_value = '%',need_time_value = '%',easiness_value = '%'):
    need_time_value = tansform_time(need_time_value)
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



def get_url(dish):
    html = requests.get('https://home.meishichina.com/search/' + dish, headers=headers)
    soup = BeautifulSoup(html.content,"lxml")
    url_dish = soup.find(href=re.compile("recipe-"))['href']
    return url_dish

def get_dish(dish):
    url = get_url(dish)
    ingredients = ''
    steps = ''
    need_time = ''
    easiness = ''
    if url:
        html = requests.get(url, headers=headers)
        html_doc = html.text
        soup = BeautifulSoup(html_doc, 'lxml')
        particulars = soup.find_all('fieldset',class_ = 'particulars')
        #爬取食材，category_s1为食材名，category_s2为食材用量
        for particular in particulars:
            category_s1 = particular.find_all('span', class_='category_s1')
            category_s2 = particular.find_all('span', class_='category_s2')
            for s1,s2 in zip(category_s1,category_s2):
                ingredients += '#' + s1.text + ':' + s2.text
        ingredients = ingredients.strip().replace('\r','').replace('\n','')

        #爬取食材的耗时和难度
        span = soup.find(text = "耗时")
        need_time = span.parent.find_previous_sibling().text.strip().replace('廿','二十')
        span = soup.find(text = "难度")
        easiness = span.parent.find_previous_sibling().text.strip()

        divs = soup.find_all('div',class_ = 'recipeStep_word')
        for div in divs:
            steps += '#' + div.text[1:]
        return ingredients,need_time,easiness,steps
    else:
        return None,None,None,None

def crawler_menu(dish):
    print('正在将爬取菜谱：' + dish)
    ingredients,need_time,easiness,steps = get_dish(dish)
    if ingredients:
        print( dish + '正在写入数据库')
        db.execute(add_menu_sql.format(dish,need_time, easiness, steps,ingredients))
    else:
        print('爬取失败！')
    

def save_score(dish,score):
    db.execute(update_score_sql.format(dish,score))
    db.execute(update_numbers_sql.format(dish))
