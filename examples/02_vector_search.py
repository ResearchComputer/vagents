from vagents.core import VecTable, Embedding, Field
from vagents.contrib.impl.libsql_vdb import LibSQLVDB

vdb = LibSQLVDB(conn_string=".local/sqlite.db")


class Student(VecTable):
    _table_name = "student"
    _vdb = vdb

    name = Field(name="name", field_type=str)
    age = Field(name="age", field_type=int)
    feature = Field(name="feature", field_type=Embedding, dimension=3)

    def __init__(self, name: str, age: int, feature: list):
        self.name = name
        self.age = age
        self.feature = feature


if __name__ == "__main__":
    vdb.create_all()
    s1 = Student(name="Alice", age=20, feature=[0.1, 0.2, 0.3])
    success = s1.insert()
    print(f"Insert success: {success}")
    # students = Student.select()
    # print("Students:", students)
