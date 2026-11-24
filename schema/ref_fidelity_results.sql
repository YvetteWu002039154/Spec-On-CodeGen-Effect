-- UML structural suite run UNCHANGED against the origin repo (impl uml/original):
-- the reference ceiling for structural fidelity. One row per repo; a repo with no
-- recoverable origin (shenmintao__marginalia — deleted upstream) has no row.
-- Source: repos/<repo>/ref_fidelity_results.json (step3_structural_reference.py).
CREATE TABLE ref_fidelity_results (
    repo                TEXT,
    condition           TEXT,
    total               INTEGER,
    passed              INTEGER,
    failed              INTEGER,
    skipped             INTEGER,
    test_case_pass_rate REAL,
    coverage_rate       REAL,
    pass_at_1           REAL,
    failed_tests        TEXT,
    pinned_commit       TEXT,
    stubbed_third_party TEXT,
    PRIMARY KEY (repo)
);
