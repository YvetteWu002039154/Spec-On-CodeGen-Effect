from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Iterator, Union, Generator


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> Generator[str, None, None]:
        for transaction in self.B001_transactions:
            if filter_type is None or filter_type in transaction:
                yield transaction


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, birth: date, address: str) -> None:
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_birth = birth
        self.D001_address = address
        self.D001_accounts: List['C001_AccountCLS'] = []

    def D001_add_accountMTD(self, account: 'C001_AccountCLS') -> None:
        self.D001_accounts.append(account)


class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance += int(self.A001_value)
        account.C001_history.B001_add_transactionMTD(f"Deposit of {self.A001_value}")


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance -= int(self.A001_value)
        account.C001_history.B001_add_transactionMTD(f"Withdraw of {self.A001_value}")


class C001_AccountCLS:
    def __init__(
        self,
        agency: str,
        number: str,
        client: D001_ClientCLS,
        limit: int = 0,
        daily_trans_limit: int = 10
    ) -> None:
        self.C001_agency = agency
        self.C001_number = number
        self.C001_client = client
        self.C001_balance = 0
        self.C001_limit = limit
        self.C001_daily_trans_limit = daily_trans_limit
        self.C001_daily_trans_count = 0
        self.C001_last_trans_date: Optional[date] = None
        self.C001_history = B001_HistoryCLS()

    def _C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        self._C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached.")
        deposit = A002_DepositCLS(value)
        deposit.A001_registerMTD(self)
        self.C001_daily_trans_count += 1

    def C001_withdrawMTD(self, value: float) -> None:
        self._C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit reached.")
        if value > self.C001_balance + self.C001_limit:
            raise ValueError("Insufficient funds.")
        withdraw = A003_WithdrawCLS(value)
        withdraw.A001_registerMTD(self)
        self.C001_daily_trans_count += 1

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        agency: str,
        number: str,
        client: D001_ClientCLS,
        limit: int = 0,
        daily_trans_limit: int = 10,
        limit_withdrawals: int = 0
    ) -> None:
        super().__init__(agency, number, client, limit, daily_trans_limit)
        self.C002_limit_withdrawals = limit_withdrawals
        self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> None:
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise ValueError("Withdrawal limit reached.")
        super().C001_withdrawMTD(value)
        self.C002_number_withdrawals += 1


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> str:
        return f"Decorated Balance: {self.C001_balance}"

    def C003_limitMTD(self) -> str:
        return f"Decorated Limit: {self.C001_limit}"


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts = accounts
        self._index = 0

    def __iter__(self) -> 'E001_IteratorAccountCLS':
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index < len(self._accounts):
            account = self._accounts[self._index]
            self._index += 1
            return account
        raise StopIteration