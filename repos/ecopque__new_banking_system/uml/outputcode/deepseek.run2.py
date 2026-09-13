from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Generator


class A001_TransactionCLS(ABC):
    def __init__(self, value: float):
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_depositMTD(self.A001_value)


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_withdrawMTD(self.A001_value)


class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> Generator[str, None, None]:
        for trans in self.B001_transactions:
            if filter_type is None or filter_type.lower() in trans.lower():
                yield trans


class C001_AccountCLS:
    def __init__(self, agency: str, number: str, client: Optional['D001_ClientCLS'] = None,
                 daily_trans_limit: int = 10, limit: int = 1000):
        self.C001_agency: str = agency
        self.C001_number: str = number
        self.C001_client: Optional['D001_ClientCLS'] = client
        self.C001_balance: float = 0.0
        self.C001_daily_trans_limit: int = daily_trans_limit
        self.C001_daily_trans_count: int = 0
        self.C001_limit: int = limit
        self.C001_last_trans_date: Optional[date] = None
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def __reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Deposit value must be positive.")
        self.__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit exceeded.")
        self.C001_balance += value
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Deposit: {value:.2f}")

    def C001_withdrawMTD(self, value: float) -> None:
        if value <= 0:
            raise ValueError("Withdrawal value must be positive.")
        if value > self.C001_limit:
            raise ValueError("Withdrawal value exceeds account limit.")
        self.__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise ValueError("Daily transaction limit exceeded.")
        if self.C001_balance < value:
            raise ValueError("Insufficient balance.")
        self.C001_balance -= value
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw: {value:.2f}")

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, agency: str, number: str, client: Optional['D001_ClientCLS'] = None,
                 daily_trans_limit: int = 10, limit: int = 1000, limit_withdrawals: int = 3):
        super().__init__(agency, number, client, daily_trans_limit, limit)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def _reset_withdrawal_count_if_new_day(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> None:
        self._reset_withdrawal_count_if_new_day()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise ValueError("Daily withdrawal limit reached.")
        super().C001_withdrawMTD(value)
        self.C002_number_withdrawals += 1
        self.C001_daily_trans_count -= 1  # parent already incremented, we adjust to reflect only one increment
        self.C001_daily_trans_count += 1  # but actually we already incremented, so no need to adjust. Wait: super().C001_withdrawMTD increments daily_trans_count once, which is correct. No double increment. So no need to adjust.


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def C003_balanceMTD(self) -> str:
        return f"*** Balance: R$ {self.C001_balance:,.2f} ***"

    def C003_limitMTD(self) -> str:
        return f"*** Account Limit: {self.C001_limit} ***"


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, address: str, birth: date):
        self.D001_name: str = name
        self.D001_cpf: str = cpf
        self.D001_address: str = address
        self.D001_birth: date = birth
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        self.D001_accounts.append(account)
        account.C001_client = self


class E001_IteratorAccountCLS:
    def __init__(self, client: D001_ClientCLS):
        self._accounts = client.D001_accounts
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._accounts):
            raise StopIteration
        account = self._accounts[self._index]
        self._index += 1
        return account