CREATE TABLE status_copy
(
    host          TEXT NOT NULL,
    url           TEXT NOT NULL,
    ip            TEXT,
    latency       INTEGER,
    last_checked  INTEGER,
    interval      INTEGER,
    status        INTEGER,
    uptime        INTEGER,
    country       TEXT,
    country_code  TEXT,
    network       TEXT,
    added         TEXT,
    historic      TEXT,
    last_downtime INTEGER,
    last_uptime   INTEGER,
    PRIMARY KEY (host)
);
INSERT INTO status_copy
SELECT host,
       url,
       ip,
       latency,
       last_checked,
       interval,
       status,
       uptime,
       country,
       country_code,
       network,
       added,
       historic,
       last_downtime,
       last_uptime
FROM status;
DROP TABLE status;
ALTER TABLE status_copy
    RENAME TO status;
