from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Generator, Optional, Union

class A001_TransactionCLS(ABC):
    def __init__(self, value: float):
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account: C001_AccountCLS) -> None:
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: C001_AccountCLS) -> None:
        account.C001_depositMTD(self.A001_value)


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: C001_AccountCLS) -> None:
        account.C001_withdrawMTD(self.A001_value)


class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: str) -> Generator[str, None, None]:
        for desc in self.B001_transactions:
            if filter_type == "all" or filter_type in desc.lower():
                yield desc


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, address: str, birth: date):
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_address = address
        self.D001_birth = birth
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        self.D001_accounts.append(account)


class C001_AccountCLS:
    def __init__(self, agency: str, number: int, client: Optional[D001_ClientCLS] = None,
                 balance: int = 0, limit: int = 0,
                 daily_trans_limit: int = 10):
        self.C001_agency = agency
        self.C001_number = number
        self.C001_balance = balance
        self.C001_limit = limit
        self.C001_daily_trans_count = 0
        self.C001_daily_trans_limit = daily_trans_limit
        self.C001_last_trans_date: Optional[date] = None
        self.C001_history = B001_HistoryCLS()
        self.C001_client = client
        if client:
            client.D001_add_accountMTD(self)

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Deposit value must be positive")
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached")
        self.C001_balance += int(value)
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Deposit: {value}")

    def C001_withdrawMTD(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Withdraw value must be positive")
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached")
        if value > self.C001_balance + self.C001_limit:
            raise ValueError("Insufficient funds, exceeds overdraft limit")
        self.C001_balance -= int(value)
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw: {value}")

    def C001_transaction_reportMTD(self, filter_type: str = "all") -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, agency: str, number: int, client: Optional[D001_ClientCLS] = None,
                 balance: int = 0, limit: int = 0, daily_trans_limit: int = 10,
                 limit_withdrawals: int = 3):
        super().__init__(agency, number, client, balance, limit, daily_trans_limit)
        self.C002_limit_withdrawals = limit_withdrawals
        self.C002_number_withdrawals = 0

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        super().C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date == date.today():
            return
        self.C002_number_withdrawals = 0

    def C001_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise ValueError("Daily withdrawal limit reached")
        super().C001_withdrawMTD(value)
        self.C002_number_withdrawals += 1
        # rollback daily_trans_count increment in case of successful super call? super increment already.
        # just ensure we don't double count, but super increments daily_trans_count. That's fine.


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    @property
    def C003_balanceMTD(self) -> int:
        return self.C001_balance

    @property
    def C003_limitMTD(self) -> int:
        return self.C001_limit


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]):
        self._accounts = accounts
        self._index = 0

    def __iter__(self) -> E001_IteratorAccountCLS:
        self._index = 0
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index >= len(self._accounts):
            raise StopIteration
        account = self._accounts[self._index]
        self._index += 1
        return account