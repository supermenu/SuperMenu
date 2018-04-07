# !/usr/bin/python3
# coding: utf-8

import pymysql
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from traceback import format_exc
import json
import time
import uuid
import datetime, calendar




class DataBase():

    default_user = 'root'
    default_password = 'sql2017..'
    default_database = 'SuperMenu'

    def __init__(self, user=None, passwd=None, database=None,
                 host='localhost', charset='utf8'):
        self.user = DataBase.default_user if not user else user
        self.passwd = DataBase.default_password if not passwd else passwd
        self.database = DataBase.default_database if not database else database
        self.host = host
        self.charset = charset
        self.db = pymysql.connect(self.host, self.user, self.passwd,
                                  self.database, charset=self.charset)
        self.last_error_time = -1

    def execute(self, sql):
        try:
            cursor = self.db.cursor()
            cursor.execute(sql)
            self.db.commit()
            return True
        except (BrokenPipeError,
                pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
            error_time = time.time()
            print(str(e))
            if error_time - self.last_error_time > 10:
                self.last_error_time = error_time
                return self.reconnect(self.execute, sql)
            self.db.rollback()
            raise e
        except:
            self.db.rollback()
            raise e

    def query_all(self, sql):
        print(sql)
        try:
            cursor = self.db.cursor()
            num = cursor.execute(sql)
        except (BrokenPipeError,
                pymysql.err.InterfaceError, pymysql.err.OperationalError) as e:
            print(str(e))
            error_time = time.time()
            if error_time - self.last_error_time > 10:
                self.last_error_time = error_time
                return self.reconnect(self.query_all, sql)
            raise e
        except:
            raise e
        if num == 0:
            print('num=0:')
            print(str(cursor.fetchall()))
            return []
        return cursor.fetchall()

    def reconnect(self, re_execute, sql):
        self.db = pymysql.connect(self.host, self.user, self.passwd,
                                  self.database, charset=self.charset)
        re_execute(sql)

    def disconnect(self):
        self.db.close()


class User(UserMixin):

    add_user_sql = \
        "INSERT INTO `users` (`username`, `password_hash`, `userid`, `nickname`) " \
        "VALUES ('{}', '{}', '{}', '{}');"
    get_user_sql = "SELECT * FROM `users` WHERE `{}`='{}'"
    get_value_sql = "SELECT {} FROM `users` WHERE `{}`='{}'"
    set_value_sql = "UPDATE `users` SET `{}`='{}' WHERE `{}`='{}'"

    @classmethod
    def get_user_by(cls, key, value, db):
        """ return None or User instance """
        sql = cls.get_user_sql.format(key, value)
        user = db.query_all(sql)
        if not user:
            return None
        else:
            return User(user[0][1], db)

    def __init__(self, username, db, nickname=None):
        self.username = username
        self.db = db
        self.password_hash = self.get_password_hash()
        self.id = self.get_id()
        if not self.password_hash:
            self.is_exist = False
        else:
            self.is_exist = True
        if not nickname:
            self.nickname = self.get_nickname()
        else:
            self.nickname = nickname

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
                self.username, self.password_hash, self.id, self.nickname)
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
            if user_info:
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
                if userinfo:
                    return userinfo[0][3]
            except IOError:
                pass
            except ValueError:
                pass
        return str(uuid.uuid4())

    def get_nickname(self):
        if not self.is_exist:
            return ''
        else:
            nickname = self.db.query_all(
                User.get_value_sql.format(
                    'nickname', 'username', self.username
                )
            )
            nickname = nickname[0][0]
            return nickname

    def is_cooking(self):
        cooking = self.get_cooking().get('success', False)
        return cooking

    def get_cooking(self):
        cookings = self.db.query_all(
            User.get_value_sql.format(
                'cooking', 'username', self.username)
        )
        if cookings[0][0]:
            cooking = cookings[0][0]
            step = self.db.query_all(
                User.get_value_sql.format(
                    'cooking_step', 'username', self.username)
            )
            step = int(step[0][0])
            return {'cooking': cooking, 'step': step, 'success': 1}
        else:
            cooking = None
            return {'cooking': '', 'step': '', 'fail': 1}

    def set_cooking(self, dish):
        sql = User.set_value_sql.format(
            'cooking', dish, 'username', self.username)
        return self.db.execute(sql)

    def set_cooking_step(self, step):
        sql = User.set_value_sql.format(
            'cooking_step', step, 'username', self.username)
        return self.db.execute(sql)

    def set_recommend(self,dishs):
        sql = User.set_value_sql.format(
            'recommend', dishs, 'username', self.username)
        return self.db.execute(sql)

    def get_recommend(self):
        if not self.is_exist:
            return ''
        else:
            recommend = self.db.query_all(
                User.get_value_sql.format(
                    'recommend', 'username', self.username
                )
            )
            recommend = recommend[0][0]
            return recommend

    def set_basket(self,dishs):
        sql = User.set_value_sql.format(
            'basket', dishs, 'username', self.username)
        return self.db.execute(sql)

    def get_basket(self):
        if not self.is_exist:
            return ''
        else:
            basket = self.db.query_all(
                User.get_value_sql.format(
                    'basket', 'username', self.username
                )
            )
            basket = basket[0][0]
            return basket

    def set_ask_status(self,ask_status):
        sql = User.set_value_sql.format(
            'ask_status', ask_status, 'username', self.username)
        return self.db.execute(sql)

    def get_ask_status(self):
        if not self.is_exist:
            return ''
        else:
            ask_status = self.db.query_all(
                User.get_value_sql.format(
                    'ask_status', 'username', self.username
                )
            )
            ask_status = ask_status[0][0]
            return ask_status

    def reset_cooking(self):
        return self.set_cooking('') and self.set_cooking_step('')
        
    def finish_cooking(self, dish):
        cook_record_sql = "INSERT INTO `cooking-record` VALUES ('{user}', '{dish}', '{time}');"
        self.db.execute(cook_record_sql.format(user = self.username,dish = dish,time =  datetime.datetime.today()))
        self.reset_cooking()
        sql = User.get_value_sql.format('cooked', 'username', self.username)
        cooked = self.db.query_all(sql)
        cooked = cooked[0][0]
        if cooked is None:
            sql = User.set_value_sql.\
                    format('cooked', dish, 'username', self.username)
        else:
            cooked = cooked.split('#')
            if dish not in cooked:
                cooked.append(dish)
            cooked = '#'.join(cooked)
            sql = User.set_value_sql.\
                    format('cooked', cooked, 'username', self.username)
        return self.db.execute(sql)

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


class AnonymousUser(User):

    def __init__(self, session_id, db):
        username = str(abs(hash(str(time.time()))))
        password = str(abs(hash(str(time.time())+username)))
        super(AnonymousUser, self).__init__(username, db, nickname='游客')
        self.password(password)
        sql = User.set_value_sql.\
                format('access_token', session_id, 'username', username)
        db.execute(sql)
        print('anonymous user {} created with session-id {}'.\
              format(username, session_id))
