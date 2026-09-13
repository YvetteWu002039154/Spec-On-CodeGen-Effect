"""Per-(model, run) drivers for the variance pilot — ecopque__new_banking_system.

Extends the main study's drivers to runs 1-3. Run 0 is NOT redefined here: it is
imported from repos/ecopque__new_banking_system/nl/tests/adapter.py, so the
generation the main study scores and the generation the pilot calls "run 0" are
driven by literally the same code. Everything else — Gen, SpecDriver, the Tk
stand-ins, the per-architecture builders — is imported from there too, so there
is one implementation and the pilot cannot drift from the instrument it is
supposed to be validating.

Only the run1-3 recipes are new. A regeneration is a different program: see the
drift table in the main adapter's docstring.
"""

import importlib.util
import os
import re
import sys

_MAIN_TESTS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "repos", "ecopque__new_banking_system", "nl", "tests"))


def _load_main_adapter():
    """Load the repo's adapter.py by PATH, under a repo-unique module name.

    Deliberately not `sys.path.insert(_MAIN_TESTS); import adapter`:

      * that puts the repo's tests dir ahead of this one on sys.path, so
        `from loader import ...` in test_conformance.py would silently resolve
        to the repo's loader.py instead of the copy next to this file;
      * `import adapter` caches under the bare name "adapter", so loading two
        repos' pilots in one process would hand the second repo the first
        repo's drivers — silently, whenever the two happen to define the same
        names.

    Loading by path under a unique name avoids both.
    """
    name = "main_adapter_" + re.sub(r"\W", "_", "ecopque__new_banking_system")
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(_MAIN_TESTS, "adapter.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


_main = _load_main_adapter()

# machinery + builders — one implementation, defined in the main adapter
CPF = _main.CPF
Gen = _main.Gen
SpecDriver = _main.SpecDriver
_bal_attr = _main._bal_attr
_dep_m = _main._dep_m
_hist_seq = _main._hist_seq
_hist_txn_attr = _main._hist_txn_attr
_hist_txns = _main._hist_txns
_rec_execute = _main._rec_execute
_rec_perform = _main._rec_perform
_rec_register = _main._rec_register
_wd_m = _main._wd_m
_RUN0 = _main.GENERATIONS


GENERATIONS = {(m, 0): g for m, g in _RUN0.items()}
GENERATIONS.update({
    ("claude", 1): Gen(
        make=lambda m: m.SavingsAccount(m.Individual("A", CPF, "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
    ("claude", 2): Gen(
        make=lambda m: m.SavingsAccount(m.Individual("A", CPF, "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
    ("claude", 3): Gen(
        make=lambda m: m.SavingsAccount(m.Individual("A", CPF, "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
    ("gpt", 1): Gen(
        make=lambda m: m.ContaPoupanca(1, "0001", m.PessoaFisica("A", CPF, "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_seq, rec=_rec_perform),
    ("gpt", 2): Gen(
        make=lambda m: m.ContaPoupanca(1, "0001", m.PessoaFisica("A", CPF)),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_seq),
    ("gpt", 3): Gen(
        make=lambda m: m.SavingsAccount(1, "0001", m.Individual("A", CPF, "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_seq),
    ("deepseek", 1): Gen(
        make=lambda m: m.SavingsAccount(1, "0001", m.Individual("A", "addr", CPF)),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr,
        hist=lambda _m, a: len(a.statement())),
    ("deepseek", 2): Gen(
        make=lambda m: m.SavingsAccount(1, "0001", m.Individual("A", "addr", CPF)),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txn_attr),
    ("deepseek", 3): Gen(
        make=lambda m: m.SavingsAccount("0001", 1, m.Individual("A", CPF)),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txn_attr),
    ("gemini", 1): Gen(
        make=lambda m: m.SavingsAccount(1, m.Individual(CPF, "A", "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_execute),
    ("gemini", 2): Gen(
        make=lambda m: m.SavingsAccount(1, m.Individual(CPF, "A", "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
    ("gemini", 3): Gen(
        make=lambda m: m.SavingsAccount(1, m.Individual(CPF, "A", "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
})


def build_driver(model, module):
    """Dispatch on (model, RUN) — a regeneration is a different program."""
    run = int(os.environ.get("RUN", "0"))
    try:
        gen = GENERATIONS[(model, run)]
    except KeyError:
        raise KeyError(f"no hand-written driver for {model}.run{run}") from None
    return SpecDriver(gen, module)
