from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Generator, List, Optional, Type, Union


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


@dataclass(frozen=True)
class _HistoryEntry:
    timestamp: datetime
    description: str


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[_HistoryEntry] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(_HistoryEntry(timestamp=datetime.now(), description=description.strip()))

    def B001_transaction_generatorMTD(
        self, filter_type: Optional[Union[str, Type[Any]]] = None
    ) -> Generator[_HistoryEntry, None, None]:
        if filter_type is None:
            for entry in self.B001_transactions:
                yield entry
            return

        if isinstance(filter_type, str):
            needle = filter_type.strip().lower()
            for entry in self.B001_transactions:
                if needle in entry.description.lower():
                    yield entry
            return

        if isinstance(filter_type, type):
            type_name = filter_type.__name__.lower()
            for entry in self.B001_transactions:
                if type_name in entry.description.lower():
                    yield entry
            return

        raise TypeError("filter_type must be None, a string, or a type")


class C001_AccountCLS:
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: "D001_ClientCLS",
        C001_balance: int = 0,
        C001_limit: int = 0,
        C001_daily_trans_limit: int = 0,
    ) -> None:
        if not isinstance(C001_agency, str) or not C001_agency.strip():
            raise ValueError("C001_agency must be a non-empty string")
        if C001_client is None:
            raise ValueError("C001_client must not be None")
        if not isinstance(C001_balance, int):
            raise TypeError("C001_balance must be int")
        if not isinstance(C001_limit, int):
            raise TypeError("C001_limit must be int")
        if not isinstance(C001_daily_trans_limit, int):
            raise TypeError("C001_daily_trans_limit must be int")
        if C001_daily_trans_limit < 0:
            raise ValueError("C001_daily_trans_limit must be >= 0")

        self.C001_agency: str = C001_agency.strip()
        self.C001_number: Any = C001_number
        self.C001_client: D001_ClientCLS = C001_client
        self.C001_balance: int = C001_balance
        self.C001_limit: int = C001_limit
        self.C001_daily_trans_limit: int = C001_daily_trans_limit
        self.C001_daily_trans_count: int = 0
        self.C001_last_trans_date: date = date.today()
        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def _C001__can_transact(self) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_limit == 0:
            return True
        return self.C001_daily_trans_count < self.C001_daily_trans_limit

    def _C001__increment_trans_count(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()

    def C001_depositMTD(self, value: Any) -> bool:
        if not self._C001__can_transact():
            return False

        try:
            amount = float(value)
        except (TypeError, ValueError):
            return False

        if amount <= 0:
            return False

        self.C001_balance += int(round(amount))
        self._C001__increment_trans_count()
        self.C001_history.B001_add_transactionMTD(f"Deposit: {amount:.2f}")
        return True

    def C001_withdrawMTD(self, value: Any) -> bool:
        if not self._C001__can_transact():
            return False

        try:
            amount = float(value)
        except (TypeError, ValueError):
            return False

        if amount <= 0:
            return False

        int_amount = int(round(amount))
        available = self.C001_balance + self.C001_limit
        if int_amount > available:
            return False

        self.C001_balance -= int_amount
        self._C001__increment_trans_count()
        self.C001_history.B001_add_transactionMTD(f"Withdraw: {amount:.2f}")
        return True

    def C001_transaction_reportMTD(
        self, filter_type: Optional[Union[str, Type[Any]]] = None
    ) -> List[str]:
        return [
            f"{entry.timestamp.isoformat(sep=' ', timespec='seconds')} - {entry.description}"
            for entry in self.C001_history.B001_transaction_generatorMTD(filter_type)
        ]


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: "D001_ClientCLS",
        C001_balance: int = 0,
        C001_limit: int = 0,
        C001_daily_trans_limit: int = 0,
        C002_limit_withdrawals: int = 0,
    ) -> None:
        super().__init__(
            C001_agency=C001_agency,
            C001_number=C001_number,
            C001_client=C001_client,
            C001_balance=C001_balance,
            C001_limit=C001_limit,
            C001_daily_trans_limit=C001_daily_trans_limit,
        )
        if not isinstance(C002_limit_withdrawals, int):
            raise TypeError("C002_limit_withdrawals must be int")
        if C002_limit_withdrawals < 0:
            raise ValueError("C002_limit_withdrawals must be >= 0")

        self.C002_limit_withdrawals: int = C002_limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def _C002__reset_withdrawals_if_new_day(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: Any) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C002_limit_withdrawals != 0 and self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            return False

        ok = super().C001_withdrawMTD(value)
        if ok:
            self.C002_number_withdrawals += 1
        return ok


class C003_DecoratedCAAccountCLS(C002_CurrentAccountCLS):
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
        self.D001_name = D001_name
        self.D001_cpf = D001_cpf
        self.D001_birth = D001_birth
        self.D001_address = D001_address
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        if account is None:
            raise ValueError("account must not be None")
        if account in self.D001_accounts:
            return
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