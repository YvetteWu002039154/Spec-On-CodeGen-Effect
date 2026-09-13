from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Sequence, Type


class CPFValidationError(ValueError):
    pass


class BusinessRuleError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def validate_cpf(cpf: str) -> str:
    cpf_digits = _only_digits(cpf or "")
    if len(cpf_digits) != 11:
        raise CPFValidationError("CPF must have 11 digits.")
    if cpf_digits == cpf_digits[0] * 11:
        raise CPFValidationError("Invalid CPF.")

    def calc_digit(base: str, factor_start: int) -> str:
        total = 0
        factor = factor_start
        for ch in base:
            total += int(ch) * factor
            factor -= 1
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        return str(digit)

    d1 = calc_digit(cpf_digits[:9], 10)
    d2 = calc_digit(cpf_digits[:9] + d1, 11)
    if cpf_digits[-2:] != d1 + d2:
        raise CPFValidationError("Invalid CPF.")
    return cpf_digits


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
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: AbstractAccount) -> TransactionRecord:
        raise NotImplementedError


class Deposit(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def name(self) -> str:
        return "DEPOSIT"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.deposit(self._amount)
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.name,
                amount=self._amount,
                success=True,
                message="Deposit successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.name,
                amount=self._amount,
                success=False,
                message=str(e),
                balance_after=account.balance,
            )


class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def name(self) -> str:
        return "WITHDRAWAL"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.withdraw(self._amount)
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.name,
                amount=self._amount,
                success=True,
                message="Withdrawal successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.name,
                amount=self._amount,
                success=False,
                message=str(e),
                balance_after=account.balance,
            )


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, owner: Client):
        self._number = int(number)
        self._agency = str(agency)
        self._owner = owner
        self._balance: float = 0.0
        self._history: List[TransactionRecord] = []

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
        return tuple(self._history)

    def _add_record(self, record: TransactionRecord) -> None:
        self._history.append(record)

    def perform(self, transaction: AbstractTransaction) -> TransactionRecord:
        record = transaction.apply(self)
        self._add_record(record)
        return record

    def deposit(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise BusinessRuleError("Deposit amount must be positive.")
        self._balance += amount

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def _count_withdrawals_on(self, day: date) -> int:
        count = 0
        for rec in self._history:
            if rec.success and rec.transaction_type == "WITHDRAWAL" and rec.timestamp.date() == day:
                count += 1
        return count

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agency={self._agency!r}, number={self._number}, owner={self._owner.name!r}, balance={self._balance:.2f})"


class SavingsAccount(AbstractAccount):
    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise BusinessRuleError("Withdrawal amount must be positive.")
        if amount > self._balance:
            raise BusinessRuleError("Insufficient funds.")
        self._balance -= amount


class CurrentAccount(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        owner: Client,
        withdrawal_limit_per_transaction: float = 500.0,
        daily_withdrawal_limit: int = 3,
    ):
        super().__init__(number=number, agency=agency, owner=owner)
        self._withdrawal_limit_per_transaction = float(withdrawal_limit_per_transaction)
        self._daily_withdrawal_limit = int(daily_withdrawal_limit)

    @property
    def withdrawal_limit_per_transaction(self) -> float:
        return self._withdrawal_limit_per_transaction

    @property
    def daily_withdrawal_limit(self) -> int:
        return self._daily_withdrawal_limit

    def withdraw(self, amount: float) -> None:
        amount = float(amount)
        if amount <= 0:
            raise BusinessRuleError("Withdrawal amount must be positive.")
        if amount > self._withdrawal_limit_per_transaction:
            raise BusinessRuleError("Withdrawal exceeds per-transaction limit.")
        today = datetime.now().date()
        if self._count_withdrawals_on(today) >= self._daily_withdrawal_limit:
            raise BusinessRuleError("Daily withdrawal limit reached.")
        if amount > self._balance:
            raise BusinessRuleError("Insufficient funds.")
        self._balance -= amount


class Client(ABC):
    def __init__(self, name: str, address: str):
        self._name = str(name).strip()
        self._address = str(address).strip()
        self._accounts: List[AbstractAccount] = []

        if not self._name:
            raise ValueError("Client name is required.")
        if not self._address:
            raise ValueError("Client address is required.")

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
        if account.owner is not self:
            raise BusinessRuleError("Account owner mismatch.")
        if any(a.agency == account.agency and a.number == account.number for a in self._accounts):
            raise BusinessRuleError("Client already has an account with this agency/number.")
        self._accounts.append(account)

    def get_account(self, number: int, agency: Optional[str] = None) -> AbstractAccount:
        for acc in self._accounts:
            if acc.number == int(number) and (agency is None or acc.agency == agency):
                return acc
        raise NotFoundError("Account not found for this client.")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r})"


class Individual(Client):
    def __init__(self, name: str, address: str, cpf: str):
        super().__init__(name=name, address=address)
        self._cpf = validate_cpf(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r}, cpf={self._cpf!r})"


class Bank:
    def __init__(self, name: str, default_agency: str = "0001"):
        self._name = str(name).strip()
        self._default_agency = str(default_agency).strip()
        if not self._name:
            raise ValueError("Bank name is required.")
        if not self._default_agency:
            raise ValueError("Default agency is required.")

        self._clients_by_cpf: Dict[str, Individual] = {}
        self._accounts_by_key: Dict[tuple[str, int], AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_agency(self) -> str:
        return self._default_agency

    def create_individual(self, name: str, address: str, cpf: str) -> Individual:
        cpf_norm = validate_cpf(cpf)
        if cpf_norm in self._clients_by_cpf:
            raise BusinessRuleError("Client with this CPF already exists.")
        client = Individual(name=name, address=address, cpf=cpf_norm)
        self._clients_by_cpf[cpf_norm] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> Individual:
        cpf_norm = validate_cpf(cpf)
        try:
            return self._clients_by_cpf[cpf_norm]
        except KeyError as e:
            raise NotFoundError("Client not found.") from e

    def _register_account(self, account: AbstractAccount) -> None:
        key = (account.agency, account.number)
        if key in self._accounts_by_key:
            raise BusinessRuleError("Account already exists.")
        self._accounts_by_key[key] = account

    def create_account(
        self,
        client_cpf: str,
        account_type: Type[AbstractAccount],
        agency: Optional[str] = None,
        **kwargs,
    ) -> AbstractAccount:
        client = self.get_client_by_cpf(client_cpf)
        agency_final = self._default_agency if agency is None else str(agency).strip()
        if not agency_final:
            raise ValueError("Agency is required.")

        number = self._next_account_number
        self._next_account_number += 1

        if account_type is CurrentAccount:
            account = CurrentAccount(number=number, agency=agency_final, owner=client, **kwargs)
        elif account_type is SavingsAccount:
            account = SavingsAccount(number=number, agency=agency_final, owner=client)
        else:
            raise ValueError("Unsupported account type.")

        client.add_account(account)
        self._register_account(account)
        return account

    def get_account(self, agency: str, number: int) -> AbstractAccount:
        key = (str(agency), int(number))
        try:
            return self._accounts_by_key[key]
        except KeyError as e:
            raise NotFoundError("Account not found.") from e

    def list_clients(self) -> Sequence[Individual]:
        return tuple(self._clients_by_cpf.values())

    def list_accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts_by_key.values())


class CLI:
    def __init__(self, bank: Bank):
        self._bank = bank

    def _input_nonempty(self, prompt: str) -> str:
        value = input(prompt).strip()
        if not value:
            raise ValueError("Input cannot be empty.")
        return value

    def _input_float(self, prompt: str) -> float:
        raw = self._input_nonempty(prompt)
        try:
            return float(raw.replace(",", "."))
        except ValueError as e:
            raise ValueError("Invalid number.") from e

    def _select_account_for_client(self, client: Individual) -> AbstractAccount:
        accounts = list(client.accounts)
        if not accounts:
            raise NotFoundError("Client has no accounts.")
        if len(accounts) == 1:
            return accounts[0]
        print("Select an account:")
        for idx, acc in enumerate(accounts, start=1):
            print(f"{idx}. {acc.__class__.__name__} - Agency {acc.agency} - Number {acc.number} - Balance {acc.balance:.2f}")
        choice_raw = self._input_nonempty("Enter option: ")
        try:
            choice = int(choice_raw)
        except ValueError as e:
            raise ValueError("Invalid option.") from e
        if choice < 1 or choice > len(accounts):
            raise ValueError("Invalid option.")
        return accounts[choice - 1]

    def run(self) -> None:
        menu = (
            "\n=== BANK MENU ===\n"
            "1. Create individual client\n"
            "2. Create current account\n"
            "3. Create savings account\n"
            "4. Deposit\n"
            "5. Withdraw\n"
            "6. Show account statement\n"
            "7. List clients\n"
            "8. List accounts\n"
            "0. Exit\n"
        )
        while True:
            try:
                print(menu)
                option = input("Choose an option: ").strip()

                if option == "0":
                    print("Exiting.")
                    return

                if option == "1":
                    name = self._input_nonempty("Name: ")
                    address = self._input_nonempty("Address: ")
                    cpf = self._input_nonempty("CPF: ")
                    client = self._bank.create_individual(name=name, address=address, cpf=cpf)
                    print(f"Client created: {client.name} (CPF {client.cpf})")

                elif option == "2":
                    cpf = self._input_nonempty("Client CPF: ")
                    acc = self._bank.create_account(client_cpf=cpf, account_type=CurrentAccount)
                    print(f"Current account created: Agency {acc.agency} Number {acc.number}")

                elif option == "3":
                    cpf = self._input_nonempty("Client CPF: ")
                    acc = self._bank.create_account(client_cpf=cpf, account_type=SavingsAccount)
                    print(f"Savings account created: Agency {acc.agency} Number {acc.number}")

                elif option == "4":
                    cpf = self._input_nonempty("Client CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    acc = self._select_account_for_client(client)
                    amount = self._input_float("Deposit amount: ")
                    record = acc.perform(Deposit(amount))
                    print(record.message)
                    print(f"Balance: {acc.balance:.2f}")

                elif option == "5":
                    cpf = self._input_nonempty("Client CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    acc = self._select_account_for_client(client)
                    amount = self._input_float("Withdrawal amount: ")
                    record = acc.perform(Withdrawal(amount))
                    print(record.message)
                    print(f"Balance: {acc.balance:.2f}")

                elif option == "6":
                    cpf = self._input_nonempty("Client CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    acc = self._select_account_for_client(client)
                    print(f"\n=== STATEMENT ===\nOwner: {client.name} (CPF {client.cpf})")
                    print(f"Account: {acc.__class__.__name__} Agency {acc.agency} Number {acc.number}")
                    print(f"Current balance: {acc.balance:.2f}\n")
                    if not acc.history:
                        print("No transactions.")
                    else:
                        for rec in acc.history:
                            ts = rec.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                            status = "OK" if rec.success else "FAIL"
                            print(f"{ts} | {rec.transaction_type:<10} | {rec.amount:>10.2f} | {status} | Bal: {rec.balance_after:>10.2f} | {rec.message}")

                elif option == "7":
                    clients = self._bank.list_clients()
                    if not clients:
                        print("No clients.")
                    else:
                        for c in clients:
                            print(f"{c.name} | CPF {c.cpf} | Accounts: {len(c.accounts)}")

                elif option == "8":
                    accounts = self._bank.list_accounts()
                    if not accounts:
                        print("No accounts.")
                    else:
                        for a in accounts:
                            owner = a.owner
                            cpf = owner.cpf if isinstance(owner, Individual) else "N/A"
                            print(f"{a.__class__.__name__} | Agency {a.agency} | Number {a.number} | Owner {owner.name} | CPF {cpf} | Balance {a.balance:.2f}")

                else:
                    print("Invalid option.")

            except (CPFValidationError, BusinessRuleError, NotFoundError, ValueError) as e:
                print(f"Error: {e}")
            except KeyboardInterrupt:
                print("\nExiting.")
                return


def main() -> None:
    bank = Bank(name="Python Bank", default_agency="0001")
    CLI(bank).run()


if __name__ == "__main__":
    main()