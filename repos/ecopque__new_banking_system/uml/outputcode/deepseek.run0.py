from abc import ABC, abstractmethod
from datetime import date
from typing import Generator, Iterator, List, Optional, Union


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, address: str, birth: date) -> None:
        self.D001_name = name
        self.D001_cpf = cpf
        self.D001_address = address
        self.D001_birth = birth
        self.D001_accounts: List['C001_AccountCLS'] = []

    def D001_add_accountMTD(self, account: 'C001_AccountCLS') -> None:
        if account not in self.D001_accounts:
            self.D001_accounts.append(account)
            account.C001_client = self


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> Generator[str, None, None]:
        for desc in self.B001_transactions:
            if filter_type is None or filter_type.lower() == 'all':
                yield desc
            elif filter_type.lower() == 'deposit' and 'deposit' in desc.lower():
                yield desc
            elif filter_type.lower() == 'withdraw' and 'withdraw' in desc.lower():
                yield desc


class C001_AccountCLS:
    def __init__(self, agency: str, number: str, client: D001_ClientCLS,
                 balance: int = 0, limit: int = 1000, daily_trans_limit: int = 10) -> None:
        self.C001_agency = agency
        self.C001_number = number
        self.C001_client = client
        self.C001_balance = balance
        self.C001_limit = limit
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
            raise Exception("Daily transaction limit exceeded")
        int_value = int(value)
        if int_value <= 0:
            raise ValueError("Deposit value must be positive")
        self.C001_balance += int_value
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Deposit of {int_value}")

    def C001_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise Exception("Daily transaction limit exceeded")
        int_value = int(value)
        if int_value <= 0:
            raise ValueError("Withdraw value must be positive")
        if self.C001_balance + self.C001_limit < int_value:
            raise Exception("Insufficient funds (including limit)")
        self.C001_balance -= int_value
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw of {int_value}")

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> Generator[str, None, None]:
        yield from self.C001_history.B001_transaction_generatorMTD(filter_type)


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, agency: str, number: str, client: D001_ClientCLS,
                 balance: int = 0, limit: int = 1000, daily_trans_limit: int = 10,
                 limit_withdrawals: int = 3) -> None:
        super().__init__(agency, number, client, balance, limit, daily_trans_limit)
        self.C002_limit_withdrawals = limit_withdrawals
        self.C002_number_withdrawals = 0

    def _reset_withdrawal_count_if_new_day(self) -> None:
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        self._reset_withdrawal_count_if_new_day()
        int_value = int(value)
        if int_value <= 0:
            raise ValueError("Withdraw value must be positive")
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise Exception("Withdrawal limit for current account reached")
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise Exception("Daily transaction limit exceeded")
        if self.C001_balance + self.C001_limit < int_value:
            raise Exception("Insufficient funds (including limit)")
        self.C001_balance -= int_value
        self.C001_daily_trans_count += 1
        self.C002_number_withdrawals += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw of {int_value}")


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> str:
        return f"Balance: R$ {self.C001_balance:,.2f}"

    def C003_limitMTD(self) -> str:
        return f"Limit: R$ {self.C001_limit:,.2f}"


class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
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


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts = accounts
        self._index = 0

    def __iter__(self) -> Iterator[C001_AccountCLS]:
        self._index = 0
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index < len(self._accounts):
            account = self._accounts[self._index]
            self._index += 1
            return account
        raise StopIteration