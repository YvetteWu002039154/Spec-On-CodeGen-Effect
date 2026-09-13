from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Generator, List, Optional, Union


class A001_TransactionCLS(ABC):
    def __init__(self, value: float) -> None:
        self.A001_value: float = float(value)

    @abstractmethod
    def A001_registerMTD(self, account: "C001_AccountCLS") -> bool:
        raise NotImplementedError


class A002_DepositCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: "C001_AccountCLS") -> bool:
        return account.C001_depositMTD(self.A001_value)


class A003_WithdrawCLS(A001_TransactionCLS):
    def A001_registerMTD(self, account: "C001_AccountCLS") -> bool:
        return account.C001_withdrawMTD(self.A001_value)


@dataclass(frozen=True)
class _HistoryTransactionRecord:
    description: str


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[_HistoryTransactionRecord] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(_HistoryTransactionRecord(description=description))

    def B001_transaction_generatorMTD(
        self, filter_type: Optional[Union[str, type]]
    ) -> Generator[_HistoryTransactionRecord, None, None]:
        if filter_type is None:
            for t in self.B001_transactions:
                yield t
            return

        if isinstance(filter_type, type):
            needle = filter_type.__name__
        else:
            needle = str(filter_type)

        needle_lower = needle.lower()
        for t in self.B001_transactions:
            if needle_lower in t.description.lower():
                yield t


class C001_AccountCLS:
    def __init__(
        self,
        agency: str,
        number: Any,
        client: Any,
        balance: int = 0,
        limit: int = 0,
        daily_trans_limit: int = 0,
    ) -> None:
        self.C001_agency: str = str(agency)
        self.C001_number: Any = number
        self.C001_client: Any = client

        self.C001_balance: int = int(balance)
        self.C001_limit: int = int(limit)

        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = int(daily_trans_limit)
        self.C001_last_trans_date: date = date.today()

        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def _C001__can_transact(self) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_limit <= 0:
            return True
        return self.C001_daily_trans_count < self.C001_daily_trans_limit

    def _C001__count_transaction(self) -> None:
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()

    def C001_depositMTD(self, value: Any) -> bool:
        if not self._C001__can_transact():
            return False

        try:
            v = float(value)
        except (TypeError, ValueError):
            return False

        if v <= 0:
            return False

        self.C001_balance += int(v)
        self._C001__count_transaction()
        self.C001_history.B001_add_transactionMTD(f"deposit:{v}")
        return True

    def C001_withdrawMTD(self, value: Any) -> bool:
        if not self._C001__can_transact():
            return False

        try:
            v = float(value)
        except (TypeError, ValueError):
            return False

        if v <= 0:
            return False

        amount = int(v)
        if amount > self.C001_balance:
            return False

        self.C001_balance -= amount
        self._C001__count_transaction()
        self.C001_history.B001_add_transactionMTD(f"withdraw:{v}")
        return True

    def C001_transaction_reportMTD(
        self, filter_type: Optional[Union[str, type]]
    ) -> List[str]:
        return [t.description for t in self.C001_history.B001_transaction_generatorMTD(filter_type)]


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        agency: str,
        number: Any,
        client: Any,
        balance: int = 0,
        limit: int = 0,
        daily_trans_limit: int = 0,
        limit_withdrawals: int = 0,
    ) -> None:
        super().__init__(
            agency=agency,
            number=number,
            client=client,
            balance=balance,
            limit=limit,
            daily_trans_limit=daily_trans_limit,
        )
        self.C002_limit_withdrawals: int = int(limit_withdrawals)
        self.C002_number_withdrawals: int = 0

    def _C002__reset_withdrawals_if_new_day(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date == date.today() and self.C001_daily_trans_count == 0:
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: Any) -> bool:
        self._C002__reset_withdrawals_if_new_day()

        if self.C002_limit_withdrawals > 0 and self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            return False

        try:
            v = float(value)
        except (TypeError, ValueError):
            return False

        if v <= 0:
            return False

        amount = int(v)
        available = self.C001_balance + max(0, int(self.C001_limit))
        if amount > available:
            return False

        self.C001_balance -= amount
        self._C001__count_transaction()
        self.C002_number_withdrawals += 1
        self.C001_history.B001_add_transactionMTD(f"withdraw:{v}")
        return True


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
    @property
    def C003_balanceMTD(self) -> int:
        return self.C001_balance

    @property
    def C003_limitMTD(self) -> int:
        return self.C001_limit


class D001_ClientCLS:
    def __init__(
        self,
        name: Any,
        cpf: Any,
        birth: Any,
        address: Any,
    ) -> None:
        self.D001_name: Any = name
        self.D001_cpf: Any = cpf
        self.D001_birth: Any = birth
        self.D001_address: Any = address
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        if account not in self.D001_accounts:
            self.D001_accounts.append(account)


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts: List[C001_AccountCLS] = list(accounts)
        self._index: int = 0

    def __iter__(self) -> "E001_IteratorAccountCLS":
        self._index = 0
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index >= len(self._accounts):
            raise StopIteration
        acc = self._accounts[self._index]
        self._index += 1
        return acc