import itertools
import sqlite3

from fastapi import FastAPI

from monitor import __version__
from monitor.config import STORAGE_PATH

if not STORAGE_PATH.is_dir():
    STORAGE_PATH.mkdir(exist_ok=True, parents=True)

db = sqlite3.connect(STORAGE_PATH / "timeseries.db")

if not db.execute("PRAGMA table_info('metrics');").fetchone():
    sql_statemtents = (
        """CREATE TABLE "metrics" (
            "metric_id"	INTEGER NOT NULL UNIQUE,
            "timestamp"	BLOB NOT NULL,
            "name"	TEXT NOT NULL,
            "value"	TEXT NOT NULL,
            "hostname"	TEXT,
            "labels"	TEXT,
            PRIMARY KEY("metric_id" AUTOINCREMENT)
        ); """,
        'CREATE INDEX "timestamp_idx" ON "metrics" ("timestamp"	DESC);',
        'CREATE INDEX "hostname_idx" ON "metrics" ( "hostname");',
        'CREATE INDEX "name_idx" ON "metrics" ( "name");',
    )
    [db.execute(sql) for sql in sql_statemtents]
    db.commit()


def f(query, start, end):
    name = query.split("{")
    if len(name) == 1:
        name = name[0]
        option_sql = ""
    else:
        name, option = name[0], name[1][:-1]

        option_sql = ""
        for s in option.split(","):
            key, value = s.split("=")
            option_sql += f"\nand {key} = '{value}'"

    sql = f"""select timestamp, value, hostname
            from metrics
            where
                timestamp >= {start}
                and timestamp <= {int(end)+5}
                and name = '{name}'
                {option_sql}
            order by hostname"""
    print(sql)
    return db.execute(sql).fetchall()


v1 = FastAPI()


@v1.get("/status/buildinfo")
async def _():
    return {"version": __version__}


@v1.get("/query_range")
async def _(query, start, end):
    data = f(query, int(start), int(end))

    result = []
    for hostname, data in itertools.groupby(data, lambda x: x[-1]):
        result.append(
            {
                "metric": {"__name__": query, "hostname": hostname},
                "values": list([(x[0], x[1]) for x in data]),
            }
        )
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": result,
        },
    }


@v1.get("/label/__name__/values")
async def _():
    return {
        "status": "success",
        "data": [
            "f1",
            "f2",
            "f3",
        ],
    }


"""

@v1.get("/query")
async def _(query, time):
    print(query, time)
    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "__name__": "w00t",
                        # "job": "prometheus",
                        "instance": "localhost:9090",
                    },
                    "values": [
                        [1731442575.781, "9"],
                    ],
                },
                {
                    "metric": {
                        "__name__": "y0l0",
                        # "job": "node",
                        "instance": "localhost:9091",
                    },
                    "values": [
                        [1731442556, "1"],
                    ],
                },
            ],
        },
    }


@v1.get("/series")
async def _():
    return {
        "status": "success",
        "data": [
            {"__name__": "up", "job": "prometheus", "instance": "localhost:9090"},
            {"__name__": "up", "job": "node", "instance": "localhost:9091"},
            {
                "__name__": "process_start_time_seconds",
                "job": "prometheus",
                "instance": "localhost:9090",
            },
        ],
    }


# @v1.get("/label/__name__/values")
async def _():
    return {
        "status": "success",
        "data": [
            "quantile",
            "reason",
            "role",
            "scrape_job",
            "slice",
            "version",
        ],
    }


# @v1.get("/label/{label}")
async def _():
    return {"status": "success", "data": ["node", "prometheus"]}


@v1.get("/labels")
async def _():
    return {
        "status": "success",
        "data": [
            "quantile",
            "reason",
            "role",
            "scrape_job",
            "slice",
            "version",
        ],
    }

"""
