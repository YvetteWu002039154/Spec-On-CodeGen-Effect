from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Generator, Iterator, List, Optional, Type, Union


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
    description: str
    entry_date: date


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[_HistoryEntry] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(_HistoryEntry(description=description.strip(), entry_date=date.today()))

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

        raise TypeError("filter_type must be None, str, or type")


class C001_AccountCLS:
    def __init__(
        self,
        agency: str,
        number: Any,
        client: "D001_ClientCLS",
        balance: int = 0,
        limit: int = 0,
        daily_trans_limit: int = 0,
    ) -> None:
        if not isinstance(agency, str) or not agency.strip():
            raise ValueError("agency must be a non-empty string")
        if client is None:
            raise ValueError("client is required")
        if not isinstance(balance, int):
            raise TypeError("balance must be int")
        if not isinstance(limit, int):
            raise TypeError("limit must be int")
        if not isinstance(daily_trans_limit, int):
            raise TypeError("daily_trans_limit must be int")
        if daily_trans_limit < 0:
            raise ValueError("daily_trans_limit must be >= 0")

        self.C001_agency: str = agency.strip()
        self.C001_number: Any = number
        self.C001_client: D001_ClientCLS = client

        self.C001_balance: int = balance
        self.C001_limit: int = limit

        self.C001_daily_trans_count: int = 0
        self.C001_daily_trans_limit: int = daily_trans_limit
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

    def _C001__register_transaction(self, description: str) -> None:
        self.C001_daily_trans_count += 1
        self.C001_last_trans_date = date.today()
        self.C001_history.B001_add_transactionMTD(description)

    def C001_depositMTD(self, value: float) -> bool:
        if not isinstance(value, (int, float)):
            raise TypeError("value must be numeric")
        value_f = float(value)
        if value_f <= 0:
            return False
        if not self._C001__can_transact():
            return False

        amount = int(value_f)
        if amount <= 0:
            return False

        self.C001_balance += amount
        self._C001__register_transaction(f"Deposit: {amount}")
        return True

    def C001_withdrawMTD(self, value: float) -> bool:
        if not isinstance(value, (int, float)):
            raise TypeError("value must be numeric")
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
        self._C001__register_transaction(f"Withdraw: {amount}")
        return True

    def C001_transaction_reportMTD(
        self, filter_type: Optional[Union[str, Type[Any]]] = None
    ) -> Generator[_HistoryEntry, None, None]:
        return self.C001_history.B001_transaction_generatorMTD(filter_type)


class C002_CurrentAccountCLS(C001_AccountCLS):
    def __init__(
        self,
        agency: str,
        number: Any,
        client: "D001_ClientCLS",
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
        if not isinstance(limit_withdrawals, int):
            raise TypeError("limit_withdrawals must be int")
        if limit_withdrawals < 0:
            raise ValueError("limit_withdrawals must be >= 0")

        self.C002_limit_withdrawals: int = limit_withdrawals
        self.C002_number_withdrawals: int = 0

    def _C002__reset_withdrawals_if_new_day(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date == date.today() and self.C001_daily_trans_count == 0:
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        self._C002__reset_withdrawals_if_new_day()

        if self.C002_limit_withdrawals != 0 and self.C002_number_withdrawals >= self.C002_limit_withdrawals:
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
    def __init__(self, name: Any, cpf: Any, birth: Any, address: Any) -> None:
        self.D001_name: Any = name
        self.D001_cpf: Any = cpf
        self.D001_birth: Any = birth
        self.D001_address: Any = address
        self.D001_accounts: List[C001_AccountCLS] = []

    def D001_add_accountMTD(self, account: C001_AccountCLS) -> None:
        if account is None:
            raise ValueError("account is required")
        if account in self.D001_accounts:
            return
        self.D001_accounts.append(account)


class E001_IteratorAccountCLS(Iterator[C001_AccountCLS]):
    def __init__(self, accounts: List[C001_AccountCLS]) -> None:
        self._accounts: List[C001_AccountCLS] = list(accounts)
        self._index: int = 0

    def __iter__(self) -> "E001_IteratorAccountCLS":
        return self

    def __next__(self) -> C001_AccountCLS:
        if self._index >= len(self._accounts):
            raise StopIteration
        item = self._accounts[self._index]
        self._index += 1
        return item