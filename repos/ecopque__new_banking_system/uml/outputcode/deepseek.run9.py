from abc import ABC, abstractmethod
from datetime import date
from typing import List, Generator, Optional, Union


class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value: float = value

    @abstractmethod
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance += int(self.A001_value)
        account.C001_history.B001_add_transactionMTD(f"Deposit of {self.A001_value}")
        account.C001_daily_trans_count += 1
        account.C001_last_trans_date = date.today()


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: 'C001_AccountCLS') -> None:
        account.C001_balance -= int(self.A001_value)
        account.C001_history.B001_add_transactionMTD(f"Withdraw of {self.A001_value}")
        account.C001_daily_trans_count += 1
        account.C001_last_trans_date = date.today()


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: str) -> Generator[str, None, None]:
        for desc in self.B001_transactions:
            if filter_type == "all" or desc.startswith(filter_type):
                yield desc


class C001_AccountCLS:
    def __init__(self, agency: str, number: str, client: 'D001_ClientCLS',
                 limit: int = 0, daily_trans_limit: int = 10) -> None:
        self.C001_agency: str = agency
        self.C001_number: str = number
        self.C001_client: 'D001_ClientCLS' = client
        self.C001_balance: int = 0
        self.C001_limit: int = limit
        self.C001_daily_trans_limit: int = daily_trans_limit
        self.C001_daily_trans_count: int = 0
        self.C001_last_trans_date: Optional[date] = None
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def __reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def depositMTD(self, value: float) -> None:
        self.__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise Exception("Daily transaction limit reached")
        if value <= 0:
            raise ValueError("Deposit value must be positive")
        transaction = A002_DepositCLS(value)
        transaction.A001_registerMTD(self)

    def withdrawMTD(self, value: float) -> None:
        self.__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            raise Exception("Daily transaction limit reached")
        if value <= 0:
            raise ValueError("Withdraw value must be positive")
        if self.C001_balance - value < -self.C001_limit:
            raise Exception("Insufficient funds or credit limit exceeded")
        transaction = A003_WithdrawCLS(value)
        transaction.A001_registerMTD(self)

    def transaction_reportMTD(self, filter_type: str) -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, agency: str, number: str, client: 'D001_ClientCLS',
                 limit: int = 0, daily_trans_limit: int = 10,
                 limit_withdrawals: int = 5) -> None:
        super().__init__(agency, number, client, limit, daily_trans_limit)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def _C002__reset_withdrawals_if_new_day(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C002_number_withdrawals = 0
            # parent's private reset is called separately; we don't need to call it here
            # because withdrawMTD will call parent's __reset which will handle daily_trans_count

    def withdrawMTD(self, value: float) -> None:
        self._C002__reset_withdrawals_if_new_day()
        # Also ensure parent's daily reset is done (parent's withdrawMTD will do it again, but safe)
        self._C001_AccountCLS__reset_transaction_count_if_new_dayMTD()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            raise Exception("Daily withdrawal limit reached")
        # Call parent's withdrawMTD which handles the rest
        super().withdrawMTD(value)
        self.C002_number_withdrawals += 1


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    @property
    def C003_balanceMTD(self) -> int:
        print("Accessing balance via decorator")
        return self.C001_balance

    @C003_balanceMTD.setter
    def C003_balanceMTD(self, value: int) -> None:
        print("Setting balance via decorator")
        self.C001_balance = value

    @property
    def C003_limitMTD(self) -> int:
        print("Accessing limit via decorator")
        return self.C001_limit

    @C003_limitMTD.setter
    def C003_limitMTD(self, value: int) -> None:
        print("Setting limit via decorator")
        self.C001_limit = value


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, address: str, birth: date) -> None:
        self.D001_name: str = name
        self.D001_cpf: str = cpf
        self.D001_address: str = address
        self.D001_birth: date = birth
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        account.C001_client = self
        self.D001_accounts.append(account)


class E001_IteratorAccountCLS:
    pass