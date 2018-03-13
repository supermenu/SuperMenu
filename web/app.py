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
    return render_template(
        'index.html',
        user=getattr(current_user, 'username', None))

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html', login=True)
    username = request.form.get('username')
    password = request.form.get('password')
    nickname = request.form.get('nickname')
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

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('login.html', register=True)
    username = request.form.get('username')
    password = request.form.get('password')
    nickname = request.form.get('nickname')
    action = request.form.get('button')
    if action == 'tologin':
        return redirect(url_for('login'))
    if not username:
        flash('请填写用户名')
        return render_template('login.html', register=True)
    elif not password:
        flash('请填写密码')
        return render_template('login.html', register=True)
    elif not nickname:
        flash('请填写昵称')
        return render_template('login.html', register=True)

    new_user = User(username, db)
    if new_user.exists():
        flash('用户名 {} 已被注册'.format(username))
        return render_template('login.html', register=True)
    else:
        new_user.password(password)
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
            return render_template('login.html')
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
