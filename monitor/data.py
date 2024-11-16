import sqlite3
import polars as pl
import datetime as dt

from monitor import STORAGE_PATH

"""
CREATE TABLE "metrics" (
	"metric_id"	INTEGER NOT NULL UNIQUE,
	"timestamp"	BLOB NOT NULL,
	"name"	TEXT NOT NULL,
	"value"	TEXT NOT NULL,
	"hostname"	TEXT,
	"labels"	TEXT,
	PRIMARY KEY("metric_id" AUTOINCREMENT)
);

CREATE INDEX "timestamp_idx" ON "metrics" (
	"timestamp"	DESC
);

CREATE INDEX "hostname_idx" ON "metrics" (
	"hostname"
);
"""

db = sqlite3.connect(STORAGE_PATH / "timeseries.db")

for i in range(1731489675, 1731489795):
    db.execute(
        f"INSERT INTO metrics (timestamp, name, value, hostname) VALUES ({i},'test',{str(i - 1731489675)}, {})"
    )
    db.commit()
exit()

df = pl.DataFrame(
    {
        "timestamp": timestamp,
        "value": value,
        "name": name,
    }
)

df.write_parquet(STORAGE_PATH / "data.parquet")
