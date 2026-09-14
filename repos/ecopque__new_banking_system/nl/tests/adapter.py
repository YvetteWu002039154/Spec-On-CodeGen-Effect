import os

# Several generations validate the Brazilian CPF check digits, so the client
# identifier has to be a genuinely valid one — a placeholder like "1" is refused
# at construction and would score the generation 0 for a reason unrelated to the
# contract.
CPF = "11144477735"


# ── generation spec ─────────────────────────────────────────────────────────

class Gen:
    """One generation's concrete recipe: build an account, then five primitives."""

    def __init__(self, make, dep, wd, bal, hist, rec=None):
        self.make, self.dep, self.wd, self.bal, self.hist = make, dep, wd, bal, hist
        # rec: the route that writes history, when it is not plain deposit()
        self.rec = rec or dep


# ── executor: the 10 contract behaviours, identical for every generation ────

class SpecDriver:
    def __init__(self, gen, module):
        self.g, self.m = gen, module

    def _acct(self):
        return self.g.make(self.m)

    def _bal(self, a):
        return self.g.bal(self.m, a)

    def _dep(self, a, v):
        try:
            self.g.dep(self.m, a, v)
        except Exception:  # noqa: BLE001 — a raise IS the rejection signal
            pass

    def _wd(self, a, v):
        try:
            self.g.wd(self.m, a, v)
        except Exception:  # noqa: BLE001
            pass

    # N1
    def new_balance(self):
        return self._bal(self._acct())

    # N2
    def deposit_increase(self):
        a = self._acct()
        self._dep(a, 200)
        return self._bal(a)

    # N3
    def deposit_zero_rejected(self):
        a = self._acct()
        self._dep(a, 100)
        self._dep(a, 0)
        return self._bal(a)

    # N4
    def deposit_negative_rejected(self):
        a = self._acct()
        self._dep(a, 100)
        self._dep(a, -50)
        return self._bal(a)

    # N9
    def deposits_accumulate(self):
        a = self._acct()
        for amt in (100, 200, 300):
            self._dep(a, amt)
        return self._bal(a)

    # N5
    def withdraw_less(self):
        a = self._acct()
        self._dep(a, 500)
        self._wd(a, 300)
        return self._bal(a)

    # N6
    def withdraw_over_rejected(self):
        a = self._acct()
        self._dep(a, 100)
        self._wd(a, 200)
        return self._bal(a)

    # N7
    def withdraw_nonpositive_rejected(self):
        a = self._acct()
        self._dep(a, 100)
        self._wd(a, 0)
        self._wd(a, -25)
        return self._bal(a)

    # N8
    def withdraw_full(self):
        a = self._acct()
        self._dep(a, 400)
        self._wd(a, 400)
        return self._bal(a)

    # N10 — a history entry only counts if the deposit actually happened
    def deposit_recorded(self):
        a = self._acct()
        before = self.g.hist(self.m, a)
        start = self._bal(a)
        try:
            self.g.rec(self.m, a, 100)
        except Exception:  # noqa: BLE001
            return 0
        if self._bal(a) != start + 100:
            return 0
        return self.g.hist(self.m, a) - before


# ── shared readers (named per generation below, never searched) ─────────────

def _bal_attr(_m, a):
    return a.balance


def _hist_txns(_m, a):
    """account.history.transactions — claude / gemini shape."""
    return len(a.history.transactions)


def _hist_seq(_m, a):
    """account.history is itself the sequence — gpt run1/2/3 shape."""
    return len(a.history)


def _hist_all(_m, a):
    """account.history.all() — gpt run0 shape."""
    return len(a.history.all())


def _hist_txn_attr(_m, a):
    """account.transactions — deepseek run0/2/3 shape."""
    return len(a.transactions)


def _dep_m(_m, a, v):
    a.deposit(v)


# Which deposit route writes history differs per generation: for some the bare
# deposit() appends the record, for others only the transaction-object route
# does while deposit() just moves the balance. Each generation names its own
# below via Gen(rec=...); default is that deposit() records.
def _rec_register(m, a, v):
    m.Deposit(v).register(a)


def _rec_execute(m, a, v):
    m.Deposit(v).execute(a)


def _rec_perform(m, a, v):
    a.perform(m.Deposit(v))


def _wd_m(_m, a, v):
    a.withdraw(v)


# ── the 4 run0 generations (the main study scores run0 only) ───────────────

GENERATIONS = {
    # claude — Account/SavingsAccount with a History object
    "claude": Gen(
        make=lambda m: m.SavingsAccount(1, m.Individual("A", "01-01-1990", CPF, "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
    # gpt — names its classes in Portuguese at run0 (ContaPoupanca / PessoaFisica)
    "gpt": Gen(
        make=lambda m: m.ContaPoupanca(1, "0001", m.PessoaFisica("A", "addr", CPF)),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_all, rec=_rec_perform),
    # deepseek — account exposes `transactions` (run0/2/3) or `statement()` (run1)
    "deepseek": Gen(
        make=lambda m: m.SavingsAccount(1, "0001", m.IndividualClient("A", CPF)),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txn_attr),
    # gemini — SavingsAccount(number, client); run3 keeps only CurrentAccount
    "gemini": Gen(
        make=lambda m: m.SavingsAccount(1, m.Individual(CPF, "A", "01-01-1990", "addr")),
        dep=_dep_m, wd=_wd_m, bal=_bal_attr, hist=_hist_txns, rec=_rec_register),
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return SpecDriver(GENERATIONS[model], module)
