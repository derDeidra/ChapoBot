from sqlalchemy import create_engine, select
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Boolean
from sqlalchemy.engine import Connection

_con_str = 'sqlite:///ChapoBot.db'


class Database(object):

    def __init__(self):
        self._engine = create_engine(_con_str)
        self._metadata = MetaData(self._engine)
        self._replied_to = Table('Replied_To', self._metadata,
                                 Column('identifier', String, primary_key=True),
                                 Column('poster', String),
                                 Column('chapo', Boolean)
                                 )
        if not self._engine.dialect.has_table(self._engine, 'Replied_To'):
            self._metadata.create_all()
        self._con = None

    def _get_connection(self) -> Connection:
        if self._con is None:
            self._con = self._engine.connect()
        return self._con

    def identifier_exists(self, identifier: str) -> bool:
        stmt = select([self._replied_to.c.identifier]).where(self._replied_to.c.identifier == identifier)
        result = self._get_connection().execute(stmt)
        return len(list(result)) > 0

    def insert_new_record(self, identifier: str, poster: str, chapo: bool) -> None:
        ins = self._replied_to.insert().values(
            identifier=identifier,
            poster=poster,
            chapo=chapo
        )
        self._get_connection().execute(ins)
