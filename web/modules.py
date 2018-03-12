# !/usr/bin/python3
# coding: utf-8


import pymysql
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from traceback import format_exc
import json
import uuid


class DataBase():

    def __init__(self, user, passwd, database=None,
                 host='localhost', charset='utf8'):
        self.db = pymysql.connect(
            host, user, passwd, database, charset=charset)
        self.cursor = self.db.cursor()

    def execute(self, sql):
        self.cursor.execute(sql)
        self.db.commit()

    def query_all(self, sql):
        num = self.cursor.execute(sql)
        if num == 0:
            return None
        return self.cursor.fetchall()


class User(UserMixin):

    add_user_sql = \
        "INSERT INTO `users` (`username`, `password_hash`, `userid`) " \
        "VALUES ('{}', '{}', '{}');"
    get_user_sql = "SELECT * FROM `users` WHERE `{}`='{}'"

    def __init__(self, username, db):
        self.username = username
        self.db = db
        self.password_hash = self.get_password_hash()
        self.id = self.get_id()
        if not self.password_hash:
            self.is_exist = False
        else:
            self.is_exist = True

    def exists(self):
        return self.is_exist

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    #@password.setter
    def password(self, password):
        """ save user name, id and password hash to db """
        self.password_hash = generate_password_hash(password)
        self.db.execute(
            User.add_user_sql.format(
                self.username, self.password_hash, self.id)
        )

    def verify_password(self, password):
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

    def get_password_hash(self):
        """try to get password hash from file.

        :return password_hash: if the there is corresponding user in
                the file, return password hash.
                None: if there is no corresponding user, return None.
        """
        try:
            user_info = self.db.query_all(
                User.get_user_sql.format('username', self.username))
            if user_info is not None:
                return user_info[0][2]
        except IOError:
            return None
        except ValueError:
            return None
        return None

    def get_id(self):
        """get user id from profile file, if not exist, it will
        generate a uuid for the user.
        """
        if self.username is not None:
            try:
                userinfo = self.db.query_all(
                    User.get_user_sql.format('username', self.username))
                if userinfo is not None:
                    return userinfo[0][3]
            except IOError:
                pass
            except ValueError:
                pass
        return str(uuid.uuid4())

    @staticmethod
    def get(user_id, db):
        """try to return user_id corresponding User object.
        This method is used by load_user callback function
        """
        if not user_id:
            return None
        try:
            users = db.query_all(User.get_user_sql.format('userid', user_id))
            print(users)
            for user in users:
                if user[3] == user_id:
                    return User(user[1], db)
        except Exception as e:
            print(str(e))
            print(format_exc())
            return None
        return None
