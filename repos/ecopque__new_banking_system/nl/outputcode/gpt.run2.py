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


class TransactionError(BankingError):
    pass


class InsufficientFundsError(TransactionError):
    pass


class WithdrawalLimitError(TransactionError):
    pass


class DailyWithdrawalLimitError(TransactionError):
    pass


class InvalidAmountError(TransactionError):
    pass


class DuplicateCPFError(BankingError):
    pass


class CPFValidator:
    @staticmethod
    def _only_digits(value: str) -> str:
        return "".join(ch for ch in value if ch.isdigit())

    @staticmethod
    def validate(cpf: str) -> str:
        if cpf is None:
            raise CPFValidationError("CPF is required.")
        digits = CPFValidator._only_digits(cpf)
        if len(digits) != 11:
            raise CPFValidationError("CPF must have 11 digits.")
        if digits == digits[0] * 11:
            raise CPFValidationError("Invalid CPF.")
        nums = [int(d) for d in digits]

        def calc_check(base: Sequence[int], factor_start: int) -> int:
            total = sum(n * f for n, f in zip(base, range(factor_start, 1, -1)))
            rem = (total * 10) % 11
            return 0 if rem == 10 else rem

        d1 = calc_check(nums[:9], 10)
        d2 = calc_check(nums[:10], 11)
        if d1 != nums[9] or d2 != nums[10]:
            raise CPFValidationError("Invalid CPF.")
        return digits


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
        self._number = number
        self._agency = agency
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

    def deposit(self, amount: float) -> TransactionRecord:
        tx = Deposit(amount)
        return self._execute(tx)

    def withdraw(self, amount: float) -> TransactionRecord:
        tx = Withdrawal(amount)
        return self._execute(tx)

    def _execute(self, transaction: AbstractTransaction) -> TransactionRecord:
        record = transaction.apply(self)
        self._transactions.append(record)
        return record

    def _validate_amount(self, amount: float) -> None:
        if not isinstance(amount, (int, float)):
            raise InvalidAmountError("Amount must be numeric.")
        if amount <= 0:
            raise InvalidAmountError("Amount must be greater than zero.")

    def _credit(self, amount: float) -> None:
        self._balance += amount

    def _debit(self, amount: float) -> None:
        self._balance -= amount

    @abstractmethod
    def _can_withdraw(self, amount: float, when: datetime) -> None:
        raise NotImplementedError


class Deposit(AbstractTransaction):
    def __init__(self, amount: float, timestamp: Optional[datetime] = None) -> None:
        self._amount = float(amount)
        self._timestamp = timestamp or datetime.now()

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
            account._validate_amount(self._amount)
            account._credit(self._amount)
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
    def __init__(self, amount: float, timestamp: Optional[datetime] = None) -> None:
        self._amount = float(amount)
        self._timestamp = timestamp or datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def transaction_type(self) -> str:
        return "WITHDRAWAL"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        try:
            account._validate_amount(self._amount)
            account._can_withdraw(self._amount, self._timestamp)
            if account.balance < self._amount:
                raise InsufficientFundsError("Insufficient funds.")
            account._debit(self._amount)
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
        if account not in self._accounts:
            self._accounts.append(account)

    def get_account(self, number: int) -> AbstractAccount:
        for acc in self._accounts:
            if acc.number == number:
                return acc
        raise AccountNotFoundError("Account not found for this client.")


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str) -> None:
        super().__init__(name=name)
        self._cpf = CPFValidator.validate(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        owner: Client,
        withdrawal_limit: float = 500.0,
        daily_withdrawal_count_limit: int = 3,
    ) -> None:
        super().__init__(number=number, agency=agency, owner=owner)
        self._withdrawal_limit = float(withdrawal_limit)
        self._daily_withdrawal_count_limit = int(daily_withdrawal_count_limit)

    @property
    def withdrawal_limit(self) -> float:
        return self._withdrawal_limit

    @property
    def daily_withdrawal_count_limit(self) -> int:
        return self._daily_withdrawal_count_limit

    def _withdrawals_today_count(self, when: datetime) -> int:
        d = when.date()
        return sum(
            1
            for r in self._transactions
            if r.success and r.transaction_type == "WITHDRAWAL" and r.timestamp.date() == d
        )

    def _can_withdraw(self, amount: float, when: datetime) -> None:
        if amount > self._withdrawal_limit:
            raise WithdrawalLimitError("Withdrawal amount exceeds per-transaction limit.")
        if self._withdrawals_today_count(when) >= self._daily_withdrawal_count_limit:
            raise DailyWithdrawalLimitError("Daily withdrawal count limit reached.")


class ContaPoupanca(AbstractAccount):
    def __init__(self, number: int, agency: str, owner: Client) -> None:
        super().__init__(number=number, agency=agency, owner=owner)

    def _can_withdraw(self, amount: float, when: datetime) -> None:
        return


class Bank:
    def __init__(self, name: str, agency: str = "0001") -> None:
        self._name = name.strip()
        self._agency = agency.strip()
        self._clients_by_cpf: Dict[str, PessoaFisica] = {}
        self._accounts_by_number: Dict[int, AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def agency(self) -> str:
        return self._agency

    def create_individual_client(self, name: str, cpf: str) -> PessoaFisica:
        normalized = CPFValidator.validate(cpf)
        if normalized in self._clients_by_cpf:
            raise DuplicateCPFError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=normalized)
        self._clients_by_cpf[normalized] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> PessoaFisica:
        normalized = CPFValidator.validate(cpf)
        client = self._clients_by_cpf.get(normalized)
        if not client:
            raise ClientNotFoundError("Client not found.")
        return client

    def create_account(self, cpf: str, account_type: Type[AbstractAccount]) -> AbstractAccount:
        client = self.get_client_by_cpf(cpf)
        number = self._next_account_number
        self._next_account_number += 1
        account = account_type(number=number, agency=self._agency, owner=client)
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
        return account.deposit(amount)

    def withdraw(self, account_number: int, amount: float) -> TransactionRecord:
        account = self.get_account(account_number)
        return account.withdraw(amount)

    def list_client_accounts(self, cpf: str) -> Sequence[AbstractAccount]:
        client = self.get_client_by_cpf(cpf)
        return client.accounts


class CommandLineInterface:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def run(self) -> None:
        while True:
            print("\n=== Banking System ===")
            print("1) Create individual client (PessoaFisica)")
            print("2) Create checking account (ContaCorrente)")
            print("3) Create savings account (ContaPoupanca)")
            print("4) Deposit")
            print("5) Withdraw")
            print("6) Account statement")
            print("7) List client accounts")
            print("0) Exit")
            choice = input("Select: ").strip()

            try:
                if choice == "1":
                    self._create_client()
                elif choice == "2":
                    self._create_account(ContaCorrente)
                elif choice == "3":
                    self._create_account(ContaPoupanca)
                elif choice == "4":
                    self._deposit()
                elif choice == "5":
                    self._withdraw()
                elif choice == "6":
                    self._statement()
                elif choice == "7":
                    self._list_accounts()
                elif choice == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Invalid option.")
            except Exception as e:
                print(f"Error: {e}")

    def _create_client(self) -> None:
        name = input("Name: ").strip()
        cpf = input("CPF: ").strip()
        client = self._bank.create_individual_client(name=name, cpf=cpf)
        print(f"Client created: {client.name} (CPF: {client.cpf})")

    def _create_account(self, account_type: Type[AbstractAccount]) -> None:
        cpf = input("CPF: ").strip()
        account = self._bank.create_account(cpf=cpf, account_type=account_type)
        print(f"Account created: {account.__class__.__name__} #{account.number} Agency {account.agency}")

    def _deposit(self) -> None:
        acc = int(input("Account number: ").strip())
        amount = float(input("Amount: ").strip())
        record = self._bank.deposit(account_number=acc, amount=amount)
        print(record.message)
        print(f"Balance: {record.balance_after:.2f}")

    def _withdraw(self) -> None:
        acc = int(input("Account number: ").strip())
        amount = float(input("Amount: ").strip())
        record = self._bank.withdraw(account_number=acc, amount=amount)
        print(record.message)
        print(f"Balance: {record.balance_after:.2f}")

    def _statement(self) -> None:
        acc = int(input("Account number: ").strip())
        account = self._bank.get_account(acc)
        print(f"\nStatement for account #{account.number} ({account.__class__.__name__})")
        if not account.history:
            print("No transactions.")
        else:
            for r in account.history:
                ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                status = "OK" if r.success else "FAIL"
                print(f"{ts} | {r.transaction_type:<10} | {r.amount:>10.2f} | {status} | {r.message}")
        print(f"Current balance: {account.balance:.2f}")

    def _list_accounts(self) -> None:
        cpf = input("CPF: ").strip()
        accounts = self._bank.list_client_accounts(cpf)
        if not accounts:
            print("No accounts.")
            return
        for a in accounts:
            print(f"{a.__class__.__name__} #{a.number} Agency {a.agency} Balance {a.balance:.2f}")


def main() -> None:
    bank = Bank(name="Bank", agency="0001")
    cli = CommandLineInterface(bank)
    cli.run()


if __name__ == "__main__":
    main()