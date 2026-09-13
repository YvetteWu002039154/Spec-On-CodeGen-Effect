CREATE TABLE generation_runs (
    repo          TEXT,
    condition     TEXT,
    model         TEXT,
    run           INTEGER,
    model_name    TEXT,
    output_tokens INTEGER,
    latency_s     REAL,
    code_chars    INTEGER,
    generated_at  TEXT,
    PRIMARY KEY (repo, condition, model, run)
);
