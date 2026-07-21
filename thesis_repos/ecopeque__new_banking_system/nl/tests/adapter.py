# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def _account(self):
        client = self.m.Individual("Tester", "2000-01-01", "00000000000", "Rua 1")
        return self.m.CurrentAccount(1, client)

    def _deposit(self, acct, amount):
        try:
            acct.deposit(amount)
        except Exception:
            pass

    def _withdraw(self, acct, amount):
        try:
            acct.withdraw(amount)
        except Exception:
            pass

    def _history_count(self, acct):
        return len(acct.history.transactions)

    def new_balance(self):
        return self._account().balance

    def deposit_increase(self):
        acct = self._account()
        self._deposit(acct, 200)
        return acct.balance

    def deposit_zero_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, 0)
        return acct.balance

    def deposit_negative_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, -50)
        return acct.balance

    def deposits_accumulate(self):
        acct = self._account()
        for amt in (100, 200, 300):
            self._deposit(acct, amt)
        return acct.balance

    def withdraw_less(self):
        acct = self._account()
        self._deposit(acct, 500)
        self._withdraw(acct, 300)
        return acct.balance

    def withdraw_over_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 200)
        return acct.balance

    def withdraw_nonpositive_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 0)
        self._withdraw(acct, -25)
        return acct.balance

    def withdraw_full(self):
        acct = self._account()
        self._deposit(acct, 400)
        self._withdraw(acct, 400)
        return acct.balance

    def deposit_recorded(self):
        acct = self._account()
        before = self._history_count(acct)
        self._deposit(acct, 100)
        return self._history_count(acct) - before


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def _account(self):
        client = self.m.PessoaFisica("Tester", "Rua 1", "11144477735")
        return self.m.ContaCorrente(1, "0001", client)

    def _deposit(self, acct, amount):
        try:
            acct.deposit(amount)
        except Exception:
            pass

    def _withdraw(self, acct, amount):
        try:
            acct.withdraw(amount)
        except Exception:
            pass

    def _history_count(self, acct):
        return len(acct.history.all())

    def new_balance(self):
        return self._account().balance

    def deposit_increase(self):
        acct = self._account()
        self._deposit(acct, 200)
        return acct.balance

    def deposit_zero_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, 0)
        return acct.balance

    def deposit_negative_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, -50)
        return acct.balance

    def deposits_accumulate(self):
        acct = self._account()
        for amt in (100, 200, 300):
            self._deposit(acct, amt)
        return acct.balance

    def withdraw_less(self):
        acct = self._account()
        self._deposit(acct, 500)
        self._withdraw(acct, 300)
        return acct.balance

    def withdraw_over_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 200)
        return acct.balance

    def withdraw_nonpositive_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 0)
        self._withdraw(acct, -25)
        return acct.balance

    def withdraw_full(self):
        acct = self._account()
        self._deposit(acct, 400)
        self._withdraw(acct, 400)
        return acct.balance

    def deposit_recorded(self):
        acct = self._account()
        before = self._history_count(acct)
        self._deposit(acct, 100)
        return self._history_count(acct) - before


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def _account(self):
        client = self.m.Client("Tester")
        return self.m.CurrentAccount(1, "0001", client)

    def _deposit(self, acct, amount):
        try:
            acct.deposit(amount)
        except Exception:
            pass

    def _withdraw(self, acct, amount):
        try:
            acct.withdraw(amount)
        except Exception:
            pass

    def _history_count(self, acct):
        return len(acct.transactions)

    def new_balance(self):
        return self._account().balance

    def deposit_increase(self):
        acct = self._account()
        self._deposit(acct, 200)
        return acct.balance

    def deposit_zero_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, 0)
        return acct.balance

    def deposit_negative_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, -50)
        return acct.balance

    def deposits_accumulate(self):
        acct = self._account()
        for amt in (100, 200, 300):
            self._deposit(acct, amt)
        return acct.balance

    def withdraw_less(self):
        acct = self._account()
        self._deposit(acct, 500)
        self._withdraw(acct, 300)
        return acct.balance

    def withdraw_over_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 200)
        return acct.balance

    def withdraw_nonpositive_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 0)
        self._withdraw(acct, -25)
        return acct.balance

    def withdraw_full(self):
        acct = self._account()
        self._deposit(acct, 400)
        self._withdraw(acct, 400)
        return acct.balance

    def deposit_recorded(self):
        acct = self._account()
        before = self._history_count(acct)
        self._deposit(acct, 100)
        return self._history_count(acct) - before


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def _account(self):
        client = self.m.Individual("12345678909", "Tester", "2000-01-01", "Rua 1")
        return self.m.CurrentAccount(1, client)

    def _deposit(self, acct, amount):
        try:
            acct.deposit(amount)
        except Exception:
            pass

    def _withdraw(self, acct, amount):
        try:
            acct.withdraw(amount)
        except Exception:
            pass

    def _history_count(self, acct):
        return len(acct.history.transactions)

    def new_balance(self):
        return self._account().balance

    def deposit_increase(self):
        acct = self._account()
        self._deposit(acct, 200)
        return acct.balance

    def deposit_zero_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, 0)
        return acct.balance

    def deposit_negative_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._deposit(acct, -50)
        return acct.balance

    def deposits_accumulate(self):
        acct = self._account()
        for amt in (100, 200, 300):
            self._deposit(acct, amt)
        return acct.balance

    def withdraw_less(self):
        acct = self._account()
        self._deposit(acct, 500)
        self._withdraw(acct, 300)
        return acct.balance

    def withdraw_over_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 200)
        return acct.balance

    def withdraw_nonpositive_rejected(self):
        acct = self._account()
        self._deposit(acct, 100)
        self._withdraw(acct, 0)
        self._withdraw(acct, -25)
        return acct.balance

    def withdraw_full(self):
        acct = self._account()
        self._deposit(acct, 400)
        self._withdraw(acct, 400)
        return acct.balance

    def deposit_recorded(self):
        acct = self._account()
        before = self._history_count(acct)
        self._deposit(acct, 100)
        return self._history_count(acct) - before


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
