# !/usr/bin/python3
# coding: utf-8


import os
import time
import json
from urllib.parse import unquote

from flask import Flask, render_template, request, flash, url_for, redirect, Response
from flask.ext.bootstrap import Bootstrap
from flask_login import login_user, login_required
from flask_login import current_user
from flask_login import logout_user

from __init__ import app, login_manager
from modules import User, DataBase


app.secret_key = os.urandom(24)
bootstrap = Bootstrap(app)
db = DataBase()


@app.route('/')
def default():
    return redirect(url_for('index'))

@app.route('/index/')
def index():
    print(current_user)
    return redirect(url_for('menus', page='1'))
    # return render_template(
    #     'index.html',
    #     user=getattr(current_user, 'username', None))

@app.route('/apk/')
def get_apk():
    return redirect(url_for('static', filename='菜单.apk'))

@app.route('/menus/')
def menus():
    page = request.args.get('page', 0)
    if not page:
        return 'Invalid'
    return render_template('index.html')

each_page_menus = 15
menu_pics_dir = ''
def get_menu_data():
    db = DataBase()
    fetch_all_menu_names_sql = 'select `name` from `menus`'
    menu_names = db.query_all(fetch_all_menu_names_sql)
    menu_names = [one[0] for one in menu_names]
    # get pic
    static_dir = os.path.join('.', 'static')
    menu_pics = os.listdir(static_dir)
    menus = []
    for menu_name in menu_names:
        if menu_name+'.png' in menu_pics:
            menu_pic = url_for("static", filename=menu_name+'.png')
        else:
            continue
            # menu_pic = ''
        menus.append({'name': menu_name, 'pic': menu_pic})
    return menus

@app.route('/get-menu-page-count/')
def menu_page_count():
    global each_page_menus
    menus = get_menu_data()
    if len(menus) < each_page_menus:
        return '1'
    else:
        return str(len(menus) // each_page_menus)

@app.route('/get-menu-data/')
def get_menu_page_data():
    global each_page_menus
    page = int(request.args.get('page', 0))
    if not page:
        return 'Invalid'
    else:
        page = int(page)
    menus = get_menu_data()
    menu_page_data = menus[each_page_menus*(page-1): each_page_menus*page]
    return Response(json.dumps(menu_page_data), mimetype='application/json')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', login=True)
    username = request.form.get('username')
    password = request.form.get('password')
    action = request.form.get('button')

    if action == 'toregister':
        return redirect(url_for('register'))
    if not username:
        flash('请填写用户名')
        return render_template('login.html')
    elif not password:
        flash('请填写密码')
        return render_template('login.html')

    user = User(username, db)
    if user.verify_password(password):
        login_user(user)
        return redirect(url_for('index'))
    else:
        flash('用户名或密码无效')
        return render_template('login.html')

def get_healthy_stats(sex, age, height,weight):
    if sex == 'm':
        need_energy = \
            (66.5 + (13.7 * weight) + (5 * height) -  (6.8 * age)) * 1.3
    else:
        need_energy = \
            (655 + (9.56 * weight) + (1.85 * height) -  (4.68 * age)) * 1.3
    if age <= 5:
        need_protein = 47.5
        need_fat = need_energy * 0.325 / 9
    elif 6 <= age <= 12:
        need_protein = 65
        need_fat = need_energy * 0.275 / 9
    elif 13 <= age <= 17:
        need_protein = 85 if sex == 'm' else 80
        need_fat = need_energy * 0.275 / 9
    elif 18 <= age <= 49:
        need_protein = 77.5 if sex == 'm' else 67.5
        need_fat = need_energy * 0.325 / 9
    elif 50 <= age <= 59:
        need_protein = 77.5 if sex == 'm' else 67.5
        need_fat = need_energy * 0.25 / 9
    elif 60 <= age <= 69:
        need_protein = 75 if sex == 'm' else 65
        need_fat = need_energy * 0.25 / 9
    elif 70 <= age <= 79:
        need_protein = 75 if sex == 'm' else 65
        need_fat = need_energy * 0.25 / 9
    elif 80 <= age:
        need_protein = 75 if sex == 'm' else 65
        need_fat = need_energy * 0.25 / 9

    return {'ne': need_energy, 'np': need_protein, 'nf': need_fat}

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    username = request.form.get('username')
    password = request.form.get('password')
    nickname = request.form.get('nickname')
    age = request.form.get('age')
    sex = request.form.get('sex')
    height = request.form.get('height')
    weight = request.form.get('weight')
    action = request.form.get('button')
    if action == 'tologin':
        return redirect(url_for('login'))
    if not username:
        flash('请填写用户名')
        return render_template('register.html')
    elif not password:
        flash('请填写密码')
        return render_template('register.html')
    elif not nickname:
        flash('请填写昵称')
        return render_template('register.html')
    elif not sex:
        flash('请填写性别')
        return render_template('register.html')
    elif not age:
        flash('请填写年龄')
        return render_template('register.html')
    elif not height:
        flash('请填写身高')
        return render_template('register.html')
    elif not weight:
        flash('请填写体重')
        return render_template('register.html')
    age = int(age)
    height = float(height)
    weight = float(weight)
    sex = 'm' if '男' in sex else 'f'
    self_infos = get_healthy_stats(sex, age, height)

    family_numbers = 0
    family_members = []
    for key in list(request.form.keys()):
        if 'relationship_' in key:
            index = int(key.replace('relationship_', ''))
            c_key = 'relationship'
            c_value = request.form.get(key)
        elif 'age_' in key:
            index = int(key.replace('age_', ''))
            c_key = 'age'
            c_value = int(request.form.get(key))
        elif 'sex_' in key:
            index = int(key.replace('sex_', ''))
            c_key = 'sex'
            c_value = request.form.get(key)
            c_value = 'm' if '男' in c_value else 'f'
        elif 'height_' in key:
            index = int(key.replace('height_', ''))
            c_key = 'height'
            c_value = float(request.form.get(key))
        elif 'weight_' in key:
            index = int(key.replace('weight_', ''))
            c_key = 'weight'
            c_value = float(request.form.get(key))
        else:
            continue
        while len(family_members) < index+1:
            family_members.append(dict())
        family_members[index][c_key] = c_value

    family_members.append({
        'relationship': '本人',
        'age': age,
        'sex': sex,
        'height': height,
        'weight': weight,
        'need_protein': self_infos['np'],
        'need_energy': self_infos['ne'],
        'need_fat': self_infos['nf']
    })

    for member in family_members:
        age = member['age']
        sex = member['sex']
        height = member['height']
        weight = member['weight']
        stats = get_healthy_stats(sex, age, height)
        member['need_protein'] = stats['np']
        member['need_energy'] = stats['ne']
        member['need_fat'] = stats['nf']

    new_user = User(username, db, nickname=nickname)
    if new_user.exists():
        flash('用户名 {} 已被注册'.format(username))
        return render_template('login.html', register=True)
    else:
        new_user.password(password)
        sql = "INSERT INTO `SuperMenu`.`family_member` (`user`, `relationship`, `sex`, `age`, `need_energy`, `need_protein`, `need_axunge`) VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}');"
        for member in family_members:
            db.execute(sql.format(
                username, member['relationship'], member['sex'],
                member['age'], member['need_energy'],
                member['need_protein'], member['need_fat']
            ))
        flash('{} 注册成功'.format(username))
        return redirect(url_for('login'))

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return render_template('index.html')

# 这个callback函数用于reload User object，根据session中存储的user id
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id, db)

@app.route('/authorize/', methods=['GET', 'POST'])
def authorize():
    if request.method == 'GET':
        if request.args.get('client_id') == 'supermenu':
            return render_template('login.html', authorize=True)
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User(username, db)
        if user.verify_password(password):
            user_code = user.get_id()
            state = request.args.get('state')
            redirect_url = unquote(request.args.get('redirect_uri'))
            redirect_url += '&code={}&state={}&response_type=code'.format(user_code, state)
            return redirect(redirect_url)
        # TODO

@app.route('/token/', methods=['GET', 'POST'])
def generate_token():
    print(request.form)
    user_id = request.form.get('code')
    sql = "SELECT `username` FROM `users` WHERE `userid`='{}'".format(user_id)
    insert_token_sql = \
        "UPDATE `users` SET `access_token`='{}' WHERE `userid`='{}'"
    user = db.query_all(sql.format(user_id))
    if not user:
        return_data = {
            'error': '100',
            'error_description': 'user not exists'
        }
    else:
        access_token = str(abs(hash(str(time.time())+user_id)))
        db.execute(insert_token_sql.format(access_token, user_id))
        return_data = {
            'access_token': access_token,
            'refresh_token': access_token,
            'expires_in': 30 * 24 * 60 * 60 * 1000
        }
    print(return_data)
    return Response(
        json.dumps(return_data), mimetype='application/json'
    )


if __name__ == '__main__':
    # context = ('cert.crt', 'key.key')
    # app.run(host='127.0.0.1', port=5002, ssl_context=context)
    app.run(host='127.0.0.1', port=5002)
