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
        success = account.C001_depositMTD(self.A001_value)
        if success:
            account.C001_history.B001_add_transactionMTD(
                f"Deposit: +${self.A001_value:.2f}"
            )


class A003_WithdrawCLS(A001_TransactionCLS):
    def __init__(self, value: float):
        super().__init__(value)

    def A001_registerMTD(self, account):
        success = account.C001_withdrawMTD(self.A001_value)
        if success:
            account.C001_history.B001_add_transactionMTD(
                f"Withdrawal: -${self.A001_value:.2f}"
            )


class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: list = []

    def B001_add_transactionMTD(self, description: str):
        self.B001_transactions.append({
            "description": description,
            "date": date.today()
        })

    def B001_transaction_generatorMTD(self, filter_type=None) -> Generator:
        for transaction in self.B001_transactions:
            if filter_type is None:
                yield transaction
            elif filter_type.lower() in transaction["description"].lower():
                yield transaction


class C001_AccountCLS:
    _account_counter = 1

    def __init__(self, client, agency: str = "0001"):
        self.C001_agency: str = agency
        self.C001_balance: int = 0
        self.C001_client = client
        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = 10
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()
        self.C001_last_trans_date: date = date.today()
        self.C001_limit: int = 1000
        self.C001_number = C001_AccountCLS._account_counter
        C001_AccountCLS._account_counter += 1

    def C001__reset_transaction_count_if_new_dayMTD(self):
        today = date.today()
        if today != self.C001_last_trans_date:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if value <= 0:
            print("Deposit value must be positive.")
            return False
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            print("Daily transaction limit reached.")
            return False
        self.C001_balance += value
        self.C001_daily_trans_count += 1
        return True

    def C001_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if value <= 0:
            print("Withdrawal value must be positive.")
            return False
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            print("Daily transaction limit reached.")
            return False
        if value > self.C001_balance:
            print("Insufficient balance.")
            return False
        self.C001_balance -= value
        self.C001_daily_trans_count += 1
        return True

    def C001_transaction_reportMTD(self, filter_type=None):
        print(f"\n--- Transaction Report (Account #{self.C001_number}) ---")
        transactions = list(self.C001_history.B001_transaction_generatorMTD(filter_type))
        if not transactions:
            print("No transactions found.")
        for t in transactions:
            print(f"  [{t['date']}] {t['description']}")
        print(f"Current Balance: ${self.C001_balance:.2f}")
        print("-------------------------------------------")


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, client, agency: str = "0001", limit: int = 1000, limit_withdrawals: int = 3):
        super().__init__(client, agency)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0
        self.C001_limit = limit

    def C001_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if value <= 0:
            print("Withdrawal value must be positive.")
            return False
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            print("Daily transaction limit reached.")
            return False
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            print("Withdrawal limit for this account reached.")
            return False
        if value > (self.C001_balance + self.C001_limit):
            print("Insufficient balance (including limit).")
            return False
        self.C001_balance -= value
        self.C001_daily_trans_count += 1
        self.C002_number_withdrawals += 1
        return True

    def C002_withdrawMTD(self, value: float) -> bool:
        return self.C001_withdrawMTD(value)


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def __init__(self, client, agency: str = "0001", limit: int = 1000, limit_withdrawals: int = 3):
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