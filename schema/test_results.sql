CREATE TABLE test_results (
    repo            TEXT,
    variant         TEXT,
    condition       TEXT,
    model           TEXT,
    total           INTEGER,
    passed          INTEGER,
    failed          INTEGER,
    skipped         INTEGER,
    test_case_pass_rate REAL,
    coverage_rate   REAL,
    pass_at_1       REAL,
    n_runs_averaged INTEGER,
    failed_tests    TEXT,
    PRIMARY KEY (repo, variant)
);
