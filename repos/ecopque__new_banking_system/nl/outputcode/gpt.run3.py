from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Sequence, Dict, Type


class CPF:
    @staticmethod
    def normalize(value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits

    @staticmethod
    def is_valid(value: str) -> bool:
        cpf = CPF.normalize(value)
        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False

        def calc_digit(base: str, factor_start: int) -> str:
            total = 0
            factor = factor_start
            for ch in base:
                total += int(ch) * factor
                factor -= 1
            remainder = (total * 10) % 11
            if remainder == 10:
                remainder = 0
            return str(remainder)

        d1 = calc_digit(cpf[:9], 10)
        d2 = calc_digit(cpf[:9] + d1, 11)
        return cpf[-2:] == d1 + d2

    @staticmethod
    def validate_or_raise(value: str) -> str:
        cpf = CPF.normalize(value)
        if not CPF.is_valid(cpf):
            raise ValueError("Invalid CPF.")
        return cpf


class AbstractTransaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def timestamp(self) -> datetime:
        raise NotImplementedError

    @property
    @abstractmethod
    def type_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: "AbstractAccount") -> bool:
        raise NotImplementedError


@dataclass(frozen=True)
class TransactionRecord:
    type_name: str
    amount: float
    timestamp: datetime


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, client: "Client") -> None:
        self._number = int(number)
        self._agency = str(agency)
        self._client = client
        self._balance: float = 0.0
        self._history: List[TransactionRecord] = []

    @property
    def number(self) -> int:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def client(self) -> "Client":
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> Sequence[TransactionRecord]:
        return tuple(self._history)

    def _add_history(self, record: TransactionRecord) -> None:
        self._history.append(record)

    def deposit(self, amount: float) -> bool:
        if not isinstance(amount, (int, float)):
            return False
        amount = float(amount)
        if amount <= 0:
            return False
        self._balance += amount
        self._add_history(TransactionRecord("Deposit", amount, datetime.now()))
        return True

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        raise NotImplementedError

    def perform(self, transaction: AbstractTransaction) -> bool:
        if not isinstance(transaction, AbstractTransaction):
            return False
        return transaction.apply(self)


class SavingsAccount(AbstractAccount):
    def withdraw(self, amount: float) -> bool:
        if not isinstance(amount, (int, float)):
            return False
        amount = float(amount)
        if amount <= 0:
            return False
        if amount > self._balance:
            return False
        self._balance -= amount
        self._add_history(TransactionRecord("Withdrawal", amount, datetime.now()))
        return True


class CurrentAccount(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        client: "Client",
        withdrawal_limit: float = 500.0,
        daily_withdrawal_count_limit: int = 3,
    ) -> None:
        super().__init__(number=number, agency=agency, client=client)
        self._withdrawal_limit = float(withdrawal_limit)
        self._daily_withdrawal_count_limit = int(daily_withdrawal_count_limit)

    @property
    def withdrawal_limit(self) -> float:
        return self._withdrawal_limit

    @property
    def daily_withdrawal_count_limit(self) -> int:
        return self._daily_withdrawal_count_limit

    def _withdrawals_today_count(self) -> int:
        today = date.today()
        count = 0
        for rec in self._history:
            if rec.type_name == "Withdrawal" and rec.timestamp.date() == today:
                count += 1
        return count

    def withdraw(self, amount: float) -> bool:
        if not isinstance(amount, (int, float)):
            return False
        amount = float(amount)
        if amount <= 0:
            return False
        if amount > self._withdrawal_limit:
            return False
        if self._withdrawals_today_count() >= self._daily_withdrawal_count_limit:
            return False
        if amount > self._balance:
            return False
        self._balance -= amount
        self._add_history(TransactionRecord("Withdrawal", amount, datetime.now()))
        return True


class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)
        self._timestamp = datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def type_name(self) -> str:
        return "Deposit"

    def apply(self, account: AbstractAccount) -> bool:
        if not isinstance(account, AbstractAccount):
            return False
        return account.deposit(self._amount)


class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)
        self._timestamp = datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def type_name(self) -> str:
        return "Withdrawal"

    def apply(self, account: AbstractAccount) -> bool:
        if not isinstance(account, AbstractAccount):
            return False
        return account.withdraw(self._amount)


class Client(ABC):
    def __init__(self, address: str) -> None:
        self._address = str(address)
        self._accounts: List[AbstractAccount] = []

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def add_account(self, account: AbstractAccount) -> None:
        if not isinstance(account, AbstractAccount):
            raise TypeError("Invalid account.")
        if account in self._accounts:
            return
        self._accounts.append(account)

    def get_account(self, number: int) -> Optional[AbstractAccount]:
        for acc in self._accounts:
            if acc.number == number:
                return acc
        return None


class Individual(Client):
    def __init__(self, name: str, cpf: str, birth_date: str, address: str) -> None:
        super().__init__(address=address)
        self._name = str(name).strip()
        self._cpf = CPF.validate_or_raise(cpf)
        self._birth_date = str(birth_date).strip()
        if not self._name:
            raise ValueError("Name is required.")
        if not self._birth_date:
            raise ValueError("Birth date is required.")

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def birth_date(self) -> str:
        return self._birth_date


class Bank:
    def __init__(self, agency: str = "0001") -> None:
        self._agency = str(agency)
        self._clients_by_cpf: Dict[str, Individual] = {}
        self._accounts_by_number: Dict[int, AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def agency(self) -> str:
        return self._agency

    def create_individual(self, name: str, cpf: str, birth_date: str, address: str) -> Individual:
        normalized = CPF.validate_or_raise(cpf)
        if normalized in self._clients_by_cpf:
            raise ValueError("Client already exists.")
        client = Individual(name=name, cpf=normalized, birth_date=birth_date, address=address)
        self._clients_by_cpf[normalized] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> Optional[Individual]:
        normalized = CPF.normalize(cpf)
        return self._clients_by_cpf.get(normalized)

    def _allocate_account_number(self) -> int:
        number = self._next_account_number
        self._next_account_number += 1
        return number

    def create_account(self, cpf: str, account_type: Type[AbstractAccount]) -> AbstractAccount:
        client = self.get_client_by_cpf(cpf)
        if client is None:
            raise ValueError("Client not found.")
        if account_type not in (CurrentAccount, SavingsAccount):
            raise ValueError("Invalid account type.")
        number = self._allocate_account_number()
        account = account_type(number=number, agency=self._agency, client=client)  # type: ignore[call-arg]
        client.add_account(account)
        self._accounts_by_number[number] = account
        return account

    def get_account(self, number: int) -> Optional[AbstractAccount]:
        return self._accounts_by_number.get(int(number))

    def deposit(self, account_number: int, amount: float) -> bool:
        account = self.get_account(account_number)
        if account is None:
            return False
        return account.perform(Deposit(amount))

    def withdraw(self, account_number: int, amount: float) -> bool:
        account = self.get_account(account_number)
        if account is None:
            return False
        return account.perform(Withdrawal(amount))


class CLI:
    def __init__(self, bank: Optional[Bank] = None) -> None:
        self._bank = bank or Bank()

    @property
    def bank(self) -> Bank:
        return self._bank

    def _input_nonempty(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("Value is required.")

    def _input_float(self, prompt: str) -> float:
        while True:
            raw = input(prompt).strip().replace(",", ".")
            try:
                return float(raw)
            except ValueError:
                print("Invalid number.")

    def _input_int(self, prompt: str) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                return int(raw)
            except ValueError:
                print("Invalid integer.")

    def _select_account(self) -> Optional[AbstractAccount]:
        number = self._input_int("Account number: ")
        account = self._bank.get_account(number)
        if account is None:
            print("Account not found.")
        return account

    def _print_account_statement(self, account: AbstractAccount) -> None:
        print(f"Agency: {account.agency}  Account: {account.number}")
        if isinstance(account.client, Individual):
            print(f"Client: {account.client.name}  CPF: {account.client.cpf}")
        print(f"Balance: {account.balance:.2f}")
        print("History:")
        if not account.history:
            print("  (no transactions)")
            return
        for rec in account.history:
            ts = rec.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {ts} - {rec.type_name}: {rec.amount:.2f}")

    def run(self) -> None:
        menu = (
            "\n"
            "[1] Create individual client\n"
            "[2] Create current account\n"
            "[3] Create savings account\n"
            "[4] Deposit\n"
            "[5] Withdraw\n"
            "[6] Statement\n"
            "[0] Exit\n"
        )
        while True:
            print(menu)
            option = input("Select: ").strip()
            if option == "1":
                name = self._input_nonempty("Name: ")
                cpf = self._input_nonempty("CPF: ")
                birth_date = self._input_nonempty("Birth date: ")
                address = self._input_nonempty("Address: ")
                try:
                    client = self._bank.create_individual(name=name, cpf=cpf, birth_date=birth_date, address=address)
                    print(f"Client created: {client.name} (CPF {client.cpf})")
                except ValueError as e:
                    print(str(e))
            elif option == "2":
                cpf = self._input_nonempty("CPF: ")
                try:
                    acc = self._bank.create_account(cpf=cpf, account_type=CurrentAccount)
                    print(f"Current account created: {acc.number} (Agency {acc.agency})")
                except ValueError as e:
                    print(str(e))
            elif option == "3":
                cpf = self._input_nonempty("CPF: ")
                try:
                    acc = self._bank.create_account(cpf=cpf, account_type=SavingsAccount)
                    print(f"Savings account created: {acc.number} (Agency {acc.agency})")
                except ValueError as e:
                    print(str(e))
            elif option == "4":
                account = self._select_account()
                if account is None:
                    continue
                amount = self._input_float("Amount: ")
                if self._bank.deposit(account.number, amount):
                    print("Deposit successful.")
                else:
                    print("Deposit failed.")
            elif option == "5":
                account = self._select_account()
                if account is None:
                    continue
                amount = self._input_float("Amount: ")
                if self._bank.withdraw(account.number, amount):
                    print("Withdrawal successful.")
                else:
                    print("Withdrawal failed.")
            elif option == "6":
                account = self._select_account()
                if account is None:
                    continue
                self._print_account_statement(account)
            elif option == "0":
                return
            else:
                print("Invalid option.")


def main() -> None:
    CLI().run()


if __name__ == "__main__":
    main()