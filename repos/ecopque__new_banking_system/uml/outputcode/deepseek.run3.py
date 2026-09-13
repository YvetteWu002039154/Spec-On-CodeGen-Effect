from abc import ABC, abstractmethod
from datetime import date
from typing import List, Iterator, Optional

class A001_TransactionCLS(ABC):
    def __init__(self, value: float):
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        ...


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance += int(self.A001_value)
        account.C001_history.B001_add_transactionMTD(f"Deposit of {self.A001_value}")


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        if self.A001_value > account.C001_balance + account.C001_limit:
            raise ValueError("Insufficient funds or limit")
        account.C001_balance -= int(self.A001_value)
        account.C001_history.B001_add_transactionMTD(f"Withdrawal of {self.A001_value}")


class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> Iterator[str]:
        for transaction in self.B001_transactions:
            if filter_type is None or filter_type.lower() in transaction.lower():
                yield transaction


class C001_AccountCLS:
    def __init__(self, agency: str, number: str, balance: int = 0, limit: int = 0,
                 daily_trans_limit: int = 10, client: Optional['D001_ClientCLS'] = None):
        self.C001_agency = agency
        self.C001_number = number
        self.C001_balance = balance
        self.C001_limit = limit
        self.C001_client = client
        self.C001_daily_trans_limit = daily_trans_limit
        self.C001_daily_trans_count = 0
        self.C001_last_trans_date: date = date.today()
        self.C001_history = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached")
        deposit = A002_DepositCLS(value)
        deposit.A001_registerMTD(self)
        self.C001_daily_trans_count += 1

    def C001_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached")
        withdraw = A003_WithdrawCLS(value)
        withdraw.A001_registerMTD(self)
        self.C001_daily_trans_count += 1

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, agency: str, number: str, balance: int = 0, limit: int = 0,
                 daily_trans_limit: int = 10, client: Optional['D001_ClientCLS'] = None,
                 limit_withdrawals: int = 3):
        super().__init__(agency, number, balance, limit, daily_trans_limit, client)
        self.C002_limit_withdrawals = limit_withdrawals
        self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> None:
        self.C002_number_withdrawals += 1
        if self.C002_number_withdrawals > self.C002_limit_withdrawals:
            raise ValueError("Withdrawal limit exceeded")
        super().C001_withdrawMTD(value)


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> str:
        return f"Balance: R$ {self.C001_balance}"

    def C003_limitMTD(self) -> str:
        return f"Limit: R$ {self.C001_limit}"


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, address: str, birth: date):
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_address = address
        self.D001_birth = birth
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        account.C001_client = self
        self.D001_accounts.append(account)

    def __iter__(self) -> 'E001_IteratorAccountCLS':
        return E001_IteratorAccountCLS(self.D001_accounts)


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]):
        self._accounts = accounts
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index >= len(self._accounts):
            raise StopIteration
        account = self._accounts[self._index]
        self._index += 1
        return account