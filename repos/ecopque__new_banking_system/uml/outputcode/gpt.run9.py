from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Generator, List, Optional, Union


class A001_TransactionCLS(ABC):
    def __init__(self, A001_value: float):
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
class _HistoryTransactionRecord:
    description: str
    type: str
    value: float
    date: date


class B001_HistoryCLS:
    def __init__(self):
        self.B001_transactions: List[_HistoryTransactionRecord] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(
            _HistoryTransactionRecord(
                description=description.strip(),
                type="description",
                value=0.0,
                date=date.today(),
            )
        )

    def _add_record(self, record: _HistoryTransactionRecord) -> None:
        self.B001_transactions.append(record)

    def B001_transaction_generatorMTD(
        self, filter_type: Optional[Union[str, type]]
    ) -> Generator[_HistoryTransactionRecord, None, None]:
        if filter_type is None:
            for t in self.B001_transactions:
                yield t
            return

        if isinstance(filter_type, type):
            name = filter_type.__name__
            for t in self.B001_transactions:
                if t.type == name:
                    yield t
            return

        if isinstance(filter_type, str):
            ft = filter_type.strip()
            for t in self.B001_transactions:
                if t.type == ft:
                    yield t
            return

        raise TypeError("filter_type must be None, str, or type")


class C001_AccountCLS:
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: Any = None,
        C001_balance: int = 0,
        C001_limit: int = 0,
        C001_daily_trans_limit: int = 0,
    ):
        self.C001_agency: str = str(C001_agency)
        self.C001_number = C001_number
        self.C001_client = C001_client

        self.C001_balance: int = int(C001_balance)
        self.C001_limit: int = int(C001_limit)

        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = int(C001_daily_trans_limit)
        self.C001_last_trans_date: date = date.today()

        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        today = date.today()
        if self.C001_last_trans_date != today:
            self.C001_daily_trans_count = 0
            self.C001_last_trans_date = today

    def _can_transact_today(self) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_daily_trans_limit <= 0:
            return True
        return self.C001_daily_trans_count < self.C001_daily_trans_limit

    def _increment_daily_count(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()

    def C001_depositMTD(self, value: float) -> bool:
        if value is None:
            raise ValueError("value cannot be None")
        v = float(value)
        if v <= 0:
            return False
        if not self._can_transact_today():
            return False

        self.C001_balance += int(v)
        self._increment_daily_count()
        self.C001_history._add_record(
            _HistoryTransactionRecord(
                description="deposit",
                type=A002_DepositCLS.__name__,
                value=v,
                date=date.today(),
            )
        )
        return True

    def C001_withdrawMTD(self, value: float) -> bool:
        if value is None:
            raise ValueError("value cannot be None")
        v = float(value)
        if v <= 0:
            return False
        if not self._can_transact_today():
            return False

        available = self.C001_balance + self.C001_limit
        if v > available:
            return False

        self.C001_balance -= int(v)
        self._increment_daily_count()
        self.C001_history._add_record(
            _HistoryTransactionRecord(
                description="withdraw",
                type=A003_WithdrawCLS.__name__,
                value=v,
                date=date.today(),
            )
        )
        return True

    def C001_transaction_reportMTD(
        self, filter_type: Optional[Union[str, type]]
    ) -> List[_HistoryTransactionRecord]:
        return list(self.C001_history.B001_transaction_generatorMTD(filter_type))


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        C001_agency: str,
        C001_number: Any,
        C001_client: Any = None,
        C001_balance: int = 0,
        C001_limit: int = 0,
        C001_daily_trans_limit: int = 0,
        C002_limit_withdrawals: int = 0,
    ):
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

    def _reset_withdrawals_if_new_day(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0

        if self.C002_limit_withdrawals > 0 and self.C002_number_withdrawals >= self.C002_limit_withdrawals:
            return False

        ok = super().C001_withdrawMTD(value)
        if ok:
            self.C002_number_withdrawals += 1
        return ok


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
        D001_name: Any,
        D001_cpf: Any,
        D001_birth: Any,
        D001_address: Any,
    ):
        self.D001_name = D001_name
        self.D001_cpf = D001_cpf
        self.D001_birth = D001_birth
        self.D001_address = D001_address
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        if account is None:
            raise ValueError("account cannot be None")
        if account in self.D001_accounts:
            return
        self.D001_accounts.append(account)
        account.C001_client = self


class E001_IteratorAccountCLS:
    def __init__(self, accounts: List[C001_AccountCLS]):
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