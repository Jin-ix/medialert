from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

engine = create_engine("sqlite:///./test_users.db")
metadata = MetaData()

users = Table('users', metadata,
              Column('id', Integer, primary_key=True),
              Column('username', String),
              Column('password_hash', String)
)

metadata.create_all(engine)
print("DB and table created successfully!")
