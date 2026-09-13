from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Sequence, Dict, Type


class CPFValidationError(ValueError):
    pass


class BankingError(Exception):
    pass


class AccountNotFoundError(BankingError):
    pass


class ClientNotFoundError(BankingError):
    pass


class TransactionError(BankingError):
    pass


class InsufficientFundsError(TransactionError):
    pass


class WithdrawalLimitError(TransactionError):
    pass


class InvalidAmountError(TransactionError):
    pass


class DuplicateCPFError(BankingError):
    pass


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
    def validate(value: str) -> str:
        cpf = CPF.normalize(value)
        if not CPF.is_valid(cpf):
            raise CPFValidationError("Invalid CPF.")
        return cpf


@dataclass(frozen=True)
class TransactionRecord:
    timestamp: datetime
    transaction_type: str
    amount: float
    success: bool
    message: str
    balance_after: float


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
    def transaction_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: AbstractAccount) -> TransactionRecord:
        raise NotImplementedError


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, owner: Client) -> None:
        self._number = int(number)
        self._agency = str(agency)
        self._owner = owner
        self._balance: float = 0.0
        self._transactions: List[TransactionRecord] = []

    @property
    def number(self) -> int:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def owner(self) -> Client:
        return self._owner

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> Sequence[TransactionRecord]:
        return tuple(self._transactions)

    def _record(self, record: TransactionRecord) -> None:
        self._transactions.append(record)

    def perform(self, transaction: AbstractTransaction) -> TransactionRecord:
        record = transaction.apply(self)
        self._record(record)
        return record

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise InvalidAmountError("Deposit amount must be positive.")
        self._balance += float(amount)

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def _ensure_sufficient_funds(self, amount: float) -> None:
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")


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
    def transaction_type(self) -> str:
        return "DEPOSIT"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        try:
            account.deposit(self._amount)
            return TransactionRecord(
                timestamp=self._timestamp,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=True,
                message="Deposit successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=self._timestamp,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=False,
                message=str(e),
                balance_after=account.balance,
            )


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
    def transaction_type(self) -> str:
        return "WITHDRAW"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        try:
            account.withdraw(self._amount)
            return TransactionRecord(
                timestamp=self._timestamp,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=True,
                message="Withdrawal successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=self._timestamp,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=False,
                message=str(e),
                balance_after=account.balance,
            )


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
        if account.owner is not self:
            raise BankingError("Account owner mismatch.")
        self._accounts.append(account)

    def get_account(self, number: int) -> Optional[AbstractAccount]:
        for acc in self._accounts:
            if acc.number == number:
                return acc
        return None


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str, birth_date: str, address: str) -> None:
        super().__init__(address=address)
        self._name = str(name).strip()
        self._cpf = CPF.validate(cpf)
        self._birth_date = str(birth_date).strip()

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def birth_date(self) -> str:
        return self._birth_date


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        owner: Client,
        withdrawal_limit_per_transaction: float = 500.0,
        daily_withdrawal_count_limit: int = 3,
    ) -> None:
        super().__init__(number=number, agency=agency, owner=owner)
        self._withdrawal_limit_per_transaction = float(withdrawal_limit_per_transaction)
        self._daily_withdrawal_count_limit = int(daily_withdrawal_count_limit)

    @property
    def withdrawal_limit_per_transaction(self) -> float:
        return self._withdrawal_limit_per_transaction

    @property
    def daily_withdrawal_count_limit(self) -> int:
        return self._daily_withdrawal_count_limit

    def _withdrawals_today_count(self) -> int:
        today = date.today()
        return sum(
            1
            for r in self._transactions
            if r.success and r.transaction_type == "WITHDRAW" and r.timestamp.date() == today
        )

    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")
        if amount > self._withdrawal_limit_per_transaction:
            raise WithdrawalLimitError("Withdrawal exceeds per-transaction limit.")
        if self._withdrawals_today_count() >= self._daily_withdrawal_count_limit:
            raise WithdrawalLimitError("Daily withdrawal count limit reached.")
        self._ensure_sufficient_funds(amount)
        self._balance -= amount


class ContaPoupanca(AbstractAccount):
    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise InvalidAmountError("Withdrawal amount must be positive.")
        self._ensure_sufficient_funds(amount)
        self._balance -= amount


class Bank:
    def __init__(self, agency: str = "0001") -> None:
        self._agency = str(agency)
        self._clients_by_cpf: Dict[str, PessoaFisica] = {}
        self._accounts_by_number: Dict[int, AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def agency(self) -> str:
        return self._agency

    def create_individual_client(self, name: str, cpf: str, birth_date: str, address: str) -> PessoaFisica:
        normalized = CPF.validate(cpf)
        if normalized in self._clients_by_cpf:
            raise DuplicateCPFError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=normalized, birth_date=birth_date, address=address)
        self._clients_by_cpf[normalized] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> PessoaFisica:
        normalized = CPF.validate(cpf)
        client = self._clients_by_cpf.get(normalized)
        if not client:
            raise ClientNotFoundError("Client not found.")
        return client

    def create_account(self, cpf: str, account_type: str) -> AbstractAccount:
        client = self.get_client_by_cpf(cpf)
        account_cls: Type[AbstractAccount]
        key = account_type.strip().lower()
        if key in {"cc", "corrente", "contacorrente", "current", "currentaccount"}:
            account_cls = ContaCorrente
        elif key in {"cp", "poupanca", "contapoupanca", "savings", "savingsaccount"}:
            account_cls = ContaPoupanca
        else:
            raise BankingError("Invalid account type.")

        number = self._next_account_number
        self._next_account_number += 1
        account = account_cls(number=number, agency=self._agency, owner=client)
        client.add_account(account)
        self._accounts_by_number[number] = account
        return account

    def get_account(self, number: int) -> AbstractAccount:
        acc = self._accounts_by_number.get(int(number))
        if not acc:
            raise AccountNotFoundError("Account not found.")
        return acc

    def deposit(self, account_number: int, amount: float) -> TransactionRecord:
        account = self.get_account(account_number)
        return account.perform(Deposit(amount))

    def withdraw(self, account_number: int, amount: float) -> TransactionRecord:
        account = self.get_account(account_number)
        return account.perform(Withdrawal(amount))

    def list_client_accounts(self, cpf: str) -> Sequence[AbstractAccount]:
        client = self.get_client_by_cpf(cpf)
        return client.accounts


class CLI:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def _input_nonempty(self, prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("Value cannot be empty.")

    def _input_float(self, prompt: str) -> float:
        while True:
            raw = input(prompt).strip().replace(",", ".")
            try:
                value = float(raw)
                return value
            except ValueError:
                print("Invalid number.")

    def _input_int(self, prompt: str) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                return int(raw)
            except ValueError:
                print("Invalid integer.")

    def _print_account(self, acc: AbstractAccount) -> None:
        owner = acc.owner
        owner_desc = ""
        if isinstance(owner, PessoaFisica):
            owner_desc = f"{owner.name} (CPF: {owner.cpf})"
        else:
            owner_desc = "Unknown owner"
        print(f"Account #{acc.number} | Agency {acc.agency} | Balance: {acc.balance:.2f} | Owner: {owner_desc}")

    def _print_history(self, acc: AbstractAccount) -> None:
        if not acc.history:
            print("No transactions.")
            return
        for r in acc.history:
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = "OK" if r.success else "FAIL"
            print(f"{ts} | {r.transaction_type:<8} | {r.amount:>10.2f} | {status:<4} | Bal: {r.balance_after:>10.2f} | {r.message}")

    def run(self) -> None:
        menu = (
            "\n--- BANK MENU ---\n"
            "1) Create individual client\n"
            "2) Create account (current/savings)\n"
            "3) Deposit\n"
            "4) Withdraw\n"
            "5) List client accounts\n"
            "6) Account history\n"
            "0) Exit\n"
        )
        while True:
            print(menu)
            choice = input("Select: ").strip()
            try:
                if choice == "1":
                    name = self._input_nonempty("Name: ")
                    cpf = self._input_nonempty("CPF: ")
                    birth_date = self._input_nonempty("Birth date: ")
                    address = self._input_nonempty("Address: ")
                    client = self._bank.create_individual_client(name=name, cpf=cpf, birth_date=birth_date, address=address)
                    print(f"Client created: {client.name} (CPF: {client.cpf})")
                elif choice == "2":
                    cpf = self._input_nonempty("CPF: ")
                    acc_type = self._input_nonempty("Account type (cc/cp): ")
                    acc = self._bank.create_account(cpf=cpf, account_type=acc_type)
                    self._print_account(acc)
                elif choice == "3":
                    number = self._input_int("Account number: ")
                    amount = self._input_float("Amount: ")
                    record = self._bank.deposit(account_number=number, amount=amount)
                    print(record.message)
                    print(f"Balance: {record.balance_after:.2f}")
                elif choice == "4":
                    number = self._input_int("Account number: ")
                    amount = self._input_float("Amount: ")
                    record = self._bank.withdraw(account_number=number, amount=amount)
                    print(record.message)
                    print(f"Balance: {record.balance_after:.2f}")
                elif choice == "5":
                    cpf = self._input_nonempty("CPF: ")
                    accounts = self._bank.list_client_accounts(cpf=cpf)
                    if not accounts:
                        print("No accounts.")
                    for acc in accounts:
                        self._print_account(acc)
                elif choice == "6":
                    number = self._input_int("Account number: ")
                    acc = self._bank.get_account(number)
                    self._print_account(acc)
                    self._print_history(acc)
                elif choice == "0":
                    return
                else:
                    print("Invalid option.")
            except Exception as e:
                print(f"Error: {e}")


def main() -> None:
    bank = Bank(agency="0001")
    CLI(bank).run()


if __name__ == "__main__":
    main()