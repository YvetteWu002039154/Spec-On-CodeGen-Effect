from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Sequence


class CPFValidationError(ValueError):
    pass


class AccountNotFoundError(ValueError):
    pass


class TransactionError(ValueError):
    pass


class InsufficientFundsError(TransactionError):
    pass


class InvalidAmountError(TransactionError):
    pass


class WithdrawalLimitError(TransactionError):
    pass


class DailyWithdrawalLimitError(TransactionError):
    pass


class CPFValidator:
    @staticmethod
    def normalize(cpf: str) -> str:
        digits = "".join(ch for ch in cpf if ch.isdigit())
        return digits

    @staticmethod
    def is_valid(cpf: str) -> bool:
        cpf = CPFValidator.normalize(cpf)
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
            return "0" if remainder == 10 else str(remainder)

        d1 = calc_digit(cpf[:9], 10)
        d2 = calc_digit(cpf[:9] + d1, 11)
        return cpf[-2:] == d1 + d2

    @staticmethod
    def validate(cpf: str) -> str:
        normalized = CPFValidator.normalize(cpf)
        if not CPFValidator.is_valid(normalized):
            raise CPFValidationError("Invalid CPF.")
        return normalized


@dataclass(frozen=True)
class TransactionRecord:
    timestamp: datetime
    transaction_type: str
    amount: float
    success: bool
    message: str


class TransactionHistory:
    def __init__(self) -> None:
        self._records: List[TransactionRecord] = []

    def add(self, record: TransactionRecord) -> None:
        self._records.append(record)

    def all(self) -> Sequence[TransactionRecord]:
        return tuple(self._records)

    def count_withdrawals_on(self, day: date) -> int:
        return sum(
            1
            for r in self._records
            if r.success and r.transaction_type == "withdraw" and r.timestamp.date() == day
        )


class AbstractTransaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def transaction_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: AbstractAccount) -> None:
        raise NotImplementedError


class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "deposit"

    def apply(self, account: AbstractAccount) -> None:
        account.deposit(self._amount)


class Withdraw(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "withdraw"

    def apply(self, account: AbstractAccount) -> None:
        account.withdraw(self._amount)


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, client: Client) -> None:
        self._number = int(number)
        self._agency = str(agency)
        self._client = client
        self._balance: float = 0.0
        self._history = TransactionHistory()

    @property
    def number(self) -> int:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def client(self) -> Client:
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> TransactionHistory:
        return self._history

    def deposit(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise InvalidAmountError("Deposit amount must be positive.")
        self._balance += amount

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def perform(self, transaction: AbstractTransaction) -> None:
        ts = datetime.now()
        try:
            transaction.apply(self)
            self._history.add(
                TransactionRecord(
                    timestamp=ts,
                    transaction_type=transaction.transaction_type,
                    amount=transaction.amount,
                    success=True,
                    message="OK",
                )
            )
        except Exception as exc:
            self._history.add(
                TransactionRecord(
                    timestamp=ts,
                    transaction_type=transaction.transaction_type,
                    amount=transaction.amount,
                    success=False,
                    message=str(exc),
                )
            )
            raise


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        client: Client,
        withdrawal_limit: float = 500.0,
        daily_withdrawal_limit: int = 3,
    ) -> None:
        super().__init__(number=number, agency=agency, client=client)
        self._withdrawal_limit = float(withdrawal_limit)
        self._daily_withdrawal_limit = int(daily_withdrawal_limit)

    @property
    def withdrawal_limit(self) -> float:
        return self._withdrawal_limit

    @property
    def daily_withdrawal_limit(self) -> int:
        return self._daily_withdrawal_limit

    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")
        if amount > self._withdrawal_limit:
            raise WithdrawalLimitError("Withdrawal exceeds per-transaction limit.")
        today = date.today()
        if self.history.count_withdrawals_on(today) >= self._daily_withdrawal_limit:
            raise DailyWithdrawalLimitError("Daily withdrawal limit reached.")
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")
        self._balance -= amount


class ContaPoupanca(AbstractAccount):
    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")
        self._balance -= amount


class Client(ABC):
    def __init__(self, name: str, address: str) -> None:
        self._name = str(name).strip()
        self._address = str(address).strip()
        self._accounts: List[AbstractAccount] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def add_account(self, account: AbstractAccount) -> None:
        if account.client is not self:
            raise ValueError("Account client mismatch.")
        if any(a.agency == account.agency and a.number == account.number for a in self._accounts):
            raise ValueError("Account already exists for this client.")
        self._accounts.append(account)

    def get_account(self, agency: str, number: int) -> AbstractAccount:
        for acc in self._accounts:
            if acc.agency == agency and acc.number == number:
                return acc
        raise AccountNotFoundError("Account not found for this client.")


class PessoaFisica(Client):
    def __init__(self, name: str, address: str, cpf: str) -> None:
        super().__init__(name=name, address=address)
        self._cpf = CPFValidator.validate(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf


class Bank:
    def __init__(self, name: str) -> None:
        self._name = str(name).strip()
        self._clients: List[Client] = []
        self._accounts: List[AbstractAccount] = []
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def clients(self) -> Sequence[Client]:
        return tuple(self._clients)

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def find_individual_by_cpf(self, cpf: str) -> Optional[PessoaFisica]:
        normalized = CPFValidator.normalize(cpf)
        for c in self._clients:
            if isinstance(c, PessoaFisica) and c.cpf == normalized:
                return c
        return None

    def add_client(self, client: Client) -> None:
        if isinstance(client, PessoaFisica):
            if self.find_individual_by_cpf(client.cpf) is not None:
                raise ValueError("Client with this CPF already exists.")
        self._clients.append(client)

    def _register_account(self, account: AbstractAccount) -> None:
        if any(a.agency == account.agency and a.number == account.number for a in self._accounts):
            raise ValueError("Account already exists in bank.")
        self._accounts.append(account)

    def create_current_account(self, client: Client, agency: str = "0001") -> ContaCorrente:
        number = self._next_account_number
        self._next_account_number += 1
        acc = ContaCorrente(number=number, agency=agency, client=client)
        client.add_account(acc)
        self._register_account(acc)
        return acc

    def create_savings_account(self, client: Client, agency: str = "0001") -> ContaPoupanca:
        number = self._next_account_number
        self._next_account_number += 1
        acc = ContaPoupanca(number=number, agency=agency, client=client)
        client.add_account(acc)
        self._register_account(acc)
        return acc

    def find_account(self, agency: str, number: int) -> AbstractAccount:
        for acc in self._accounts:
            if acc.agency == agency and acc.number == number:
                return acc
        raise AccountNotFoundError("Account not found.")

    def deposit(self, agency: str, number: int, amount: float) -> None:
        acc = self.find_account(agency, number)
        acc.perform(Deposit(amount))

    def withdraw(self, agency: str, number: int, amount: float) -> None:
        acc = self.find_account(agency, number)
        acc.perform(Withdraw(amount))


class CommandLineInterface:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def _input(self, prompt: str) -> str:
        return input(prompt)

    def _print(self, text: str) -> None:
        print(text)

    def _menu(self) -> str:
        return (
            "\n"
            "[1] Create individual client\n"
            "[2] Create current account\n"
            "[3] Create savings account\n"
            "[4] Deposit\n"
            "[5] Withdraw\n"
            "[6] Account statement\n"
            "[0] Exit\n"
        )

    def run(self) -> None:
        while True:
            self._print(self._menu())
            choice = self._input("Select an option: ").strip()

            try:
                if choice == "0":
                    return
                if choice == "1":
                    self._create_individual()
                elif choice == "2":
                    self._create_account(kind="current")
                elif choice == "3":
                    self._create_account(kind="savings")
                elif choice == "4":
                    self._do_deposit()
                elif choice == "5":
                    self._do_withdraw()
                elif choice == "6":
                    self._statement()
                else:
                    self._print("Invalid option.")
            except Exception as exc:
                self._print(f"Error: {exc}")

    def _create_individual(self) -> None:
        name = self._input("Name: ").strip()
        address = self._input("Address: ").strip()
        cpf = self._input("CPF: ").strip()
        client = PessoaFisica(name=name, address=address, cpf=cpf)
        self._bank.add_client(client)
        self._print("Client created.")

    def _select_client_by_cpf(self) -> PessoaFisica:
        cpf = self._input("CPF: ").strip()
        client = self._bank.find_individual_by_cpf(cpf)
        if client is None:
            raise ValueError("Client not found.")
        return client

    def _create_account(self, kind: str) -> None:
        client = self._select_client_by_cpf()
        agency = self._input("Agency (default 0001): ").strip() or "0001"
        if kind == "current":
            acc = self._bank.create_current_account(client=client, agency=agency)
            self._print(f"Current account created: agency={acc.agency} number={acc.number}")
        elif kind == "savings":
            acc = self._bank.create_savings_account(client=client, agency=agency)
            self._print(f"Savings account created: agency={acc.agency} number={acc.number}")
        else:
            raise ValueError("Invalid account type.")

    def _read_account_ref(self) -> tuple[str, int]:
        agency = self._input("Agency: ").strip()
        number_str = self._input("Account number: ").strip()
        if not number_str.isdigit():
            raise ValueError("Invalid account number.")
        return agency, int(number_str)

    def _do_deposit(self) -> None:
        agency, number = self._read_account_ref()
        amount = float(self._input("Amount: ").strip())
        self._bank.deposit(agency=agency, number=number, amount=amount)
        self._print("Deposit completed.")

    def _do_withdraw(self) -> None:
        agency, number = self._read_account_ref()
        amount = float(self._input("Amount: ").strip())
        self._bank.withdraw(agency=agency, number=number, amount=amount)
        self._print("Withdrawal completed.")

    def _statement(self) -> None:
        agency, number = self._read_account_ref()
        acc = self._bank.find_account(agency=agency, number=number)
        self._print(f"\nStatement - agency={acc.agency} number={acc.number}")
        self._print(f"Client: {acc.client.name}")
        self._print(f"Balance: {acc.balance:.2f}")
        records = acc.history.all()
        if not records:
            self._print("No transactions.")
            return
        for r in records:
            status = "OK" if r.success else "FAIL"
            self._print(
                f"{r.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | {r.transaction_type:<8} | "
                f"{r.amount:>10.2f} | {status} | {r.message}"
            )


def main() -> None:
    bank = Bank(name="Bank")
    cli = CommandLineInterface(bank)
    cli.run()


if __name__ == "__main__":
    main()