from abc import ABC, abstractmethod
from datetime import date
from typing import Generator, Any


class A001_TransactionCLS(ABC):
    def __init__(self, value: float):
        self.A001_value = value

    @abstractmethod
    def A001_registerMTD(self, account):
        pass


class A002_DepositCLS(A001_TransactionCLS):
    def __init__(self, value: float):
        super().__init__(value)

    def A001_registerMTD(self, account):
        account.C001_depositMTD(self.A001_value)


class A003_WithdrawCLS(A001_TransactionCLS):
    def __init__(self, value: float):
        super().__init__(value)

    def A001_registerMTD(self, account):
        account.C001_withdrawMTD(self.A001_value)


class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: list = []

    def B001_add_transactionMTD(self, description: str):
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type) -> Generator:
        for transaction in self.B001_transactions:
            if filter_type is None or filter_type in transaction:
                yield transaction


class C001_AccountCLS:
    _account_counter = 1

    def __init__(self, client, agency: str = "0001", limit: int = 500):
        self.C001_agency: str = agency
        self.C001_balance: int = 0
        self.C001_client = client
        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = 10
        self.C001_history = B001_HistoryCLS()
        self.C001_last_trans_date: date = date.today()
        self.C001_limit: int = limit
        self.C001_number = C001_AccountCLS._account_counter
        C001_AccountCLS._account_counter += 1

    def C001__reset_transaction_count_if_new_dayMTD(self):
        today = date.today()
        if today != self.C001_last_trans_date:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            print("Daily transaction limit reached.")
            return False
        if value <= 0:
            print("Deposit value must be positive.")
            return False
        self.C001_balance += value
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Deposit: +{value:.2f}")
        return True

    def C001_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            print("Daily transaction limit reached.")
            return False
        if value <= 0:
            print("Withdrawal value must be positive.")
            return False
        if value > self.C001_balance:
            print("Insufficient balance.")
            return False
        self.C001_balance -= value
        self.C001_daily_trans_count += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw: -{value:.2f}")
        return True

    def C001_transaction_reportMTD(self, filter_type=None):
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, client, agency: str = "0001", limit: int = 500,
                 limit_withdrawals: int = 3):
        super().__init__(client, agency, limit)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            print("Daily transaction limit reached.")
            return False
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            print("Withdrawal limit reached.")
            return False
        if value <= 0:
            print("Withdrawal value must be positive.")
            return False
        if value > (self.C001_balance + self.C001_limit):
            print("Insufficient balance including limit.")
            return False
        self.C001_balance -= value
        self.C001_daily_trans_count += 1
        self.C002_number_withdrawals += 1
        self.C001_history.B001_add_transactionMTD(f"Withdraw: -{value:.2f}")
        return True


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def __init__(self, client, agency: str = "0001", limit: int = 500,
                 limit_withdrawals: int = 3):
        super().__init__(client, agency, limit, limit_withdrawals)

    @property
    def C003_balanceMTD(self) -> float:
        return self.C001_balance

    @property
    def C003_limitMTD(self) -> int:
        return self.C001_limit


class D001_ClientCLS:
    def __init__(self, name, cpf, birth, address):
        self.D001_accounts: list = []
        self.D001_address = address
        self.D001_birth = birth
        self.D001_cpf = cpf
        self.D001_name = name

    def D001_add_accountMTD(self, account):
        self.D001_accounts.append(account)


class E001_IteratorAccountCLS:
    def __init__(self, accounts: list):
        self._accounts = accounts
        self._index = 0

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        if self._index < len(self._accounts):
            account = self._accounts[self._index]
            self._index += 1
            return account
        raise StopIteration