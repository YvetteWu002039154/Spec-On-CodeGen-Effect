from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

class A001_TransactionCLS(ABC):
    def __init__(self, value: float):
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        pass

class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance += self.A001_value
        desc = f"Deposit: {self.A001_value}"
        account.C001_history.B001_add_transactionMTD(desc)

class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance -= self.A001_value
        desc = f"Withdrawal: {self.A001_value}"
        account.C001_history.B001_add_transactionMTD(desc)

class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: List[dict] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if description.startswith("Deposit"):
            typ = "deposit"
        elif description.startswith("Withdrawal"):
            typ = "withdraw"
        else:
            typ = "unknown"
        self.B001_transactions.append({"description": description, "type": typ})

    def B001_transaction_generatorMTD(self, filter_type: str) -> 'E001_IteratorAccountCLS':
        return E001_IteratorAccountCLS(self.B001_transactions, filter_type)

class E001_IteratorAccountCLS:
    def __init__(self, transactions: List[dict], filter_type: str):
        self._transactions = transactions
        self._filter_type = filter_type.lower()
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        while self._index < len(self._transactions):
            trans = self._transactions[self._index]
            self._index += 1
            if self._filter_type == 'all' or trans['type'] == self._filter_type:
                return trans
        raise StopIteration

class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, birth: date, address: str):
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_birth = birth
        self.D001_address = address
        self.D001_accounts: List['C001_AccountCLS'] = []

    def D001_add_accountMTD(self, account: 'C001_AccountCLS') -> None:
        self.D001_accounts.append(account)

class C001_AccountCLS:
    def __init__(self, number: str, agency: str, client: D001_ClientCLS,
                 limit: int = 1000, daily_trans_limit: int = 10):
        self.C001_number = number
        self.C001_agency = agency
        self.C001_client = client
        self.C001_limit = limit
        self.C001_balance = 0
        self.C001_daily_trans_count = 0
        self.C001_daily_trans_limit = daily_trans_limit
        self.C001_history = B001_HistoryCLS()
        self.C001_last_trans_date: Optional[date] = None

    def _C001__reset_transaction_count_if_new_dayMTD(self):
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Deposit value must be positive")
        deposit = A002_DepositCLS(value)
        deposit.A001_registerMTD(self)

    def C001_withdrawMTD(self, value: float) -> None:
        self._C001__reset_transaction_count_if_new_dayMTD()
        if value <= 0:
            raise ValueError("Withdrawal value must be positive")
        if value > self.C001_limit:
            raise ValueError("Withdrawal exceeds per-transaction limit")
        if value > self.C001_balance:
            raise ValueError("Insufficient balance")
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise Exception("Daily transaction limit reached")

        withdraw = A003_WithdrawCLS(value)
        withdraw.A001_registerMTD(self)
        self.C001_daily_trans_count += 1

    def C001_transaction_reportMTD(self, filter_type: str) -> E001_IteratorAccountCLS:
        return self.C001_history.B001_transaction_generatorMTD(filter_type)

class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, number: str, agency: str, client: D001_ClientCLS,
                 limit: int = 1000, daily_trans_limit: int = 10,
                 limit_withdrawals: int = 5):
        super().__init__(number, agency, client, limit, daily_trans_limit)
        self.C002_limit_withdrawals = limit_withdrawals
        self.C002_number_withdrawals = 0

    def _reset_transaction_and_withdrawals_if_new_day(self):
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C002_number_withdrawals = 0
            self.C001_last_trans_date = today

    def _C001__reset_transaction_count_if_new_dayMTD(self):
        self._reset_transaction_and_withdrawals_if_new_day()

    def C002_withdrawMTD(self, value: float) -> None:
        self._reset_transaction_and_withdrawals_if_new_day()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise Exception("Daily withdrawal count limit reached")
        self.C002_number_withdrawals += 1
        try:
            super().C001_withdrawMTD(value)
        except:
            self.C002_number_withdrawals -= 1
            raise

class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> int:
        return self.C001_balance

    def C003_limitMTD(self) -> int:
        return self.C001_limit