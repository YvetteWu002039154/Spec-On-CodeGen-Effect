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


class ValidationError(TransactionError):
    pass


class CPF:
    @staticmethod
    def normalize(value: str) -> str:
        if value is None:
            raise CPFValidationError("CPF is required.")
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return digits

    @staticmethod
    def is_valid(value: str) -> bool:
        cpf = CPF.normalize(value)
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
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: AbstractAccount) -> TransactionRecord:
        raise NotImplementedError


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, client: Client) -> None:
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
    def client(self) -> Client:
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> Sequence[TransactionRecord]:
        return tuple(self._history)

    def _add_record(self, record: TransactionRecord) -> None:
        self._history.append(record)

    def deposit(self, amount: float) -> None:
        if amount is None or amount <= 0:
            raise ValidationError("Deposit amount must be positive.")
        self._balance += float(amount)

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def perform(self, transaction: AbstractTransaction) -> TransactionRecord:
        record = transaction.apply(self)
        self._add_record(record)
        return record

    def _count_withdrawals_on(self, day: date) -> int:
        count = 0
        for r in self._history:
            if r.success and r.transaction_type.lower() == "withdraw" and r.timestamp.date() == day:
                count += 1
        return count

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agency={self.agency!r}, number={self.number!r}, balance={self.balance:.2f})"


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        number: int,
        agency: str,
        client: Client,
        withdrawal_limit_per_transaction: float = 500.0,
        daily_withdrawal_limit_count: int = 3,
    ) -> None:
        super().__init__(number=number, agency=agency, client=client)
        self._withdrawal_limit_per_transaction = float(withdrawal_limit_per_transaction)
        self._daily_withdrawal_limit_count = int(daily_withdrawal_limit_count)

    @property
    def withdrawal_limit_per_transaction(self) -> float:
        return self._withdrawal_limit_per_transaction

    @property
    def daily_withdrawal_limit_count(self) -> int:
        return self._daily_withdrawal_limit_count

    def withdraw(self, amount: float) -> None:
        if amount is None or amount <= 0:
            raise ValidationError("Withdrawal amount must be positive.")
        amount = float(amount)

        if amount > self._withdrawal_limit_per_transaction:
            raise WithdrawalLimitError("Withdrawal exceeds per-transaction limit.")

        today = datetime.now().date()
        if self._count_withdrawals_on(today) >= self._daily_withdrawal_limit_count:
            raise WithdrawalLimitError("Daily withdrawal count limit reached.")

        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")

        self._balance -= amount


class ContaPoupanca(AbstractAccount):
    def withdraw(self, amount: float) -> None:
        if amount is None or amount <= 0:
            raise ValidationError("Withdrawal amount must be positive.")
        amount = float(amount)
        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds.")
        self._balance -= amount


class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def name(self) -> str:
        return "Deposit"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.deposit(self._amount)
            return TransactionRecord(
                timestamp=ts,
                transaction_type="deposit",
                amount=self._amount,
                success=True,
                message="Deposit successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=ts,
                transaction_type="deposit",
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
    def name(self) -> str:
        return "Withdraw"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.withdraw(self._amount)
            return TransactionRecord(
                timestamp=ts,
                transaction_type="withdraw",
                amount=self._amount,
                success=True,
                message="Withdrawal successful.",
                balance_after=account.balance,
            )
        except Exception as e:
            return TransactionRecord(
                timestamp=ts,
                transaction_type="withdraw",
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
        if account.client is not self:
            raise ValidationError("Account client mismatch.")
        if any(a.agency == account.agency and a.number == account.number for a in self._accounts):
            raise ValidationError("Client already has an account with same agency and number.")
        self._accounts.append(account)

    def get_account(self, agency: str, number: int) -> AbstractAccount:
        for a in self._accounts:
            if a.agency == agency and a.number == number:
                return a
        raise AccountNotFoundError("Account not found for this client.")

    def perform_transaction(self, account: AbstractAccount, transaction: AbstractTransaction) -> TransactionRecord:
        if account not in self._accounts:
            raise AccountNotFoundError("Account does not belong to this client.")
        return account.perform(transaction)


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str, birth_date: str, address: str) -> None:
        super().__init__(address=address)
        self._name = str(name)
        self._cpf = CPF.validate(cpf)
        self._birth_date = str(birth_date)

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def birth_date(self) -> str:
        return self._birth_date

    def __repr__(self) -> str:
        return f"PessoaFisica(name={self.name!r}, cpf={self.cpf!r})"


class Bank:
    def __init__(self, name: str, default_agency: str = "0001") -> None:
        self._name = str(name)
        self._default_agency = str(default_agency)
        self._clients_by_cpf: Dict[str, PessoaFisica] = {}
        self._accounts: Dict[tuple[str, int], AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_agency(self) -> str:
        return self._default_agency

    def create_individual_client(self, name: str, cpf: str, birth_date: str, address: str) -> PessoaFisica:
        normalized = CPF.validate(cpf)
        if normalized in self._clients_by_cpf:
            raise ValidationError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=normalized, birth_date=birth_date, address=address)
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

    def create_account_for_client(
        self,
        cpf: str,
        account_type: Type[AbstractAccount],
        agency: Optional[str] = None,
        **kwargs,
    ) -> AbstractAccount:
        client = self.get_client_by_cpf(cpf)
        agency_value = self._default_agency if agency is None else str(agency)
        number = self._allocate_account_number()

        account = account_type(number=number, agency=agency_value, client=client, **kwargs)
        key = (account.agency, account.number)
        if key in self._accounts:
            raise ValidationError("Account already exists.")
        self._accounts[key] = account
        client.add_account(account)
        return account

    def find_account(self, agency: str, number: int) -> AbstractAccount:
        key = (str(agency), int(number))
        account = self._accounts.get(key)
        if account is None:
            raise AccountNotFoundError("Account not found.")
        return account

    def list_clients(self) -> Sequence[PessoaFisica]:
        return tuple(self._clients_by_cpf.values())

    def list_accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts.values())


class CLI:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def run(self) -> None:
        menu = (
            "\n"
            "[1] Create individual client\n"
            "[2] Create checking account\n"
            "[3] Create savings account\n"
            "[4] Deposit\n"
            "[5] Withdraw\n"
            "[6] Statement\n"
            "[7] List clients\n"
            "[8] List accounts\n"
            "[0] Exit\n"
        )
        while True:
            print(menu)
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
                    self._list_clients()
                elif choice == "8":
                    self._list_accounts()
                elif choice == "0":
                    return
                else:
                    print("Invalid option.")
            except Exception as e:
                print(f"Error: {e}")

    def _prompt_cpf(self) -> str:
        return input("CPF: ").strip()

    def _prompt_account_ref(self) -> tuple[str, int]:
        agency = input(f"Agency (default {self._bank.default_agency}): ").strip() or self._bank.default_agency
        number_str = input("Account number: ").strip()
        if not number_str.isdigit():
            raise ValidationError("Account number must be numeric.")
        return agency, int(number_str)

    def _create_client(self) -> None:
        name = input("Name: ").strip()
        cpf = self._prompt_cpf()
        birth_date = input("Birth date (YYYY-MM-DD): ").strip()
        address = input("Address: ").strip()
        client = self._bank.create_individual_client(name=name, cpf=cpf, birth_date=birth_date, address=address)
        print(f"Client created: {client.name} (CPF {client.cpf})")

    def _create_account(self, account_type: Type[AbstractAccount]) -> None:
        cpf = self._prompt_cpf()
        account = self._bank.create_account_for_client(cpf=cpf, account_type=account_type)
        print(f"Account created: {account}")

    def _deposit(self) -> None:
        agency, number = self._prompt_account_ref()
        amount = float(input("Amount: ").strip())
        account = self._bank.find_account(agency, number)
        record = account.perform(Deposit(amount))
        print(record.message)
        print(f"Balance: {record.balance_after:.2f}")

    def _withdraw(self) -> None:
        agency, number = self._prompt_account_ref()
        amount = float(input("Amount: ").strip())
        account = self._bank.find_account(agency, number)
        record = account.perform(Withdraw(amount))
        print(record.message)
        print(f"Balance: {record.balance_after:.2f}")

    def _statement(self) -> None:
        agency, number = self._prompt_account_ref()
        account = self._bank.find_account(agency, number)
        print(f"\nStatement for {account}")
        if not account.history:
            print("No transactions.")
            print(f"Current balance: {account.balance:.2f}")
            return
        for r in account.history:
            ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            status = "OK" if r.success else "FAIL"
            print(f"{ts} | {r.transaction_type.upper():8} | {r.amount:10.2f} | {status:4} | {r.message}")
        print(f"Current balance: {account.balance:.2f}")

    def _list_clients(self) -> None:
        clients = self._bank.list_clients()
        if not clients:
            print("No clients.")
            return
        for c in clients:
            print(f"{c.name} | CPF: {c.cpf} | Accounts: {len(c.accounts)}")

    def _list_accounts(self) -> None:
        accounts = self._bank.list_accounts()
        if not accounts:
            print("No accounts.")
            return
        for a in accounts:
            print(f"{a.__class__.__name__} | Agency: {a.agency} | Number: {a.number} | Client: {getattr(a.client, 'cpf', '')} | Balance: {a.balance:.2f}")


def main() -> None:
    bank = Bank(name="Bank", default_agency="0001")
    CLI(bank).run()


if __name__ == "__main__":
    main()