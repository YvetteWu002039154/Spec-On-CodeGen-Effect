from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Generator, List, Optional, Type


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
    trans_type: str
    value: float
    trans_date: date


class B001_HistoryCLS:
    def __init__(self) -> None:
        self.B001_transactions: List[_HistoryTransactionRecord] = []

    def B001_add_transactionMTD(self, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(
            _HistoryTransactionRecord(
                description=description.strip(),
                trans_type="description",
                value=0.0,
                trans_date=date.today(),
            )
        )

    def _add_record(self, trans_type: str, value: float, description: str) -> None:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")
        self.B001_transactions.append(
            _HistoryTransactionRecord(
                description=description.strip(),
                trans_type=str(trans_type),
                value=float(value),
                trans_date=date.today(),
            )
        )

    def B001_transaction_generatorMTD(
        self, filter_type: Optional[Any]
    ) -> Generator[_HistoryTransactionRecord, None, None]:
        if filter_type is None:
            for t in self.B001_transactions:
                yield t
            return

        if isinstance(filter_type, str):
            ft = filter_type.strip().lower()
            for t in self.B001_transactions:
                if t.trans_type.lower() == ft:
                    yield t
            return

        if isinstance(filter_type, type):
            ft_cls: Type[Any] = filter_type
            for t in self.B001_transactions:
                if t.trans_type == ft_cls.__name__:
                    yield t
            return

        ft = str(filter_type).strip().lower()
        for t in self.B001_transactions:
            if t.trans_type.lower() == ft:
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

        self.C001_history: B001_HistoryCLS = B001_HistoryCLS()
        self.C001_last_trans_date: date = date.today()

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
            raise ValueError("value must not be None")
        value_f = float(value)
        if value_f <= 0:
            raise ValueError("deposit value must be positive")
        if not self._can_transact_today():
            return False

        self.C001_balance += int(round(value_f))
        self._increment_daily_count()
        self.C001_history._add_record(
            trans_type=A002_DepositCLS.__name__,
            value=value_f,
            description=f"Deposit: {value_f:.2f}",
        )
        return True

    def C001_withdrawMTD(self, value: float) -> bool:
        if value is None:
            raise ValueError("value must not be None")
        value_f = float(value)
        if value_f <= 0:
            raise ValueError("withdraw value must be positive")
        if not self._can_transact_today():
            return False

        amount = int(round(value_f))
        available = self.C001_balance + self.C001_limit
        if amount > available:
            return False

        self.C001_balance -= amount
        self._increment_daily_count()
        self.C001_history._add_record(
            trans_type=A003_WithdrawCLS.__name__,
            value=value_f,
            description=f"Withdraw: {value_f:.2f}",
        )
        return True

    def C001_transaction_reportMTD(
        self, filter_type: Optional[Any]
    ) -> Generator[_HistoryTransactionRecord, None, None]:
        return self.C001_history.B001_transaction_generatorMTD(filter_type)


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

    def _reset_withdrawals_if_new_day(self) -> None:
        self.C001__reset_transaction_count_if_new_dayMTD()
        if self.C001_last_trans_date != date.today():
            self.C002_number_withdrawals = 0

    def C002_withdrawMTD(self, value: float) -> bool:
        self._reset_withdrawals_if_new_day()
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
        if account is None:
            raise ValueError("account must not be None")
        self.D001_accounts.append(account)


class E001_IteratorAccountCLS:
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