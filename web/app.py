# !/usr/bin/python3
# coding: utf-8


import os
import time

from flask import Flask, render_template, request, flash, url_for, redirect
from flask.ext.bootstrap import Bootstrap
from flask_login import login_user, login_required
from flask_login import current_user
from flask_login import logout_user

from __init__ import app, login_manager
from modules import User, DataBase


app.secret_key = os.urandom(24)
bootstrap = Bootstrap(app)
db = DataBase('root', 'sql2017..', 'SuperMenu')


@app.route('/')
def default():
    return redirect(url_for('index'))

@app.route('/index/')
def index():
    print(current_user)
    return render_template(
        'index.html',
        user=getattr(current_user, 'username', None))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    # 展示登录界面
    if request.method == 'GET':
        return render_template('login.html')
    username = request.form.get('username')
    password = request.form.get('password')
    if not username:
        flash('请填写用户名')
        return render_template('login.html')
    elif not password:
        flash('请填写密码')
        return render_template('login.html')
    action = request.form.get('button')
    if action == 'register':
        # 注册
        new_user = User(username, db)
        if new_user.exists():
            flash('用户名 {} 已被注册'.format(username))
        else:
            new_user.password(password)
            flash('{} 注册成功'.format(username))
        return render_template('login.html')
    elif action == 'login':
        # 登录
        user = User(username, db)
        if user.verify_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('用户名或密码无效')
            return render_template('login.html')

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return render_template('index.html')


# 这个callback函数用于reload User object，根据session中存储的user id
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id, db)





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)
