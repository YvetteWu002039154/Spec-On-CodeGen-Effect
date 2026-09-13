CREATE TABLE human_evaluation (
    repo      TEXT,
    condition TEXT,
    model     TEXT,
    metric    TEXT,
    score     REAL,
    PRIMARY KEY (repo, condition, model, metric)
);
