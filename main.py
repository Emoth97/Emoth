# !/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request
from config import DevConfig
from flask_sqlalchemy import SQLAlchemy
#from sqlalchemy import func
#from flask_wtf import Form
#from wtforms import StringField, TextAreaField
#from wtforms.validators import DataRequired, Length
from datetime import datetime
from hashlib import md5
from random import randint
import random
import sqlite3
import SM2
import traceback

app = Flask(__name__)
app.config.from_object(DevConfig)
db = SQLAlchemy(app)
len_para = int(SM2.Fp / 4)
current_level = 4

class data_query(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(255))
    # 绝密
    attribute1 = db.Column(db.String(255))
    verify_value1 = db.Column(db.VARCHAR(255))
    # 机密
    attribute2 = db.Column(db.String(255))
    verify_value2 = db.Column(db.VARCHAR(255))
    # 秘密
    attribute3 = db.Column(db.String(255))
    verify_value3 = db.Column(db.VARCHAR(255))
    # 公开
    attribute4 = db.Column(db.String(255))
    verify_value4 = db.Column(db.VARCHAR(255))
    
    node1 = db.Column(db.VARCHAR(255))
    node2 = db.Column(db.VARCHAR(255))
    node_root = db.Column(db.VARCHAR(255))
    
    '''
                    node_root                      hash(node2||veri4)
                  /           \
                node2     attribute4               hash(node1||veri3)    veri4
              /       \
            node1     attribute3                   hash(veri1||veri2)    veri3
          /       \
    attribute1    attribute2                       veri1                 veri2
    '''
    def __init__(self, name, attr4, attr3 = "", attr2 = "", attr1 = ""):
        random.seed(datetime.now())
        self.name = name
        self.attribute1 = attr1 + '#' + str(randint(2**128,2**256)) # 在数据后加上128位到256位的随机数
        self.verify_value1 = md5(self.attribute1.encode(encoding='utf-8')).hexdigest() # 数据的hash散列值
        self.attribute2 = attr2 + '#' + str(randint(2**128,2**256))
        self.verify_value2 = md5(self.attribute2.encode(encoding='utf-8')).hexdigest()
        self.attribute3 = attr3 + '#' + str(randint(2**128,2**256))
        self.verify_value3 = md5(self.attribute3.encode(encoding='utf-8')).hexdigest()
        self.attribute4 = attr4 + '#' + str(randint(2**128,2**256))
        self.verify_value4 = md5(self.attribute4.encode(encoding='utf-8')).hexdigest()
        
        self.node1 = md5((self.verify_value1 + self.verify_value2).encode("utf-8")).hexdigest()
        self.node2 = md5((self.node1 + self.verify_value1).encode("utf-8")).hexdigest()
        self.node_root = md5((self.node2 + self.verify_value1).encode("utf-8")).hexdigest()
        
    def __repr__(self):
        return "<DATA '{}'>".format(self.name)
    
@app.route('/')
def home():
    return render_template(
        'home.html'
    )
    
@app.route('/loginhome')
def login():
    return render_template('login.html')

# 获取登录参数及处理
@app.route('/login')
def getLoginRequest():
    # 连接数据库
    db2 = sqlite3.connect('users_database.db')
    # 数据库游标cursor
    cursor = db2.cursor()

    # SQL 查询语句
    sql = "select user.user, password, private_key from user, private_key where user.user='%s'" % request.args.get('user')+" and user.user = private_key.user"

    try:
        # 执行sql语句
        cursor.execute(sql)
        results = cursor.fetchall()[0]

        '''
        解密函数Decrypt
        例子中privatekey为私钥 pwd为密文 解密后为16进制数据
        '''
        m = SM2.Decrypt(results[1], results[2], len_para)
        M = bytes.fromhex(m)

        if M.decode() == request.args.get('password'):
            return '登录成功'

        else:
            return '用户名或密码不正确'

        # 提交到数据库执行
            db2.commit()

    except:
        # 如果发生错误则回滚
        traceback.print_exc()
        db2.rollback()

    # 关闭cursor
    cursor.close()

    # 关闭数据库连接
    db2.close()

    
# 注册界面
@app.route('/register')
def register():
    return render_template('register.html')

# 获取注册请求及处理
@app.route('/registuser')
def getRegisterRequest():
    # 连接数据库
    db2 = sqlite3.connect('users_database.db')

    # 数据库游标cursor
    cursor = db2.cursor()

    # 如果存在返回用户名已存在
    sql_if_exist = "select * from user where user = '%s'" % request.args.get('user')
    cursor.execute(sql_if_exist)

    if (len(cursor.fetchall())):
        return '用户名已存在'
    
    '''
    len_para是密钥长度/4 密钥长度Fp在SM2设置
    e、d、k为随机16进制数
    '''
    e = SM2.get_random_str(len_para)
    d = SM2.get_random_str(len_para)
    k = SM2.get_random_str(len_para)

    '''
    加密函数Encrypt
    例子中Pa为公钥由私钥d计算得到 Message为消息
    '''
    Pa = SM2.kG(int(d, 16), SM2.sm2_G, len_para)
    Encrypt_password = SM2.Encrypt(request.args.get('password'), Pa, len_para, 0)

    # SQL 插入语句
    sql_user = "INSERT INTO user(user, password, public_key, level) VALUES ('%s'" % request.args.get('user')+", '%s'" % Encrypt_password+", '%s'" % Pa+", '%s'" % request.args.get('level')+")"
    sql_private_key = "INSERT INTO private_key(user, private_key) VALUES ('%s'" % request.args.get('user')+", '%s'" % d+")"

    try:
        # 执行sql语句
        cursor.execute(sql_user)
        cursor.execute(sql_private_key)

        # 提交到数据库执行
        db2.commit()

        # 注册成功之后跳转到登录页面
        return render_template('login.html')

    except:
        # 抛出错误信息
        traceback.print_exc()

        # 如果发生错误则回滚
        db2.rollback()

        return '注册失败'

    # 关闭cursor
    cursor.close()

    # 关闭数据库连接
    db2.close()

def init_userdate():
    # 连接数据库
    init_connect = sqlite3.connect('users_database.db')

    # 数据库游标init_cursor
    init_cursor = init_connect.cursor()

    # 如果表user不存在则新建
    init_cursor.execute("CREATE TABLE IF NOT EXISTS user (user varchar(50) PRIMARY KEY not null, password varchar(300), public_key varchar(300), level varchar(3))")

    # 如果表private_key不存在则新建
    init_cursor.execute("CREATE TABLE IF NOT EXISTS private_key (user varchar(50) PRIMARY KEY not null, private_key varchar(300))")

    # 关闭init_cursor
    init_cursor.close()

    # 提交事务
    init_connect.commit()

    # 关闭connection
    init_connect.close()
    
if __name__ == '__main__':
    init_userdate()
    app.run(ssl_context = (
        "server/server-cert.pem",
        "server/server-key.pem"))