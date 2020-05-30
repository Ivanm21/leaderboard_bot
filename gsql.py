
import datetime
import logging
import os

import sqlalchemy

# from model import  Activity


# Remember - storing secrets in plaintext is potentially unsafe. Consider using
# something like https://cloud.google.com/kms/ to help keep secrets secret.
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

print(db_user, db_pass, db_name, cloud_sql_connection_name)
logger = logging.getLogger()

def ensure_connection(func):
    """
    Decorator to connect to db
    """
    def inner(*args, **kwargs):
        db = sqlalchemy.create_engine(
    # Equivalent URL:
    # mysql+pymysql://<db_user>:<db_pass>@/<db_name>?unix_socket=/cloudsql/<cloud_sql_instance_name>
            sqlalchemy.engine.url.URL(
                drivername="mysql+pymysql",
                username=db_user,
                password=db_pass,
                host='127.0.0.1',
                port=3306,
                database=db_name,
                # query={"unix_socket": "/cloudsql/{}".format(cloud_sql_connection_name)},
            ),
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,  # 30 seconds
            pool_recycle=1800,  # 30 minutes

        )

        with db.connect() as conn:
            kwargs['conn'] = conn
            res = func(*args, **kwargs)
        return res

    return inner


@ensure_connection
def init_db(conn):
    # Create tables (if they don't already exist)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS activities "
        " ( activity_id SERIAL NOT NULL AUTO_INCREMENT, time_created timestamp NOT NULL,  "
        " points INT NOT NULL, author_user_id INT, activity_name  VARCHAR(255), PRIMARY KEY (activity_id) );"
    )

@ensure_connection
def drop_table(conn, table:str):
    conn.execute(
        f"DROP TABLE {table};"
    )

@ensure_connection
def save_activity(conn, name:str, points:int, author:int):

    conn.execute(
        f"INSERT INTO activities (time_created, points, author_user_id, activity_name) VALUES ( CURRENT_TIMESTAMP,{points},{author}, '{name}'  )"
    )
    

# drop_table(table='activities')



