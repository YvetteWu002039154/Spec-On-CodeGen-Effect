from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Union, Iterator, Any


class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001__reset_transaction_count_if_new_dayMTD()
        account.C001_balance += self.A001_value
        account.C001_daily_trans_count += 1
        description = f"Deposit: {self.A001_value}"
        account.C001_history.B001_add_transactionMTD(description)


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001__reset_transaction_count_if_new_dayMTD()
        if self.A001_value <= 0:
            raise ValueError("Withdrawal value must be positive")
        if account.C001_balance < self.A001_value:
            raise ValueError("Insufficient balance")
        if hasattr(account, 'C001_limit') and self.A001_value > account.C001_limit:
            raise ValueError("Exceeds per-transaction withdrawal limit")
        if account.C001_daily_trans_count >= account.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached")
        account.C001_balance -= self.A001_value
        account.C001_daily_trans_count += 1
        description = f"Withdraw: {self.A001_value}"
        account.C001_history.B001_add_transactionMTD(description)


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> Iterator[str]:
        for trans in self.B001_transactions:
            if filter_type is None or filter_type in trans:
                yield trans


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, address: str, birth: date) -> None:
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_address = address
        self.D001_birth = birth
        self.D001_accounts: List['C001_AccountCLS'] = []

    def D001_add_accountMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_client = self
        self.D001_accounts.append(account)


class C001_AccountCLS:
    def __init__(
        self,
        number: str,
        agency: str,
        client: Optional[D001_ClientCLS] = None,
        daily_trans_limit: int = 10,
        limit: int = 1000
    ) -> None:
        self.C001_number = number
        self.C001_agency = agency
        self.C001_client = client
        self.C001_balance: float = 0.0
        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = daily_trans_limit
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()
        self.C001_last_trans_date: date = date.today()
        self.C001_limit: int = limit

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date < today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Deposit value must be positive")
        transaction = A002_DepositCLS(value)
        transaction.A001_registerMTD(self)

    def C001_withdrawMTD(self, value: float) -> None:
        transaction = A003_WithdrawCLS(value)
        transaction.A001_registerMTD(self)

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        number: str,
        agency: str,
        client: Optional[D001_ClientCLS] = None,
        daily_trans_limit: int = 10,
        limit: int = 1000,
        limit_withdrawals: int = 3
    ) -> None:
        super().__init__(number, agency, client, daily_trans_limit, limit)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def C002_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise ValueError("Exceeds maximum number of withdrawals allowed today")
        transaction = A003_WithdrawCLS(value)
        transaction.A001_registerMTD(self)
        self.C002_number_withdrawals += 1

    # Override daily count reset to also reset withdrawal count
    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date < today:
            self.C001_daily_trans_count = 0
            self.C002_number_withdrawals = 0
            self.C001_last_trans_date = today


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> str:
        return f"Decorated Balance: ${self.C001_balance:.2f}"

    def C003_limitMTD(self) -> str:
        return f"Withdrawal limit today: {self.C002_limit_withdrawals}"


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts = accounts
        self._index = 0

    def __iter__(self) -> 'E001_IteratorAccountCLS':
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index >= len(self._accounts):
            raise StopIteration
        account = self._accounts[self._index]
        self._index += 1
        return account