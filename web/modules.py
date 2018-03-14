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

    default_user = 'root'
    default_password = 'sql2017..'
    default_database = 'SuperMenu'

    def __init__(self, user=None, passwd=None, database=None,
                 host='localhost', charset='utf8'):
        if not user:
            user = DataBase.default_user
        if not passwd:
            passwd = DataBase.default_password
        if not database:
            database = DataBase.default_database
        self.db = pymysql.connect(
            host, user, passwd, database, charset=charset)
        self.cursor = self.db.cursor()

    def execute(self, sql):
        try:
            self.cursor.execute(sql)
            self.db.commit()
            return True
        except:
            self.db.rollback()
            return False

    def query_all(self, sql):
        num = self.cursor.execute(sql)
        if num == 0:
            return None
        return self.cursor.fetchall()

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
        return self.get_cooking().get('success', False)

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

    def reset_cooking(self):
        return self.set_cooking('') and self.set_cooking_step('')

    def finish_cooking(self, dish):
        sql = User.get_value_sql.format('cooked', 'username', self.username)
        cooked = self.db.query_all(sql)
        if not cooked:
            sql = User.set_value_sql.\
                    format('cooked', dish, 'username', self.username)
        else:
            cooked = cooked[0].split('#')
            cooked.append(dish)
            cooked = '#',join(cooked)
            sql = User.set_value_sql.\
                    format('cooked', cooked)
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

