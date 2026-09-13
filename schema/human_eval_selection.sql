CREATE TABLE IF NOT EXISTS human_eval_selection (
    repo           TEXT,
    condition      TEXT,
    model          TEXT,
    cc_run0        INTEGER,
    cell_median_cc REAL,
    iqr            REAL,
    dist_run0      REAL,
    chosen_run     INTEGER,
    updated        TEXT,
    PRIMARY KEY (repo, condition, model)
);
