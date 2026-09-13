from abc import ABC, abstractmethod
from datetime import date
from typing import List, Iterator, Optional


class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value: float = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001__reset_transaction_count_if_new_dayMTD()
        if account.C001_daily_trans_count >= account.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit exceeded")
        account.C001_balance += int(self.A001_value)
        account.C001_daily_trans_count += 1
        account.C001_history.B001_add_transactionMTD(f"Deposit: {self.A001_value}")


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001__reset_transaction_count_if_new_dayMTD()
        if account.C001_daily_trans_count >= account.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit exceeded")
        available = account.C001_balance + account.C001_limit
        if self.A001_value > available:
            raise ValueError("Insufficient funds, including overdraft limit")
        account.C001_balance -= int(self.A001_value)
        account.C001_daily_trans_count += 1
        account.C001_history.B001_add_transactionMTD(f"Withdraw: {self.A001_value}")


class E001_IteratorAccountCLS:
    def __init__(self, transactions: List[str]) -> None:
        self._transactions: List[str] = transactions
        self._index: int = 0

    def __iter__(self) -> 'E001_IteratorAccountCLS':
        return self

    def __next__(self) -> str:
        if self._index >= len(self._transactions):
            raise StopIteration
        item = self._transactions[self._index]
        self._index += 1
        return item


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> E001_IteratorAccountCLS:
        if filter_type is None:
            return E001_IteratorAccountCLS(self.B001_transactions.copy())
        filtered = [t for t in self.B001_transactions if filter_type in t]
        return E001_IteratorAccountCLS(filtered)


class C001_AccountCLS:
    def __init__(
        self,
        agency: str,
        number: str,
        client: 'D001_ClientCLS',
        balance: int = 0,
        limit: int = 0,
        daily_trans_limit: int = 10,
    ) -> None:
        self.C001_agency: str = agency
        self.C001_number: str = number
        self.C001_client: 'D001_ClientCLS' = client
        self.C001_balance: int = balance
        self.C001_limit: int = limit
        self.C001_daily_trans_limit: int = daily_trans_limit
        self.C001_daily_trans_count: int = 0
        self.C001_last_trans_date: Optional[date] = None
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        deposit = A002_DepositCLS(value)
        deposit.A001_registerMTD(self)

    def C001_withdrawMTD(self, value: float) -> None:
        withdraw = A003_WithdrawCLS(value)
        withdraw.A001_registerMTD(self)

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> E001_IteratorAccountCLS:
        return self.C001_history.B001_transaction_generatorMTD(filter_type)


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        agency: str,
        number: str,
        client: 'D001_ClientCLS',
        balance: int = 0,
        limit: int = 0,
        daily_trans_limit: int = 10,
        limit_withdrawals: int = 3,
    ) -> None:
        super().__init__(agency, number, client, balance, limit, daily_trans_limit)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def C002_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        # reset withdrawal count if new day (relying on common reset)
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise ValueError("Daily withdrawal limit exceeded for current account")
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit exceeded")
        available = self.C001_balance + self.C001_limit
        if value > available:
            raise ValueError("Insufficient funds, including overdraft limit")
        self.C001_balance -= int(value)
        self.C001_daily_trans_count += 1
        self.C002_number_withdrawals += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw: {value}")


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> int:
        return self.C001_balance

    def C003_limitMTD(self) -> int:
        return self.C001_limit


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, birth: date, address: str) -> None:
        self.D001_name: str = name
        self.D001_cpf: str = cpf
        self.D001_birth: date = birth
        self.D001_address: str = address
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        self.D001_accounts.append(account)
        account.C001_client = self