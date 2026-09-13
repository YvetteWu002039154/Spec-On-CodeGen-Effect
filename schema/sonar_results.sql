CREATE TABLE sonar_results (
    repo                     TEXT,
    variant                  TEXT,
    condition                TEXT,
    model                    TEXT,
    run                      INTEGER,
    project_key              TEXT,
    bugs                     INTEGER,
    vulnerabilities          INTEGER,
    code_smells              INTEGER,
    ncloc                    INTEGER,
    lines                    INTEGER,
    complexity               INTEGER,
    cognitive_complexity     INTEGER,
    duplicated_lines_density REAL,
    comment_lines_density    REAL,
    error                    TEXT,
    PRIMARY KEY (repo, variant)
);
