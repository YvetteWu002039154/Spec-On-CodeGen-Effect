CREATE TABLE IF NOT EXISTS variance_pilot (
    repo                TEXT,
    condition           TEXT,
    adapter             TEXT,
    model               TEXT,
    run                 INTEGER,
    test_case_pass_rate REAL,
    passed              INTEGER,
    failed              INTEGER,
    skipped             INTEGER,
    total               INTEGER,
    pass_at_1           INTEGER,
    failed_tests        TEXT,
    PRIMARY KEY (repo, condition, adapter, model, run)
);
