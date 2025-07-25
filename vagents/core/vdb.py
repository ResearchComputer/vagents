from typing import Dict, Optional, List
from typing_extensions import Self

__ALL_TABLES__ = {}


class Field:
    def __init__(self, name: str, field_type: type, **kwargs):
        self.name = name
        self.field_type = field_type
        self.kwargs = kwargs


class Embedding:
    def __init__(self, vector: list):
        self.vector = vector


class VectorDB:
    def __init__(self):
        pass

    def create_table(self, table_name: str, attributes: dict, **kwargs):
        """
        Create a table in the vector database if it does not already exist.

        Each subclass should implement this method to create a table with the specified attributes. They should map the attributes to the database schema.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def query(self, table_name: str, field_names: List[str], **kwargs) -> List:
        """
        Query the vector database with a given query string and return the top_k results.

        :param query: The query string to search for.
        :param top_k: The number of top results to return.
        :return: A list of top_k results from the vector database.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def insert(self, table_name: str, data: Dict):
        """
        Insert a list of data into the vector database.

        :param data: A list of data to insert into the vector database.
        :return: None
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

    def create_all(self):
        """
        Create all tables defined in the __ALL_TABLES__ dictionary.

        This method should be called to ensure that all tables are created in the vector database.
        """
        for table_name, table_columns in __ALL_TABLES__.items():
            self.create_table(table_name, table_columns)
        # create index for embedding fields
        for table_name, table_columns in __ALL_TABLES__.items():
            for field_name, field in table_columns.items():
                if isinstance(field, Field) and field.field_type == Embedding:
                    self.create_index(table_name, field_name)

    def create_index(self, table_name: str, field_name: str):
        """
        Create an index on a specific field in the table.

        :param table_name: The name of the table to create the index on.
        :param field_name: The name of the field to index.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class VecTableMeta(type):
    def __new__(cls, name, bases, attrs):
        return super().__new__(cls, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        if not hasattr(cls, "_table_name"):
            raise ValueError(
                "VecTable subclasses must define a 'table_name' attribute."
            )

        if cls._table_name:
            cls._table_name = cls._table_name.lower() or name.lower()
            columns = {k: v for k, v in attrs.items() if isinstance(v, Field)}
            __ALL_TABLES__[cls._table_name] = columns


class VecTable(metaclass=VecTableMeta):
    _table_name: Optional[str] = None
    _vdb: Optional[VectorDB] = None

    def __init__(self, **kwargs):
        return super().__init__(**kwargs)

    def insert(self):
        if not self._vdb:
            raise ValueError("VectorDB instance is not set for this VecTable.")
        data = {
            field.name: getattr(self, field.name)
            for field in self.__class__.__dict__.values()
            if isinstance(field, Field)
        }
        return self._vdb.insert(self._table_name, data)

    @classmethod
    def select(cls, **kwargs) -> List[Self]:
        if not cls._vdb:
            raise ValueError("VectorDB instance is not set for this VecTable.")
        if "fields" not in kwargs or kwargs["fields"] == "*":
            fields = [
                field.name
                for field in cls.__dict__.values()
                if isinstance(field, Field)
            ]
        else:
            fields = kwargs["fields"]
        rows = cls._vdb.query(cls._table_name, fields, **kwargs)
        results = []
        for row in rows:
            if isinstance(row, tuple):
                row = {fields[i]: value for i, value in enumerate(row)}
            results.append(cls(**row))
        return results


if __name__ == "__main__":
    vdb = VectorDB()

    class Student(VecTable):
        _table_name = "students"
        name = Field(name="name", field_type=str)
        age = Field(name="age", field_type=int)
        feature = Field(name="feature", field_type=Embedding, dimension=3)
