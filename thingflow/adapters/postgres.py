# Copyright 2016 by MPI-SWS and Data-Ken Research.
# Licensed under the Apache 2.0 License.
from thingflow.base import BlockingInputThing, OutputThing, DirectOutputThingMixin,\
                           FatalError, SensorEvent
from thingflow.adapters.generic import EventRowMapping

import datetime
import psycopg2

class DatabaseMapping(EventRowMapping):
    def __init__(self, table_name):
        """Define how we map between the event and database world for
        a given port. field_to_colname mappings should be a list
        of (field_name, column_name) pairs.
        """
        self.table_name = table_name
        self.insert_sql = "insert into %s (%s) values (%s);" % \
                          (table_name,
                           ', '.join(self.get_col_names()),
                           ', '.join(['%s']*len(self.get_col_names())))
        self.query_sql = "select %s from %s order by id asc;" % \
                         (', '.join(self.get_col_names()), table_name)

    def get_col_names(self):
        """Return the column names for use in sql statements
        """
        raise NotImplemented

    def event_to_row(self, event):
        """Convert an event to a tuple of values suitable for use as sql
        bind values for a single row.
        """
        raise NotImplemented

    def row_to_event(self, row):
        """Given a tuple representing a row of results returned by a sql
        select, return an event
        """
        raise NotImplemented

    
class SensorEventMapping(DatabaseMapping):
    def __init__(self, table_name):
        super().__init__(table_name)

    def get_col_names(self):
        return ['ts', 'sensor_id', 'val']

    def event_to_row(self, event):
        return (datetime.datetime.fromtimestamp(event.ts), event.sensor_id, event.val)

    def row_to_event(self, row):
        assert len(row)==3, "Expecting 3 elements, got '%s'" % row.__repr__()
        #dt = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        return SensorEvent(ts=row[0].timestamp(), sensor_id=row[1], val=row[2])

def create_sensor_table(conn, table_name, drop_if_exists=False):
    """Utility function to create a sensor event table.
    """
    seqname = table_name + '_seq'
    cur = conn.cursor()
    def exe(stmt):
        print(stmt)
        cur.execute(stmt)
    if drop_if_exists:
        exe("drop table if exists %s" % table_name)
        exe("drop sequence if exists %s;" % seqname)
    exe("create sequence %s" % seqname)
    exe("create table %s(id bigint NOT NULL DEFAULT nextval('%s'), ts timestamp NOT NULL, sensor_id integer NOT NULL, val double precision NOT NULL);" %
                 (table_name, seqname))
    exe("create unique index on %s (id);" % table_name)
    exe("create index on %s (ts);" % table_name)
    exe("create index on %s (sensor_id);" % table_name)
    conn.commit()
    cur.close()

def delete_sensor_table(conn, table_name):
    """Utility funtion to delete a sensor event table and its associated sequence.
    """
    seqname = table_name + '_seq'
    cur = conn.cursor()
    def exe(stmt):
        print(stmt)
        cur.execute(stmt)
    exe("drop table if exists %s" % table_name)
    exe("drop sequence if exists %s;" % seqname)
    

class PostgresWriter(BlockingInputThing):
    """Write the events to the database.
    """
    def __init__(self, scheduler, connect_string, mapping):
        self.mapping = mapping
        self.conn = psycopg2.connect(connect_string)
        super().__init__(scheduler)

    def _on_next(self, port, x):
        data = self.mapping.event_to_row(x)
        cur = self.conn.cursor()
        cur.execute(self.mapping.insert_sql,data)
        print("%s %s" % (self.mapping.insert_sql, data.__repr__()))
        self.conn.commit()
        cur.close()

    def _on_completed(self, port):
        pass

    def _on_error(self, port):
        pass

    def _close(self):
        self.conn.close()


class PostgresReader(OutputThing, DirectOutputThingMixin):
    """Read a row from the table to the default port each
    time _observe() is called. Note that this output_thing signals
    completed when it finishes the query. We could also imagine a
    version that keeps looking for new rows, re-running the query
    as needed.
    """
    def __init__(self, connect_string, mapping):
        self.conn = psycopg2.connect(connect_string)
        self.mapping = mapping
        self.cur = None
        super().__init__()

    def _observe(self):
        try:
            if not self.cur:
                self.cur = self.conn.cursor()
                print(self.mapping.query_sql)
                self.cur.execute(self.mapping.query_sql)
            row = self.cur.fetchone()
            if row is not None:
                self._dispatch_next(self.mapping.row_to_event(row))
                return True
            else:
                if self.cur:
                    self.cur.close()
                self.conn.close()
                self._dispatch_completed()
                return False
        except FatalError:
            raise
        except Exception as e:
            if self.cur:
                self.cur.close()
            self.conn.close()
            self._dispatch_error(e)
            return False
        
