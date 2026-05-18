from abc import ABC, abstractmethod
from datetime import date
from typing import List, Any, Generator, Optional

class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(description)

    def B001_transaction_generatorMTD(self, filter_type: Optional[str] = None) -> Generator[str, None, None]:
        for transaction in self.B001_transactions:
            if filter_type is None or filter_type.lower() in transaction.lower():
                yield transaction

class C001_AccountCLS:
    def __init__(self, agency: str, number: Any, client: 'D001_ClientCLS', limit: int = 0, daily_trans_limit: int = 10) -> None:
        self.C001_agency: str = agency
        self.C001_number: Any = number
        self.C001_client: 'D001_ClientCLS' = client
        self.C001_balance: int = 0
        self.C001_limit: int = limit
        self.C001_daily_trans_limit: int = daily_trans_limit
        self.C001_daily_trans_count: int = 0
        self.C001_last_trans_date: date = date.today()
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_last_trans_date = today
            self.C001_daily_trans_count = 0

    def C001_depositMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            return False
        if value > 0:
            self.C001_balance += int(value)
            self.C001_daily_trans_count += 1
            return True
        return False

    def C001_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            return False
        if value > 0 and (self.C001_balance + self.C001_limit) >= value:
            self.C001_balance -= int(value)
            self.C001_daily_trans_count += 1
            return True
        return False

    def C001_transaction_reportMTD(self, filter_type: Optional[str] = None) -> List[str]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))

class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(self, agency: str, number: Any, client: 'D001_ClientCLS', limit: int = 0, daily_trans_limit: int = 10, limit_withdrawals: int = 3) -> None:
        super().__init__(agency, number, client, limit, daily_trans_limit)
        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            return False
        success = self.C001_withdrawMTD(value)
        if success:
            self.C002_number_withdrawals += 1
        return success

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

class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value: float = value

    @abstractmethod
    def A001_registerMTD(self, account: C001_AccountCLS) -> None:
        pass

class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: C001_AccountCLS) -> None:
        success = account.C001_depositMTD(self.A001_value)
        if success:
            account.C001_history.B001_add_transactionMTD(f"Deposit: {self.A001_value}")

class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: C001_AccountCLS) -> None:
        if hasattr(account, 'C002_withdrawMTD'):
            success = account.C002_withdrawMTD(self.A001_value)
        else:
            success = account.C001_withdrawMTD(self.A001_value)
            
        if success:
            account.C001_history.B001_add_transactionMTD(f"Withdraw: {self.A001_value}")

class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts: List[C001_AccountCLS] = accounts
        self._index: int = 0

    def __iter__(self) -> 'E001_IteratorAccountCLS':
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index < len(self._accounts):
            account = self._accounts[self._index]
            self._index += 1
            return account
        raise StopIteration