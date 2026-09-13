from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Sequence, Dict


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


class WithdrawalLimitError(TransactionError):
    pass


class InsufficientFundsError(TransactionError):
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
            digit = 0 if remainder == 10 else remainder
            return str(digit)

        d1 = calc_digit(cpf[:9], 10)
        d2 = calc_digit(cpf[:9] + d1, 11)
        return cpf[-2:] == d1 + d2

    @staticmethod
    def validate(value: str) -> str:
        cpf = CPF.normalize(value)
        if not CPF.is_valid(cpf):
            raise CPFValidationError("Invalid CPF.")
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
    def kind(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: AbstractAccount) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class Deposit(AbstractTransaction):
    _amount: float
    _timestamp: datetime = datetime.now()

    @property
    def amount(self) -> float:
        return float(self._amount)

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def kind(self) -> str:
        return "DEPOSIT"

    def apply(self, account: AbstractAccount) -> None:
        account._apply_deposit(self.amount)


@dataclass(frozen=True)
class Withdrawal(AbstractTransaction):
    _amount: float
    _timestamp: datetime = datetime.now()

    @property
    def amount(self) -> float:
        return float(self._amount)

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def kind(self) -> str:
        return "WITHDRAWAL"

    def apply(self, account: AbstractAccount) -> None:
        account._apply_withdrawal(self.amount, self.timestamp)


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, owner: Client) -> None:
        self._number = int(number)
        self._agency = str(agency)
        self._owner = owner
        self._balance: float = 0.0
        self._transactions: List[AbstractTransaction] = []

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
        return float(self._balance)

    @property
    def transactions(self) -> Sequence[AbstractTransaction]:
        return tuple(self._transactions)

    def deposit(self, amount: float) -> None:
        tx = Deposit(amount)
        self._execute_transaction(tx)

    def withdraw(self, amount: float) -> None:
        tx = Withdrawal(amount)
        self._execute_transaction(tx)

    def _execute_transaction(self, tx: AbstractTransaction) -> None:
        if tx.amount <= 0:
            raise InvalidAmountError("Amount must be positive.")
        tx.apply(self)
        self._transactions.append(tx)

    def _apply_deposit(self, amount: float) -> None:
        self._balance += amount

    def _apply_withdrawal(self, amount: float, ts: datetime) -> None:
        self._validate_withdrawal(amount, ts)
        self._balance -= amount

    @abstractmethod
    def _validate_withdrawal(self, amount: float, ts: datetime) -> None:
        raise NotImplementedError

    def _withdrawals_on_date(self, d: date) -> List[Withdrawal]:
        result: List[Withdrawal] = []
        for tx in self._transactions:
            if isinstance(tx, Withdrawal) and tx.timestamp.date() == d:
                result.append(tx)
        return result

    def statement(self) -> str:
        lines: List[str] = []
        lines.append(f"AGENCY: {self.agency}  ACCOUNT: {self.number}")
        lines.append(f"OWNER: {self.owner.name}  CPF: {self.owner.cpf}")
        lines.append(f"BALANCE: {self.balance:.2f}")
        lines.append("HISTORY:")
        if not self._transactions:
            lines.append("  (no transactions)")
        else:
            for tx in self._transactions:
                lines.append(f"  {tx.timestamp.isoformat(sep=' ', timespec='seconds')}  {tx.kind:<10}  {tx.amount:.2f}")
        return "\n".join(lines)


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        owner: Client,
        daily_withdrawal_limit: int = 3,
        per_withdrawal_limit: float = 500.0,
    ) -> None:
        super().__init__(number, agency, owner)
        self._daily_withdrawal_limit = int(daily_withdrawal_limit)
        self._per_withdrawal_limit = float(per_withdrawal_limit)

    @property
    def daily_withdrawal_limit(self) -> int:
        return self._daily_withdrawal_limit

    @property
    def per_withdrawal_limit(self) -> float:
        return self._per_withdrawal_limit

    def _validate_withdrawal(self, amount: float, ts: datetime) -> None:
        if amount > self._per_withdrawal_limit:
            raise WithdrawalLimitError("Per-withdrawal limit exceeded.")
        todays_withdrawals = self._withdrawals_on_date(ts.date())
        if len(todays_withdrawals) >= self._daily_withdrawal_limit:
            raise WithdrawalLimitError("Daily withdrawal limit exceeded.")
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")


class ContaPoupanca(AbstractAccount):
    def _validate_withdrawal(self, amount: float, ts: datetime) -> None:
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")


class Client(ABC):
    def __init__(self, name: str) -> None:
        self._name = str(name).strip()
        self._accounts: List[AbstractAccount] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def cpf(self) -> str:
        raise NotImplementedError

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def add_account(self, account: AbstractAccount) -> None:
        if account.owner is not self:
            raise BankingError("Account owner mismatch.")
        if any(a.agency == account.agency and a.number == account.number for a in self._accounts):
            raise BankingError("Account already added to client.")
        self._accounts.append(account)

    def get_account(self, agency: str, number: int) -> AbstractAccount:
        for acc in self._accounts:
            if acc.agency == agency and acc.number == number:
                return acc
        raise AccountNotFoundError("Account not found for client.")


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str) -> None:
        super().__init__(name)
        self._cpf = CPF.validate(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf


class Bank:
    def __init__(self, name: str) -> None:
        self._name = str(name).strip()
        self._clients_by_cpf: Dict[str, PessoaFisica] = {}
        self._accounts: List[AbstractAccount] = []
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def clients(self) -> Sequence[PessoaFisica]:
        return tuple(self._clients_by_cpf.values())

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def create_individual_client(self, name: str, cpf: str) -> PessoaFisica:
        normalized = CPF.validate(cpf)
        if normalized in self._clients_by_cpf:
            raise DuplicateCPFError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=normalized)
        self._clients_by_cpf[normalized] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> PessoaFisica:
        normalized = CPF.validate(cpf)
        client = self._clients_by_cpf.get(normalized)
        if client is None:
            raise ClientNotFoundError("Client not found.")
        return client

    def _allocate_account_number(self) -> int:
        n = self._next_account_number
        self._next_account_number += 1
        return n

    def open_checking_account(
        self,
        cpf: str,
        agency: str = "0001",
        daily_withdrawal_limit: int = 3,
        per_withdrawal_limit: float = 500.0,
    ) -> ContaCorrente:
        client = self.get_client_by_cpf(cpf)
        number = self._allocate_account_number()
        acc = ContaCorrente(
            number=number,
            agency=agency,
            owner=client,
            daily_withdrawal_limit=daily_withdrawal_limit,
            per_withdrawal_limit=per_withdrawal_limit,
        )
        client.add_account(acc)
        self._accounts.append(acc)
        return acc

    def open_savings_account(self, cpf: str, agency: str = "0001") -> ContaPoupanca:
        client = self.get_client_by_cpf(cpf)
        number = self._allocate_account_number()
        acc = ContaPoupanca(number=number, agency=agency, owner=client)
        client.add_account(acc)
        self._accounts.append(acc)
        return acc

    def find_account(self, agency: str, number: int) -> AbstractAccount:
        for acc in self._accounts:
            if acc.agency == agency and acc.number == number:
                return acc
        raise AccountNotFoundError("Account not found.")

    def deposit(self, agency: str, number: int, amount: float) -> None:
        acc = self.find_account(agency, number)
        acc.deposit(amount)

    def withdraw(self, agency: str, number: int, amount: float) -> None:
        acc = self.find_account(agency, number)
        acc.withdraw(amount)


class CommandLineInterface:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def run(self) -> None:
        menu = (
            "\n"
            "1 - Create individual client\n"
            "2 - Open checking account\n"
            "3 - Open savings account\n"
            "4 - Deposit\n"
            "5 - Withdraw\n"
            "6 - Statement\n"
            "0 - Exit\n"
        )
        while True:
            print(menu)
            choice = input("Select: ").strip()
            try:
                if choice == "1":
                    self._create_client()
                elif choice == "2":
                    self._open_checking()
                elif choice == "3":
                    self._open_savings()
                elif choice == "4":
                    self._deposit()
                elif choice == "5":
                    self._withdraw()
                elif choice == "6":
                    self._statement()
                elif choice == "0":
                    break
                else:
                    print("Invalid option.")
            except Exception as e:
                print(f"Error: {e}")

    def _create_client(self) -> None:
        name = input("Name: ").strip()
        cpf = input("CPF: ").strip()
        client = self._bank.create_individual_client(name, cpf)
        print(f"Client created: {client.name} (CPF {client.cpf})")

    def _open_checking(self) -> None:
        cpf = input("CPF: ").strip()
        agency = input("Agency [0001]: ").strip() or "0001"
        acc = self._bank.open_checking_account(cpf=cpf, agency=agency)
        print(f"Checking account opened: {acc.agency}/{acc.number}")

    def _open_savings(self) -> None:
        cpf = input("CPF: ").strip()
        agency = input("Agency [0001]: ").strip() or "0001"
        acc = self._bank.open_savings_account(cpf=cpf, agency=agency)
        print(f"Savings account opened: {acc.agency}/{acc.number}")

    def _deposit(self) -> None:
        agency = input("Agency: ").strip()
        number = int(input("Account number: ").strip())
        amount = float(input("Amount: ").strip())
        self._bank.deposit(agency, number, amount)
        print("Deposit completed.")

    def _withdraw(self) -> None:
        agency = input("Agency: ").strip()
        number = int(input("Account number: ").strip())
        amount = float(input("Amount: ").strip())
        self._bank.withdraw(agency, number, amount)
        print("Withdrawal completed.")

    def _statement(self) -> None:
        agency = input("Agency: ").strip()
        number = int(input("Account number: ").strip())
        acc = self._bank.find_account(agency, number)
        print(acc.statement())


def main() -> None:
    bank = Bank("Bank")
    cli = CommandLineInterface(bank)
    cli.run()


if __name__ == "__main__":
    main()