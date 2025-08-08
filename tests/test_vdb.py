import pytest

from vagents.core.vdb import VectorDB, VecTable, Field, Embedding


def test_vetable_registration_and_defaults():
    class DummyDB(VectorDB):
        def create_table(self, table_name: str, attributes: dict, **kwargs):
            self.created = (table_name, attributes)

        def query(self, table_name: str, field_names, **kwargs):
            # Return partial row missing some fields to trigger defaults
            return [{"name": "alice"}]

        def insert(self, table_name: str, data: dict):
            self.last_insert = (table_name, data)

        def create_index(self, table_name: str, field_name: str):
            # record index creation
            self.index = (table_name, field_name)

    db = DummyDB()

    class Person(VecTable):
        _table_name = "people"
        _vdb = db
        name = Field("name", str)
        age = Field("age", int)
        vec = Field("vec", Embedding, dimension=3)

    # create_all should call create_table and index creation for embedding
    db.create_all()
    assert hasattr(db, "created")
    assert getattr(db, "index", None) == ("people", "vec")

    # select should fill defaults for missing fields
    rows = Person.select()
    assert len(rows) == 1
    p = rows[0]
    assert p.name == "alice"
    # Default for int becomes None, for Embedding becomes []
    assert getattr(p, "age") is None
    assert getattr(p, "vec") == []


def test_vetable_insert_calls_db_insert():
    class DummyDB(VectorDB):
        def insert(self, table_name: str, data: dict):
            self.called = (table_name, data)

        def create_table(self, *a, **k):
            pass

        def query(self, *a, **k):
            return []

    db = DummyDB()

    class Doc(VecTable):
        _table_name = "docs"
        _vdb = db
        title = Field("title", str)
        feature = Field("feature", Embedding, dimension=2)

    d = Doc(title="t", feature=[0.1, 0.2])
    d.insert()
    assert db.called[0] == "docs"
    assert db.called[1]["title"] == "t"
    assert db.called[1]["feature"] == [0.1, 0.2]
