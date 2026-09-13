from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Sequence, Type


class ValidationError(ValueError):
    pass


class BusinessRuleError(RuntimeError):
    pass


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def validate_cpf(cpf: str) -> str:
    cpf_digits = _only_digits(cpf)
    if len(cpf_digits) != 11:
        raise ValidationError("CPF must have 11 digits.")
    if cpf_digits == cpf_digits[0] * 11:
        raise ValidationError("Invalid CPF.")
    nums = [int(d) for d in cpf_digits]

    def calc_check(digs: Sequence[int], factor_start: int) -> int:
        total = 0
        factor = factor_start
        for n in digs:
            total += n * factor
            factor -= 1
        remainder = (total * 10) % 11
        return 0 if remainder == 10 else remainder

    d1 = calc_check(nums[:9], 10)
    d2 = calc_check(nums[:9] + [d1], 11)
    if d1 != nums[9] or d2 != nums[10]:
        raise ValidationError("Invalid CPF.")
    return cpf_digits


@dataclass(frozen=True)
class TransactionRecord:
    timestamp: datetime
    transaction_type: str
    amount: float
    success: bool
    message: str


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


class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive.")
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "DEPOSIT"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account._deposit_internal(self._amount)
            return TransactionRecord(ts, self.transaction_type, self._amount, True, "Deposit successful.")
        except Exception as e:
            return TransactionRecord(ts, self.transaction_type, self._amount, False, str(e))


class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive.")
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "WITHDRAWAL"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        ts = datetime.now()
        try:
            account.withdraw(self._amount)
            return TransactionRecord(ts, self.transaction_type, self._amount, True, "Withdrawal successful.")
        except Exception as e:
            return TransactionRecord(ts, self.transaction_type, self._amount, False, str(e))


class AbstractAccount(ABC):
    def __init__(self, number: int, agency: str, owner: Client) -> None:
        if number <= 0:
            raise ValidationError("Account number must be positive.")
        if not agency:
            raise ValidationError("Agency is required.")
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

    def perform(self, transaction: AbstractTransaction) -> TransactionRecord:
        record = transaction.apply(self)
        self._transactions.append(record)
        return record

    def _deposit_internal(self, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive.")
        self._balance += float(amount)

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(agency={self._agency!r}, number={self._number}, balance={self._balance:.2f})"


class ContaPoupanca(AbstractAccount):
    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive.")
        if amount > self._balance:
            raise BusinessRuleError("Insufficient funds.")
        self._balance -= float(amount)


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
        if daily_withdrawal_limit <= 0:
            raise ValidationError("Daily withdrawal limit must be positive.")
        if per_withdrawal_limit <= 0:
            raise ValidationError("Per-withdrawal limit must be positive.")
        self._daily_withdrawal_limit = int(daily_withdrawal_limit)
        self._per_withdrawal_limit = float(per_withdrawal_limit)

    @property
    def daily_withdrawal_limit(self) -> int:
        return self._daily_withdrawal_limit

    @property
    def per_withdrawal_limit(self) -> float:
        return self._per_withdrawal_limit

    def _withdrawals_today_count(self) -> int:
        today = date.today()
        return sum(
            1
            for r in self._transactions
            if r.success and r.transaction_type == "WITHDRAWAL" and r.timestamp.date() == today
        )

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Withdrawal amount must be positive.")
        if amount > self._per_withdrawal_limit:
            raise BusinessRuleError("Per-withdrawal limit exceeded.")
        if self._withdrawals_today_count() >= self._daily_withdrawal_limit:
            raise BusinessRuleError("Daily withdrawal limit exceeded.")
        if amount > self._balance:
            raise BusinessRuleError("Insufficient funds.")
        self._balance -= float(amount)


class Client(ABC):
    def __init__(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Client name is required.")
        self._name = name.strip()
        self._accounts: List[AbstractAccount] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts)

    def add_account(self, account: AbstractAccount) -> None:
        if account.owner is not self:
            raise ValidationError("Account owner mismatch.")
        if any(a.agency == account.agency and a.number == account.number for a in self._accounts):
            raise ValidationError("Duplicate account for this client.")
        self._accounts.append(account)

    def get_account(self, agency: str, number: int) -> Optional[AbstractAccount]:
        for a in self._accounts:
            if a.agency == agency and a.number == number:
                return a
        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r})"


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str) -> None:
        super().__init__(name)
        self._cpf = validate_cpf(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r}, cpf={self._cpf!r})"


class Bank:
    def __init__(self, name: str, default_agency: str = "0001") -> None:
        if not name or not name.strip():
            raise ValidationError("Bank name is required.")
        if not default_agency:
            raise ValidationError("Default agency is required.")
        self._name = name.strip()
        self._default_agency = str(default_agency)
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
        cpf_digits = validate_cpf(cpf)
        if cpf_digits in self._clients_by_cpf:
            raise ValidationError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=cpf_digits)
        self._clients_by_cpf[cpf_digits] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> Optional[PessoaFisica]:
        try:
            cpf_digits = validate_cpf(cpf)
        except ValidationError:
            return None
        return self._clients_by_cpf.get(cpf_digits)

    def _allocate_account_number(self) -> int:
        n = self._next_account_number
        self._next_account_number += 1
        return n

    def create_account(
        self,
        client_cpf: str,
        account_type: Type[AbstractAccount],
        agency: Optional[str] = None,
        **kwargs,
    ) -> AbstractAccount:
        client = self.get_client_by_cpf(client_cpf)
        if client is None:
            raise ValidationError("Client not found for CPF.")
        ag = self._default_agency if agency is None else str(agency)
        number = self._allocate_account_number()
        key = (ag, number)
        if key in self._accounts_by_key:
            raise ValidationError("Account already exists.")
        account = account_type(number=number, agency=ag, owner=client, **kwargs)
        client.add_account(account)
        self._accounts_by_key[key] = account
        return account

    def get_account(self, agency: str, number: int) -> Optional[AbstractAccount]:
        return self._accounts_by_key.get((str(agency), int(number)))

    def list_clients(self) -> Sequence[PessoaFisica]:
        return tuple(self._clients_by_cpf.values())

    def list_accounts(self) -> Sequence[AbstractAccount]:
        return tuple(self._accounts_by_key.values())


class CLI:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def run(self) -> None:
        menu = (
            "\n"
            "1 - Create individual client\n"
            "2 - Create checking account\n"
            "3 - Create savings account\n"
            "4 - Deposit\n"
            "5 - Withdraw\n"
            "6 - Account statement\n"
            "7 - List clients\n"
            "8 - List accounts\n"
            "0 - Exit\n"
        )
        while True:
            print(menu)
            choice = input("Select an option: ").strip()
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
                    print("Goodbye.")
                    return
                else:
                    print("Invalid option.")
            except (ValidationError, BusinessRuleError) as e:
                print(f"Error: {e}")

    def _create_client(self) -> None:
        name = input("Name: ").strip()
        cpf = input("CPF: ").strip()
        client = self._bank.create_individual_client(name=name, cpf=cpf)
        print(f"Client created: {client.name} (CPF: {client.cpf})")

    def _create_account(self, account_cls: Type[AbstractAccount]) -> None:
        cpf = input("Client CPF: ").strip()
        if account_cls is ContaCorrente:
            account = self._bank.create_account(cpf, ContaCorrente)
        else:
            account = self._bank.create_account(cpf, ContaPoupanca)
        print(f"Account created: {account}")

    def _get_account_from_input(self) -> AbstractAccount:
        agency = input(f"Agency (default {self._bank.default_agency}): ").strip() or self._bank.default_agency
        number_str = input("Account number: ").strip()
        if not number_str.isdigit():
            raise ValidationError("Account number must be numeric.")
        number = int(number_str)
        account = self._bank.get_account(agency, number)
        if account is None:
            raise ValidationError("Account not found.")
        return account

    def _deposit(self) -> None:
        account = self._get_account_from_input()
        amount_str = input("Amount: ").strip()
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValidationError("Invalid amount.")
        record = account.perform(Deposit(amount))
        print(record.message)

    def _withdraw(self) -> None:
        account = self._get_account_from_input()
        amount_str = input("Amount: ").strip()
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValidationError("Invalid amount.")
        record = account.perform(Withdrawal(amount))
        print(record.message)

    def _statement(self) -> None:
        account = self._get_account_from_input()
        print(f"\nStatement for {account}")
        if not account.history:
            print("No transactions.")
        else:
            for r in account.history:
                ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                status = "OK" if r.success else "FAIL"
                print(f"{ts} | {r.transaction_type:<10} | {r.amount:>10.2f} | {status} | {r.message}")
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
            owner = a.owner.name
            print(f"{a.__class__.__name__} | {a.agency}-{a.number} | Owner: {owner} | Balance: {a.balance:.2f}")


def main() -> None:
    bank = Bank(name="Bank", default_agency="0001")
    CLI(bank).run()


if __name__ == "__main__":
    main()