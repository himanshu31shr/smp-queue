import mysql.connector
import os
import sys


class mysqlConnector:
    _engine = None

    @classmethod
    def _init_engine(cls):
        if cls._engine is None:
            try:
                cls._engine = mysql.connector.connect(
                    host=os.getenv("DB_HOSTNAME") or "localhost",
                    user=os.getenv("DB_USERNAME") or "root",
                    password=os.getenv("DB_PASSWORD") or "mysql12345",
                    database=os.getenv("DB_NAME") or "spot_my_pic_dev",
                )
            
            except mysql.connector.Error as e:
                print(f"Error connecting to MySQL server: {e}")
                sys.exit(1)
                
        cls._engine.reconnect()
        return cls._engine

    @classmethod
    def findAll(cls, query, data=()):
        mycursor = cls._init_engine().cursor(buffered=True, dictionary=True)
        mycursor.execute(query, data)
        # print(mycursor.statement)
        return mycursor.fetchall()

    @classmethod
    def findOne(cls, query, data=()):
        mycursor = cls._init_engine().cursor(buffered=True, dictionary=True)
        mycursor.execute(query, data)
        # print(mycursor.statement)
        return mycursor.fetchone()

    @classmethod
    def insert(cls, query, val):
        mycursor = cls._init_engine().cursor(buffered=True)
        mycursor.execute(query, val)
        # print(mycursor.statement)
        cls._engine.commit()
        return mycursor.lastrowid
