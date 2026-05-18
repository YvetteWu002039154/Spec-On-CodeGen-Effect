from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Generator, List, Optional


class A001_TransactionCLS(ABC):
    def __init__(self, A001_value: float) -> None:
        self.A001_value: float = float(A001_value)

    @abstractmethod
    def A001_registerMTD(self, account: "C001_AccountCLS") -> bool:
        raise NotImplementedError


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: "C001_AccountCLS") -> bool:
        return account.C001_depositMTD(self.A001_value)


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: "C001_AccountCLS") -> bool:
        return account.C001_withdrawMTD(self.A001_value)


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[str] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        self.B001_transactions.append(str(description))

    def B001_transaction_generatorMTD(self, filter_type: Optional[Any]) -> Generator[str, None, None]:
        if filter_type is None:
            for transaction in self.B001_transactions:
                yield transaction
            return

        filter_text = str(filter_type).lower()
        for transaction in self.B001_transactions:
            if filter_text in transaction.lower():
                yield transaction


class C001_AccountCLS:
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: Any,
        C001_balance: int = 0,
        C001_limit: int = 500,
        C001_daily_trans_limit: int = 10,
    ) -> None:
        self.C001_agency: str = str(C001_agency)
        self.C001_balance: int = int(C001_balance)
        self.C001_client: Any = C001_client
        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = int(C001_daily_trans_limit)
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()
        self.C001_last_trans_date: date = date.today()
        self.C001_limit: int = int(C001_limit)
        self.C001_number: Any = C001_number

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def C001_depositMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            return False
        if value <= 0:
            return False

        self.C001_balance += int(value)
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()
        self.C001_history.B001_add_transactionMTD(f"deposit:{float(value):.2f}")
        return True

    def C001_transaction_reportMTD(self, filter_type: Optional[Any]) -> Generator[str, None, None]:
        return self.C001_history.B001_transaction_generatorMTD(filter_type)

    def C001_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_count >= self.C001_daily_trans_limit:
            return False
        if value <= 0:
            return False
        if value > self.C001_limit:
            return False
        if value > self.C001_balance:
            return False

        self.C001_balance -= int(value)
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()
        self.C001_history.B001_add_transactionMTD(f"withdraw:{float(value):.2f}")
        return True


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: Any,
        C001_balance: int = 0,
        C001_limit: int = 500,
        C001_daily_trans_limit: int = 10,
        C002_limit_withdrawals: int = 3,
    ) -> None:
        super().__init__(
            C001_agency=C001_agency,
            C001_number=C001_number,
            C001_client=C001_client,
            C001_balance=C001_balance,
            C001_limit=C001_limit,
            C001_daily_trans_limit=C001_daily_trans_limit,
        )
        self.C002_limit_withdrawals: int = int(C002_limit_withdrawals)
        self.C002_number_withdrawals: int = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0
        if self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            return False

        success = super().C001_withdrawMTD(value)
        if success:
            self.C002_number_withdrawals += 1
        return success

    def C001_withdrawMTD(self, value: float) -> bool:
        return self.C002_withdrawMTD(value)


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: Any,
        C001_balance: int = 0,
        C001_limit: int = 500,
        C001_daily_trans_limit: int = 10,
        C002_limit_withdrawals: int = 3,
    ) -> None:
        super().__init__(
            C001_agency=C001_agency,
            C001_number=C001_number,
            C001_client=C001_client,
            C001_balance=C001_balance,
            C001_limit=C001_limit,
            C001_daily_trans_limit=C001_daily_trans_limit,
            C002_limit_withdrawals=C002_limit_withdrawals,
        )

    def C003_balanceMTD(self) -> int:
        return self.C001_balance

    def C003_limitMTD(self) -> int:
        return self.C001_limit


class D001_ClientCLS:
    def __init__(
        self,
        D001_name: Any,
        D001_cpf: Any,
        D001_birth: Any,
        D001_address: Any,
    ) -> None:
        self.D001_accounts: List[C001_AccountCLS] = []
        self.D001_address: Any = D001_address
        self.D001_birth: Any = D001_birth
        self.D001_cpf: Any = D001_cpf
        self.D001_name: Any = D001_name

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        self.D001_accounts.append(account)
        account.C001_client = self


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts: List[C001_AccountCLS] = accounts
        self._index: int = 0

    def __iter__(self) -> "E001_IteratorAccountCLS":
        self._index = 0
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index >= len(self._accounts):
            raise StopIteration
        account = self._accounts[self._index]
        self._index += 1
        return account