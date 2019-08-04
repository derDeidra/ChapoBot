from sqlalchemy import create_engine, select
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Boolean
from sqlalchemy.engine import Connection

_con_str = 'sqlite:///{db_name}.db'


class Database(object):

    def __init__(self, db_name):
        """
        Create a new Database instance
        """
        self._engine = create_engine(_con_str.format(db_name=db_name))
        self._metadata = MetaData(self._engine)
        self._replied_to = Table('Replied_To', self._metadata,
                                 Column('Identifier', String, primary_key=True),
                                 Column('Poster', String),
                                 Column('Is_Pure', Boolean)
                                 )
        if not self._engine.dialect.has_table(self._engine, 'Replied_To'):
            self._metadata.create_all()
        self._con = None

    def _get_connection(self) -> Connection:
        """
        Get or create a cached sqlite connection
        :return: the connection object
        """
        if self._con is None:
            self._con = self._engine.connect()
        return self._con

    def identifier_exists(self, identifier: str) -> bool:
        """
        Determine if a comment or post identifier has been scanned
        :param identifier: the identifier
        :return: whether or not it has been scanned
        """
        stmt = select([self._replied_to.c.Identifier]).where(self._replied_to.c.Identifier == identifier)
        result = self._get_connection().execute(stmt)
        return len(list(result)) > 0

    def insert_new_record(self, identifier: str, poster: str, is_pure: bool) -> None:
        """
        Insert a new identifier record
        :param identifier: the identifier
        :param poster:     the poster
        :param is_pure:    the poster purity flag
        """
        ins = self._replied_to.insert().values(
            Identifier=identifier,
            Poster=poster,
            Is_Pure=is_pure
        )
        self._get_connection().execute(ins)
