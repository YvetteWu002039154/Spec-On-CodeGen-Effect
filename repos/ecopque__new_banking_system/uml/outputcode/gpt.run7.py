from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Generator, Iterable, List, Optional, Type, Union


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
class _HistoryEntry:
    date: date
    description: str


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[_HistoryEntry] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(_HistoryEntry(date=date.today(), description=description.strip()))

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

        raise TypeError("filter_type must be None, str, or a type")


class D001_ClientCLS:
    def __init__(self, name: str, cpf: str, birth: Any, address: Any) -> None:
        self.D001_accounts: List[C001_AccountCLS] = []
        self.D001_address = address
        self.D001_birth = birth
        self.D001_cpf = cpf
        self.D001_name = name

    def D001_add_accountMTD(self, account: "C001_AccountCLS") -> None:
        if account is None:
            raise ValueError("account cannot be None")
        if account in self.D001_accounts:
            return
        self.D001_accounts.append(account)
        account.C001_client = self


class C001_AccountCLS:
    def __init__(
        self,
        agency: str,
        number: Any,
        client: Optional[D001_ClientCLS] = None,
        balance: int = 0,
        limit: int = 0,
        daily_trans_limit: int = 0,
    ) -> None:
        self.C001_agency: str = str(agency)
        self.C001_number = number
        self.C001_client: Optional[D001_ClientCLS] = None

        self.C001_balance: int = int(balance)
        self.C001_limit: int = int(limit)

        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = int(daily_trans_limit)
        self.C001_last_trans_date: date = date.today()

        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()

        if client is not None:
            client.D001_add_accountMTD(self)

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
        self.C001__reset_transaction_count_if_new_dayMTD()
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()

    def C001_depositMTD(self, value: float) -> bool:
        if value is None:
            raise ValueError("value cannot be None")
        value_f = float(value)
        if value_f <= 0:
            return False
        if not self._C001__can_transact():
            return False

        amount = int(value_f)
        if amount <= 0:
            return False

        self.C001_balance += amount
        self._C001__count_transaction()
        self.C001_history.B001_add_transactionMTD(f"Deposit: {amount}")
        return True

    def C001_withdrawMTD(self, value: float) -> bool:
        if value is None:
            raise ValueError("value cannot be None")
        value_f = float(value)
        if value_f <= 0:
            return False
        if not self._C001__can_transact():
            return False

        amount = int(value_f)
        if amount <= 0:
            return False

        available = self.C001_balance + self.C001_limit
        if amount > available:
            return False

        self.C001_balance -= amount
        self._C001__count_transaction()
        self.C001_history.B001_add_transactionMTD(f"Withdraw: {amount}")
        return True

    def C001_transaction_reportMTD(
        self, filter_type: Optional[Union[str, Type[Any]]] = None
    ) -> List[str]:
        return [entry.description for entry in self.C001_history.B001_transaction_generatorMTD(filter_type)]


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        agency: str,
        number: Any,
        client: Optional[D001_ClientCLS] = None,
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
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0

    def C001__reset_transaction_count_if_new_dayMTD(self) -> None:
        prev_date = self.C001_last_trans_date
        super().C001__reset_transaction_count_if_new_dayMTD()
        if prev_date != self.C001_last_trans_date:
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        return self.C001_withdrawMTD(value)

    def C001_withdrawMTD(self, value: float) -> bool:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C002_limit_withdrawals > 0 and self.C002_number_withdrawals >= self.C002_limit_withdrawals:
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


class E001_IteratorAccountCLS:
    def __init__(self, accounts: Iterable[C001_AccountCLS]) -> None:
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