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

    def vector_search(
        self,
        table_name: str,
        field_names: List[str],
        vector: List[float],
        top_k: int = 10,
        **kwargs,
    ) -> List:
        """
        Perform vector similarity search on the database.

        :param table_name: The name of the table to search in.
        :param field_names: List of field names to return.
        :param vector: The query vector for similarity search.
        :param top_k: The number of top similar results to return.
        :return: A list of top_k similar results from the vector database.
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
        if not self._table_name:
            raise ValueError(
                "VecTable subclasses must define a '_table_name' attribute."
            )
        # put kwargs into the instance
        for key, value in kwargs.items():
            setattr(self, key, value)
        return super().__init__()

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

        # Determine which fields to select
        if "fields" not in kwargs or kwargs["fields"] == "*":
            fields = [
                field.name
                for field in cls.__dict__.values()
                if isinstance(field, Field)
            ]
        else:
            fields = kwargs["fields"]

        # Check if this is a vector search query
        if "vector" in kwargs and "vector_field" in kwargs:
            # Extract vector search parameters
            query_vector = kwargs.pop("vector")
            vector_field = kwargs.pop("vector_field")
            top_k = kwargs.pop("top_k", 10)
            kwargs.pop(
                "fields", None
            )  # Remove fields from kwargs to avoid SQL parameter conflicts

            # Validate that the vector_field exists and is an Embedding field
            embedding_field = None
            for field in cls.__dict__.values():
                if (
                    isinstance(field, Field)
                    and field.name == vector_field
                    and field.field_type == Embedding
                ):
                    embedding_field = field
                    break

            if not embedding_field:
                raise ValueError(
                    f"Vector field '{vector_field}' not found or is not an Embedding field."
                )

            # Perform vector search
            rows = cls._vdb.vector_search(
                cls._table_name, fields, query_vector, top_k, **kwargs
            )
        else:
            # Regular query
            rows = cls._vdb.query(cls._table_name, fields, **kwargs)

        # Process results
        results = []
        for row in rows:
            if isinstance(row, tuple):
                row = {fields[i]: value for i, value in enumerate(row)}

            # For partial field results (like vector search), provide default values for missing fields
            field_defaults = {}
            for field in cls.__dict__.values():
                if isinstance(field, Field):
                    if field.name not in row:
                        # Provide default values for missing fields
                        if field.field_type == str:
                            field_defaults[field.name] = ""
                        elif field.field_type == Embedding:
                            field_defaults[field.name] = []
                        else:
                            field_defaults[field.name] = None

            # Merge row data with defaults
            complete_row = {**field_defaults, **row}
            results.append(cls(**complete_row))
        return results

    @classmethod
    def vector_search(
        cls,
        vector_field: str,
        query_vector: List[float],
        top_k: int = 10,
        fields: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Self]:
        """
        Convenience method for vector similarity search.

        :param vector_field: The name of the embedding field to search on.
        :param query_vector: The query vector for similarity search.
        :param top_k: The number of top similar results to return.
        :param fields: Optional list of field names to return. If None, returns all fields.
        :return: A list of top_k similar results.
        """
        if fields is not None:
            kwargs["fields"] = fields
        kwargs["vector"] = query_vector
        kwargs["vector_field"] = vector_field
        kwargs["top_k"] = top_k
        return cls.select(**kwargs)


if __name__ == "__main__":
    vdb = VectorDB()

    class Student(VecTable):
        _table_name = "students"
        name = Field(name="name", field_type=str)
        age = Field(name="age", field_type=int)
        feature = Field(name="feature", field_type=Embedding, dimension=768)

    # Example usage:
    # Regular select
    # students = Student.select(fields=["name", "age"])

    # Vector search using select method
    # similar_students = Student.select(
    #     vector=[4, 5, 6],
    #     vector_field="feature",
    #     top_k=3,
    #     fields=["name", "age"]
    # )

    # Vector search using convenience method
    # similar_students = Student.vector_search(
    #     vector_field="feature",
    #     query_vector=[4, 5, 6],
    #     top_k=3,
    #     fields=["name", "age"]
    # )
