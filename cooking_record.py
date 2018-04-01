#!/usr/bin/python3
#coding: utf-8


import pymysql
from web.modules import DataBase


db = DataBase()
fetch_all_records_sql = "select * from `cooking-record` where `user`='{0}'"
fetch_by_time_sql = "select * from `cooking-record` where `complete_time` Between  '{star_time}'\
                      and '{end_time}' and `user` = '{name}'"
cook_record_sql = "INSERT INTO `cooking-record` VALUES ('{user}', '{dish}', '{time}');"

menu_dict_example = {
    'name': 'dish_name',
    'ingredients': 'dish_ingredients',
    'ingredientsReply': 'reply sentence of ingredients',
    'steps': {'stepA': 'this is step A'}
}

cooking_record_example = {
    'user': 'user_name',
    'dish': 'dish_name',
    'time': 'complete_time',

}

def _to_dict(data):

    """ pack data from database as a dict like `cooking_record_example` """
    cooking_record = {}
    cooking_record['user'] = data[0]
    cooking_record['dish'] = data[1]
    cooking_record['time'] = data[2]
    return cooking_record

def get_all_cooking_record(user):
    fetch_cooking_records = db.query_all(fetch_all_records_sql.format(user))
    cooking_records = []
    for cooking_record in fetch_cooking_records:
        cooking_records.append(_to_dict(cooking_record))
    return cooking_records

def get_cooking_record_by_time(user,star_time,end_time):
    fetch_cooking_records = db.query_all(fetch_by_time_sql.format(star_time = star_time,end_time = end_time,name = user))
    cooking_records = []
    for cooking_record in fetch_cooking_records:
        cooking_records.append(_to_dict(cooking_record))
    return cooking_records


def cook_record(user,dish,time):
    db.execute(cook_record_sql.format(user = user,dish = dish,time = time))
