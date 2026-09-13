from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Sequence, Type


class CPFValidationError(ValueError):
    pass


class BankingError(Exception):
    pass


class AccountNotFoundError(BankingError):
    pass


class ClientNotFoundError(BankingError):
    pass


class InsufficientFundsError(BankingError):
    pass


class InvalidAmountError(BankingError):
    pass


class WithdrawalLimitError(BankingError):
    pass


class DailyWithdrawalLimitError(BankingError):
    pass


class DuplicateCPFError(BankingError):
    pass


class DuplicateAccountError(BankingError):
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

        def calc_digit(base: str, factor_start: int) -> int:
            total = 0
            factor = factor_start
            for ch in base:
                total += int(ch) * factor
                factor -= 1
            remainder = (total * 10) % 11
            return 0 if remainder == 10 else remainder

        d1 = calc_digit(cpf[:9], 10)
        d2 = calc_digit(cpf[:9] + str(d1), 11)
        return cpf[-2:] == f"{d1}{d2}"

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
    balance_after: float


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
    def apply(self, account: AbstractAccount) -> TransactionRecord:
        raise NotImplementedError


class AbstractAccount(ABC):
    def __init__(self, agency: str, number: int) -> None:
        self._agency = agency
        self._number = number
        self._balance: float = 0.0
        self._history: List[TransactionRecord] = []

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def number(self) -> int:
        return self._number

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> Sequence[TransactionRecord]:
        return tuple(self._history)

    def perform(self, transaction: AbstractTransaction) -> TransactionRecord:
        record = transaction.apply(self)
        self._history.append(record)
        return record

    def _validate_amount(self, amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise InvalidAmountError("Amount must be numeric.")
        if amount <= 0:
            raise InvalidAmountError("Amount must be greater than zero.")

    def deposit(self, amount: float) -> None:
        self._validate_amount(amount)
        self._balance += float(amount)

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def _require_funds(self, amount: float) -> None:
        if self._balance < amount:
            raise InsufficientFundsError("Insufficient funds.")


class ContaPoupanca(AbstractAccount):
    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        self._require_funds(float(amount))
        self._balance -= float(amount)


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        agency: str,
        number: int,
        withdrawal_limit: float = 500.0,
        daily_withdrawal_count_limit: int = 3,
    ) -> None:
        super().__init__(agency, number)
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
            if (
                rec.success
                and rec.transaction_type == "withdraw"
                and rec.timestamp.date() == today
            ):
                count += 1
        return count

    def withdraw(self, amount: float) -> None:
        self._validate_amount(amount)
        amount_f = float(amount)

        if amount_f > self._withdrawal_limit:
            raise WithdrawalLimitError("Withdrawal amount exceeds account limit.")

        if self._withdrawals_today_count() >= self._daily_withdrawal_count_limit:
            raise DailyWithdrawalLimitError("Daily withdrawal count limit reached.")

        self._require_funds(amount_f)
        self._balance -= amount_f


class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "deposit"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.deposit(self._amount)
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=True,
                message="Deposit successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=False,
                message=str(e),
                balance_after=account.balance,
            )


class Withdraw(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "withdraw"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.withdraw(self._amount)
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=True,
                message="Withdrawal successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=ts,
                transaction_type=self.transaction_type,
                amount=self._amount,
                success=False,
                message=str(e),
                balance_after=account.balance,
            )


class Client(ABC):
    def __init__(self, name: str) -> None:
        self._name = name.strip()
        self._accounts: List[AbstractAccount] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def add_account(self, account: AbstractAccount) -> None:
        for acc in self._accounts:
            if acc.agency == account.agency and acc.number == account.number:
                raise DuplicateAccountError("Client already has this account.")
        self._accounts.append(account)

    def get_account(self, agency: str, number: int) -> AbstractAccount:
        for acc in self._accounts:
            if acc.agency == agency and acc.number == number:
                return acc
        raise AccountNotFoundError("Account not found for this client.")

    @property
    @abstractmethod
    def identifier(self) -> str:
        raise NotImplementedError


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str) -> None:
        super().__init__(name)
        self._cpf = CPFValidator.validate(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def identifier(self) -> str:
        return self._cpf


class Bank:
    def __init__(self, name: str, default_agency: str = "0001") -> None:
        self._name = name.strip()
        self._default_agency = default_agency
        self._clients_by_cpf: Dict[str, PessoaFisica] = {}
        self._accounts_by_key: Dict[tuple[str, int], AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_agency(self) -> str:
        return self._default_agency

    def create_individual_client(self, name: str, cpf: str) -> PessoaFisica:
        cpf_n = CPFValidator.validate(cpf)
        if cpf_n in self._clients_by_cpf:
            raise DuplicateCPFError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=cpf_n)
        self._clients_by_cpf[cpf_n] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> PessoaFisica:
        cpf_n = CPFValidator.validate(cpf)
        client = self._clients_by_cpf.get(cpf_n)
        if not client:
            raise ClientNotFoundError("Client not found.")
        return client

    def _allocate_account_number(self) -> int:
        n = self._next_account_number
        self._next_account_number += 1
        return n

    def create_account_for_client(
        self,
        cpf: str,
        account_type: Type[AbstractAccount],
        agency: Optional[str] = None,
        **kwargs,
    ) -> AbstractAccount:
        client = self.get_client_by_cpf(cpf)
        agency_use = agency if agency is not None else self._default_agency
        number = self._allocate_account_number()
        account = account_type(agency_use, number, **kwargs)
        key = (account.agency, account.number)
        if key in self._accounts_by_key:
            raise DuplicateAccountError("Account already exists.")
        self._accounts_by_key[key] = account
        client.add_account(account)
        return account

    def find_account(self, agency: str, number: int) -> AbstractAccount:
        acc = self._accounts_by_key.get((agency, number))
        if not acc:
            raise AccountNotFoundError("Account not found.")
        return acc

    def deposit(self, cpf: str, agency: str, number: int, amount: float) -> TransactionRecord:
        client = self.get_client_by_cpf(cpf)
        account = client.get_account(agency, number)
        record = account.perform(Deposit(amount))
        return record

    def withdraw(self, cpf: str, agency: str, number: int, amount: float) -> TransactionRecord:
        client = self.get_client_by_cpf(cpf)
        account = client.get_account(agency, number)
        record = account.perform(Withdraw(amount))
        return record


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

    def _select_account(self, client: PessoaFisica) -> Optional[AbstractAccount]:
        if not client.accounts:
            print("Client has no accounts.")
            return None
        print("Accounts:")
        for idx, acc in enumerate(client.accounts, start=1):
            print(f"{idx}. Agency {acc.agency} Account {acc.number} Balance {acc.balance:.2f}")
        while True:
            choice = self._input_int("Select account number (list index): ")
            if 1 <= choice <= len(client.accounts):
                return client.accounts[choice - 1]
            print("Invalid selection.")

    def _print_history(self, account: AbstractAccount) -> None:
        if not account.history:
            print("No transactions.")
            return
        for rec in account.history:
            ts = rec.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = "OK" if rec.success else "FAIL"
            print(
                f"{ts} | {rec.transaction_type.upper():8} | {rec.amount:10.2f} | {status:4} | "
                f"Balance: {rec.balance_after:10.2f} | {rec.message}"
            )

    def run(self) -> None:
        menu = (
            "\n=== Banking System ===\n"
            "1. Create individual client (CPF)\n"
            "2. Create checking account (ContaCorrente)\n"
            "3. Create savings account (ContaPoupanca)\n"
            "4. Deposit\n"
            "5. Withdraw\n"
            "6. Show account history\n"
            "7. List client accounts\n"
            "0. Exit\n"
        )
        while True:
            print(menu)
            option = input("Choose an option: ").strip()
            try:
                if option == "1":
                    name = self._input_nonempty("Name: ")
                    cpf = self._input_nonempty("CPF: ")
                    client = self._bank.create_individual_client(name, cpf)
                    print(f"Client created: {client.name} CPF {client.cpf}")
                elif option == "2":
                    cpf = self._input_nonempty("CPF: ")
                    acc = self._bank.create_account_for_client(cpf, ContaCorrente)
                    print(f"Checking account created: Agency {acc.agency} Account {acc.number}")
                elif option == "3":
                    cpf = self._input_nonempty("CPF: ")
                    acc = self._bank.create_account_for_client(cpf, ContaPoupanca)
                    print(f"Savings account created: Agency {acc.agency} Account {acc.number}")
                elif option == "4":
                    cpf = self._input_nonempty("CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    acc = self._select_account(client)
                    if not acc:
                        continue
                    amount = self._input_float("Deposit amount: ")
                    rec = self._bank.deposit(client.cpf, acc.agency, acc.number, amount)
                    print(rec.message)
                    print(f"Balance: {rec.balance_after:.2f}")
                elif option == "5":
                    cpf = self._input_nonempty("CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    acc = self._select_account(client)
                    if not acc:
                        continue
                    amount = self._input_float("Withdrawal amount: ")
                    rec = self._bank.withdraw(client.cpf, acc.agency, acc.number, amount)
                    print(rec.message)
                    print(f"Balance: {rec.balance_after:.2f}")
                elif option == "6":
                    cpf = self._input_nonempty("CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    acc = self._select_account(client)
                    if not acc:
                        continue
                    self._print_history(acc)
                elif option == "7":
                    cpf = self._input_nonempty("CPF: ")
                    client = self._bank.get_client_by_cpf(cpf)
                    if not client.accounts:
                        print("No accounts.")
                    else:
                        for acc in client.accounts:
                            print(f"Agency {acc.agency} Account {acc.number} Balance {acc.balance:.2f}")
                elif option == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Invalid option.")
            except CPFValidationError as e:
                print(str(e))
            except BankingError as e:
                print(str(e))
            except Exception as e:
                print(f"Unexpected error: {e}")


def main() -> None:
    bank = Bank(name="Bank", default_agency="0001")
    CLI(bank).run()


if __name__ == "__main__":
    main()