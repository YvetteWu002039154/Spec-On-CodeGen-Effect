from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Generator, Union

class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value = value

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
        account.C001_history.B001_add_transactionMTD(
            f"Deposit of {self.A001_value}"
        )

class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001__reset_transaction_count_if_new_dayMTD()
        if account.C001_daily_trans_count >= account.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit exceeded")
        if account.C001_balance < int(self.A001_value):
            raise ValueError("Insufficient balance")
        account.C001_balance -= int(self.A001_value)
        account.C001_daily_trans_count += 1
        account.C001_history.B001_add_transactionMTD(
            f"Withdraw of {self.A001_value}"
        )

class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: str) -> Generator[str, None, None]:
        for desc in self.B001_transactions:
            if filter_type.lower() in desc.lower():
                yield desc

class C001_AccountCLS:
    def __init__(
        self,
        agency: str,
        number: str,
        client: 'D001_ClientCLS',
        limit: int = 0,
        daily_trans_limit: int = 10
    ) -> None:
        self.C001_agency = agency
        self.C001_number = number
        self.C001_balance: int = 0
        self.C001_client = client
        self.C001_limit = limit
        self.C001_daily_trans_limit = daily_trans_limit
        self.C001_daily_trans_count: int = 0
        self.C001_last_trans_date: Optional[date] = None
        self.C001_history = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        transaction = A002_DepositCLS(value)
        transaction.A001_registerMTD(self)

    def C001_withdrawMTD(self, value: float) -> None:
        transaction = A003_WithdrawCLS(value)
        transaction.A001_registerMTD(self)

    def C001_transaction_reportMTD(self, filter_type: str) -> Generator[str, None, None]:
        return self.C001_history.B001_transaction_generatorMTD(filter_type)

class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        agency: str,
        number: str,
        client: 'D001_ClientCLS',
        limit: int = 0,
        daily_trans_limit: int = 10,
        limit_withdrawals: int = 3
    ) -> None:
        super().__init__(agency, number, client, limit, daily_trans_limit)
        self.C002_limit_withdrawals = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        super().C001__reset_transaction_count_if_new_dayMTD()
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise ValueError("Daily withdrawal limit reached")
        super().C001_withdrawMTD(value)
        self.C002_number_withdrawals += 1

class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    @property
    def C003_balanceMTD(self) -> str:
        return f"R$ {self.C001_balance}"

    @property
    def C003_limitMTD(self) -> str:
        return f"R$ {self.C001_limit}"

class D001_ClientCLS:
    def __init__(
        self,
        name: str,
        cpf: str,
        birth: date,
        address: str
    ) -> None:
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_birth = birth
        self.D001_address = address
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        if account not in self.D001_accounts:
            self.D001_accounts.append(account)
            account.C001_client = self

class E001_IteratorAccountCLS:
    def __init__(self, client: D001_ClientCLS) -> None:
        self._client = client
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._client.D001_accounts):
            raise StopIteration
        account = self._client.D001_accounts[self._index]
        self._index += 1
        return account