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
add_menu_sql =  "INSERT INTO `menus` (`name`, `need_time`, `easiness`, `steps`,`ingredients`,`energy`,`protein`,`axunge`) " \
                "VALUES ('{}', '{}', '{}', '{}','{}','{}','{}','{}');"
update_score_sql = "UPDATE `menus` SET `score` = `score` + '{}' WHERE `name` = '{}'"
update_numbers_sql = "UPDATE `menus` SET `numbers` = `numbers` + 1 WHERE `name` = '{}'"
fetch_by_keys_ingredients = "select name from `menus` where `ingredients` like '%{}%'"

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

def get_menu_by_ingredients(ingredients):
    menus_temp =  db.query_all(fetch_by_keys_ingredients.format(ingredients))
    menus = []
    if menus_temp:
        for menu in menus_temp:
            menus.append(menu[0])
    return menus

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

def get_nutritional(ingredient,weight):
    html = requests.get('http://www.boohee.com/food/search?keyword=' + ingredient, headers=headers)
    html_doc_search = html.text
    soup = BeautifulSoup(html_doc_search, "lxml")
    url = soup.find('li',class_='item clearfix').find('div').find('a',href = re.compile("/shiwu/"))['href']
    url = 'http://www.boohee.com' + url
    html = urllib.request.urlopen(url).read().decode('utf-8')
    soup = BeautifulSoup(html, "lxml")
    dds = soup.find('div',class_ = 'nutr-tag margin10').find_all('span',class_ = 'dd')
    dts = soup.find('div',class_ = 'nutr-tag margin10').find_all('span',class_ = 'dt')
    energy = 0
    protein = 0
    axunge = 0
    for dd,dt in zip(dds,dts):
        dd = dd.text
        dt = dt.text
        if dt == '热量(大卡)':
            energy = float(dd)  * float(weight)/100
        if dt == '脂肪(克)':
            axunge = float(dd) * float(weight)/100
        if dt == '蛋白质(克)':
            protein = float(dd) * float(weight)/100
    return energy,protein,axunge

def get_url_haodou(dish):
    html = requests.get('https://m.haodou.com/recipe/search/?keyword=' + dish,headers=headers)
    html_doc_search = html.text
    soup = BeautifulSoup(html_doc_search,"lxml")
    url_dish = soup.find(href=re.compile("/recipe/[0-9]"))
    if url_dish:
        return 'https://www.haodou.com' + url_dish['href']
    else:
        return None



def get_url(dish):
    html = requests.get('https://home.meishichina.com/search/' + dish, headers=headers)
    soup = BeautifulSoup(html.content,"lxml")
    url_dish = soup.find(href=re.compile("recipe-"))['href']
    return url_dish

def get_dish(dish):
    url_meishi = get_url_meishi(dish)
    url_haodou = get_url_haodou(dish)
    ingredients = ''
    steps = ''
    need_time = ''
    easiness = ''
    energy = 0
    protein = 0
    axunge = 0
    flag = 1
    if url_meishi:
        html = requests.get(url_meishi, headers=headers)
        html_doc = html.text
        soup = BeautifulSoup(html_doc, 'lxml')
        #爬取食材的耗时和难度
        span = soup.find(text = "耗时")
        need_time = span.parent.find_previous_sibling().text.strip().replace('廿','二十')
        span = soup.find(text = "难度")
        easiness = span.parent.find_previous_sibling().text.strip()
    if url_haodou:
        print(url_haodou)
        html = requests.get(url_haodou, headers=headers)
        html_doc = html.text
        soup = BeautifulSoup(html_doc, 'lxml')
        # 爬取 食材 主料
        full_text_ingredients = soup.findAll("li", {"class": "ingtmgr"})
        for text in full_text_ingredients:
            # 食材
            ingredients += '#' + text.p.text + ':'
            # 用量
            ingredients += text.span.text
            if 'g' not in text.span.text:
                flag = energy = protein = axunge = 0
            if flag:
                energy_,protein_,axunge_ =get_nutritional(text.p.text,text.span.text[:-1])
                energy += energy_
                protein += protein_
                axunge += axunge_
        # 爬取 食材 辅料
        print(energy, axunge, protein)
        full_text_accessories = soup.findAll("li", {"class": "ingtbur"})
        for text in full_text_accessories:
            # 食材
            ingredients += '#' + text.p.text + ':'
            # 用量
            ingredients += text.span.text

        # 爬取详细步骤
        full_text_step_text = soup.findAll("p", {"class": "sstep"})
        for text in full_text_step_text:
            steps += '#' + text.text[2:]
        return ingredients,need_time,easiness,steps,energy,protein,axunge
    return None,None,None,None,None,None,None

def get_url_meishi(dish):
    html = requests.get('https://home.meishichina.com/search/' + dish, headers=headers)
    soup = BeautifulSoup(html.content,"lxml")
    url_dish = soup.find(href=re.compile("recipe-"))['href']
    return url_dish


def crawler_menu(dish):
    print('正在将爬取菜谱：' + dish)
    ingredients,need_time,easiness,steps,energy,protein,axunge = get_dish(dish)
    if ingredients and need_time:
        print( dish + '正在写入数据库')
        db.execute(add_menu_sql.format(dish,need_time, easiness, steps,ingredients,energy,protein,axunge))
    else:
        print('爬取失败！')
    

def save_score(dish,score):
    print(dish)
    print(score)
    db.execute(update_score_sql.format(score,dish))
    db.execute(update_numbers_sql.format(dish))
