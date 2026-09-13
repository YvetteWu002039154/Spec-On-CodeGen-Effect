from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Sequence, Dict


class CPFValidationError(ValueError):
    pass


class AccountNotFoundError(LookupError):
    pass


class InsufficientFundsError(ValueError):
    pass


class TransactionLimitError(ValueError):
    pass


class InvalidAmountError(ValueError):
    pass


class ClientAlreadyExistsError(ValueError):
    pass


class ClientNotFoundError(LookupError):
    pass


def _only_digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def validate_cpf(cpf: str) -> str:
    cpf_digits = _only_digits(cpf or "")
    if len(cpf_digits) != 11:
        raise CPFValidationError("CPF must have 11 digits.")
    if cpf_digits == cpf_digits[0] * 11:
        raise CPFValidationError("Invalid CPF.")
    nums = [int(d) for d in cpf_digits]

    def calc_digit(base: Sequence[int], factor_start: int) -> int:
        total = sum(n * f for n, f in zip(base, range(factor_start, 1, -1)))
        rem = (total * 10) % 11
        return 0 if rem == 10 else rem

    d1 = calc_digit(nums[:9], 10)
    d2 = calc_digit(nums[:10], 11)
    if d1 != nums[9] or d2 != nums[10]:
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
    def transaction_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, account: AbstractAccount) -> TransactionRecord:
        raise NotImplementedError


class AbstractAccount(ABC):
    def __init__(self, agency: str, number: int, client: Client) -> None:
        self._agency = agency
        self._number = number
        self._client = client
        self._balance: float = 0.0
        self._history: List[TransactionRecord] = []

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def number(self) -> int:
        return self._number

    @property
    def client(self) -> Client:
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> Sequence[TransactionRecord]:
        return tuple(self._history)

    def deposit(self, amount: float) -> None:
        record = Deposit(amount).apply(self)
        self._history.append(record)

    def withdraw(self, amount: float) -> None:
        record = Withdrawal(amount).apply(self)
        self._history.append(record)

    def perform(self, transaction: AbstractTransaction) -> None:
        record = transaction.apply(self)
        self._history.append(record)

    def _record(self, transaction_type: str, amount: float, success: bool, message: str) -> TransactionRecord:
        return TransactionRecord(
            timestamp=datetime.now(),
            transaction_type=transaction_type,
            amount=amount,
            success=success,
            message=message,
            balance_after=self._balance,
        )

    def _validate_amount_positive(self, amount: float) -> None:
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise InvalidAmountError("Amount must be positive.")

    def _credit(self, amount: float) -> None:
        self._balance += float(amount)

    def _debit(self, amount: float) -> None:
        if self._balance < amount:
            raise InsufficientFundsError("Insufficient funds.")
        self._balance -= float(amount)

    @abstractmethod
    def _can_withdraw(self, amount: float) -> None:
        raise NotImplementedError

    def _withdraw_impl(self, amount: float) -> None:
        self._validate_amount_positive(amount)
        self._can_withdraw(amount)
        self._debit(amount)

    def _deposit_impl(self, amount: float) -> None:
        self._validate_amount_positive(amount)
        self._credit(amount)


class ContaPoupanca(AbstractAccount):
    def _can_withdraw(self, amount: float) -> None:
        return


class ContaCorrente(AbstractAccount):
    def __init__(
        self,
        agency: str,
        number: int,
        client: Client,
        withdrawal_limit: float = 500.0,
        daily_withdrawal_count_limit: int = 3,
    ) -> None:
        super().__init__(agency, number, client)
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
        return sum(
            1
            for r in self._history
            if r.success and r.transaction_type == "WITHDRAWAL" and r.timestamp.date() == today
        )

    def _can_withdraw(self, amount: float) -> None:
        if amount > self._withdrawal_limit:
            raise TransactionLimitError("Withdrawal amount exceeds per-transaction limit.")
        if self._withdrawals_today_count() >= self._daily_withdrawal_count_limit:
            raise TransactionLimitError("Daily withdrawal count limit reached.")


class Client(ABC):
    def __init__(self, address: str) -> None:
        self._address = address
        self._accounts: List[AbstractAccount] = []

    @property
    def address(self) -> str:
        return self._address

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
        raise AccountNotFoundError("Account not found.")


class PessoaFisica(Client):
    def __init__(self, name: str, cpf: str, birth_date: str, address: str) -> None:
        super().__init__(address=address)
        self._name = name
        self._cpf = validate_cpf(cpf)
        self._birth_date = birth_date

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def birth_date(self) -> str:
        return self._birth_date


class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "DEPOSIT"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        try:
            account._deposit_impl(self._amount)
            return account._record(self.transaction_type, self._amount, True, "Deposit successful.")
        except Exception as e:
            return account._record(self.transaction_type, self._amount, False, str(e))


class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = float(amount)

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> str:
        return "WITHDRAWAL"

    def apply(self, account: AbstractAccount) -> TransactionRecord:
        try:
            account._withdraw_impl(self._amount)
            return account._record(self.transaction_type, self._amount, True, "Withdrawal successful.")
        except Exception as e:
            return account._record(self.transaction_type, self._amount, False, str(e))


class Bank:
    def __init__(self, name: str, default_agency: str = "0001") -> None:
        self._name = name
        self._default_agency = default_agency
        self._clients_by_cpf: Dict[str, PessoaFisica] = {}
        self._accounts_by_number: Dict[int, AbstractAccount] = {}
        self._next_account_number: int = 1

    @property
    def name(self) -> str:
        return self._name

    @property
    def default_agency(self) -> str:
        return self._default_agency

    def create_individual_client(self, name: str, cpf: str, birth_date: str, address: str) -> PessoaFisica:
        cpf_norm = validate_cpf(cpf)
        if cpf_norm in self._clients_by_cpf:
            raise ClientAlreadyExistsError("Client with this CPF already exists.")
        client = PessoaFisica(name=name, cpf=cpf_norm, birth_date=birth_date, address=address)
        self._clients_by_cpf[cpf_norm] = client
        return client

    def get_client_by_cpf(self, cpf: str) -> PessoaFisica:
        cpf_norm = validate_cpf(cpf)
        client = self._clients_by_cpf.get(cpf_norm)
        if not client:
            raise ClientNotFoundError("Client not found.")
        return client

    def open_checking_account(
        self,
        cpf: str,
        withdrawal_limit: float = 500.0,
        daily_withdrawal_count_limit: int = 3,
        agency: Optional[str] = None,
    ) -> ContaCorrente:
        client = self.get_client_by_cpf(cpf)
        number = self._next_account_number
        self._next_account_number += 1
        acc = ContaCorrente(
            agency=agency or self._default_agency,
            number=number,
            client=client,
            withdrawal_limit=withdrawal_limit,
            daily_withdrawal_count_limit=daily_withdrawal_count_limit,
        )
        client.add_account(acc)
        self._accounts_by_number[number] = acc
        return acc

    def open_savings_account(self, cpf: str, agency: Optional[str] = None) -> ContaPoupanca:
        client = self.get_client_by_cpf(cpf)
        number = self._next_account_number
        self._next_account_number += 1
        acc = ContaPoupanca(agency=agency or self._default_agency, number=number, client=client)
        client.add_account(acc)
        self._accounts_by_number[number] = acc
        return acc

    def get_account(self, number: int) -> AbstractAccount:
        acc = self._accounts_by_number.get(int(number))
        if not acc:
            raise AccountNotFoundError("Account not found.")
        return acc

    def deposit(self, account_number: int, amount: float) -> TransactionRecord:
        acc = self.get_account(account_number)
        record = Deposit(amount).apply(acc)
        acc._history.append(record)
        return record

    def withdraw(self, account_number: int, amount: float) -> TransactionRecord:
        acc = self.get_account(account_number)
        record = Withdrawal(amount).apply(acc)
        acc._history.append(record)
        return record


class CLI:
    def __init__(self, bank: Bank) -> None:
        self._bank = bank

    def run(self) -> None:
        menu = (
            "\n=== BANK MENU ===\n"
            "[1] Create individual client\n"
            "[2] Open checking account\n"
            "[3] Open savings account\n"
            "[4] Deposit\n"
            "[5] Withdraw\n"
            "[6] Statement\n"
            "[0] Exit\n"
            "Choose: "
        )
        while True:
            try:
                choice = input(menu).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting.")
                return

            if choice == "0":
                print("Exiting.")
                return
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
            else:
                print("Invalid option.")

    def _create_client(self) -> None:
        try:
            name = input("Name: ").strip()
            cpf = input("CPF: ").strip()
            birth_date = input("Birth date: ").strip()
            address = input("Address: ").strip()
            client = self._bank.create_individual_client(name=name, cpf=cpf, birth_date=birth_date, address=address)
            print(f"Client created: {client.name} (CPF {client.cpf})")
        except Exception as e:
            print(f"Error: {e}")

    def _open_checking(self) -> None:
        try:
            cpf = input("CPF: ").strip()
            acc = self._bank.open_checking_account(cpf=cpf)
            print(f"Checking account opened: agency {acc.agency}, number {acc.number}")
        except Exception as e:
            print(f"Error: {e}")

    def _open_savings(self) -> None:
        try:
            cpf = input("CPF: ").strip()
            acc = self._bank.open_savings_account(cpf=cpf)
            print(f"Savings account opened: agency {acc.agency}, number {acc.number}")
        except Exception as e:
            print(f"Error: {e}")

    def _deposit(self) -> None:
        try:
            number = int(input("Account number: ").strip())
            amount = float(input("Amount: ").strip())
            record = self._bank.deposit(account_number=number, amount=amount)
            print(record.message)
            print(f"Balance: {record.balance_after:.2f}")
        except Exception as e:
            print(f"Error: {e}")

    def _withdraw(self) -> None:
        try:
            number = int(input("Account number: ").strip())
            amount = float(input("Amount: ").strip())
            record = self._bank.withdraw(account_number=number, amount=amount)
            print(record.message)
            print(f"Balance: {record.balance_after:.2f}")
        except Exception as e:
            print(f"Error: {e}")

    def _statement(self) -> None:
        try:
            number = int(input("Account number: ").strip())
            acc = self._bank.get_account(number)
            print(f"\n=== STATEMENT ===\nAgency: {acc.agency}\nAccount: {acc.number}\nBalance: {acc.balance:.2f}\n")
            if not acc.history:
                print("No transactions.")
                return
            for r in acc.history:
                ts = r.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                status = "OK" if r.success else "FAIL"
                print(f"{ts} | {r.transaction_type:<10} | {r.amount:>10.2f} | {status:<4} | {r.message}")
        except Exception as e:
            print(f"Error: {e}")


def main() -> None:
    bank = Bank(name="Bank")
    CLI(bank).run()


if __name__ == "__main__":
    main()