#!/usr/bin/python3
#coding: utf-8


import pymysql
from web.modules import DataBase


db = DataBase()
fetch_all_family_member_sql = "select * from `family_member` where `user`='{0}'"




family_member_example = {
    'user': 'user_name',
    'relationship': 'Relationship of relatives',
    'sex': 'sex of relatives',
    'age': 'age of relatives',
    'need_energy':'The energy needed for a day',
    'need_protein':'The protein needed for a day',
    'need_axunge':'The axunge needed for a day'
}

def _to_dict(data):

    """ pack data from database as a dict like `cooking_record_example` """
    family_member = {}
    family_member['user'] = data[0]
    family_member['relationship'] = data[1]
    family_member['sex'] = data[2]
    family_member['age'] = data[3]
    family_member['need_energy'] = data[4]
    family_member['need_protein'] = data[5]
    family_member['need_axunge'] = data[6]
    return family_member

def get_all_cooking_record(user):
    fetch_family_members = db.query_all(fetch_all_family_member_sql.format(user))
    print(fetch_family_members)
    family_members = []
    for family_member in fetch_family_members:
        family_members.append(_to_dict(family_member))
    return family_members

