from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Union
import re

# ---------- Custom Exceptions ----------
class BankException(Exception):
    """Base exception for banking operations."""
    pass

class InsufficientFundsError(BankException):
    pass

class DailyLimitExceededError(BankException):
    pass

class AccountNotFoundError(BankException):
    pass

class InvalidCPFError(BankException):
    pass

# ---------- Utility: CPF Validation ----------
def validate_cpf(cpf: str) -> bool:
    """Validates a Brazilian CPF number (11 digits)."""
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    # Calculate first check digit
    sum_ = sum(int(cpf[i]) * (10 - i) for i in range(9))
    first_digit = (sum_ * 10) % 11
    if first_digit == 10:
        first_digit = 0
    if int(cpf[9]) != first_digit:
        return False
    # Calculate second check digit
    sum_ = sum(int(cpf[i]) * (11 - i) for i in range(10))
    second_digit = (sum_ * 10) % 11
    if second_digit == 10:
        second_digit = 0
    return int(cpf[10]) == second_digit

# ---------- Enums ----------
from enum import Enum

class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"

# ---------- Abstract Transaction ----------
class AbstractTransaction(ABC):
    def __init__(self, amount: float, transaction_type: TransactionType, timestamp: Optional[datetime] = None):
        self._amount = amount
        self._transaction_type = transaction_type
        self._timestamp = timestamp or datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @abstractmethod
    def __str__(self) -> str:
        pass

class Transaction(AbstractTransaction):
    """Concrete transaction recording."""
    def __init__(self, amount: float, transaction_type: TransactionType, timestamp: Optional[datetime] = None):
        super().__init__(amount, transaction_type, timestamp)

    def __str__(self) -> str:
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.transaction_type.value}: R${self.amount:.2f}"

# ---------- Abstract Account ----------
class AbstractAccount(ABC):
    def __init__(self, agency: str, account_number: str, owner: 'Client'):
        self._agency = agency
        self._account_number = account_number
        self._owner = owner
        self._balance: float = 0.0
        self._transactions: List[Transaction] = []
        self._daily_withdrawal_amount: float = 0.0
        self._last_withdrawal_date: Optional[date] = None

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def owner(self) -> 'Client':
        return self._owner

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def transactions(self) -> List[Transaction]:
        return self._transactions.copy()

    def _reset_daily_limit_if_new_day(self) -> None:
        today = date.today()
        if self._last_withdrawal_date != today:
            self._daily_withdrawal_amount = 0.0
            self._last_withdrawal_date = today

    def _add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append(transaction)

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self._balance += amount
        self._add_transaction(Transaction(amount, TransactionType.DEPOSIT))

    def get_statement(self) -> List[str]:
        return [str(t) for t in self._transactions]

    def __str__(self) -> str:
        return f"Account {self._account_number} - Agency: {self._agency} | Balance: R${self._balance:.2f}"

# ---------- Concrete Accounts ----------
class CurrentAccount(AbstractAccount):
    """Checking account with overdraft facility."""
    OVERDRAFT_LIMIT = 500.0
    DAILY_WITHDRAWAL_LIMIT = 2000.0

    def __init__(self, agency: str, account_number: str, owner: 'Client', overdraft_limit: Optional[float] = None):
        super().__init__(agency, account_number, owner)
        self._overdraft_limit = overdraft_limit or self.OVERDRAFT_LIMIT

    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        self._reset_daily_limit_if_new_day()
        if self._daily_withdrawal_amount + amount > self.DAILY_WITHDRAWAL_LIMIT:
            raise DailyLimitExceededError(f"Daily withdrawal limit exceeded. Limit: R${self.DAILY_WITHDRAWAL_LIMIT:.2f}, already withdrawn: R${self._daily_withdrawal_amount:.2f}.")
        if self._balance + self._overdraft_limit < amount:
            raise InsufficientFundsError(f"Insufficient funds (including overdraft). Balance: R${self._balance:.2f}, overdraft: R${self._overdraft_limit:.2f}.")
        self._balance -= amount
        self._daily_withdrawal_amount += amount
        self._add_transaction(Transaction(amount, TransactionType.WITHDRAWAL))
        return True

    def __str__(self) -> str:
        return f"[Current] {super().__str__()} Overdraft: R${self._overdraft_limit:.2f}"


class SavingsAccount(AbstractAccount):
    """Savings account with minimum balance requirement and no overdraft."""
    MINIMUM_BALANCE = 0.0
    DAILY_WITHDRAWAL_LIMIT = 1000.0
    INTEREST_RATE = 0.005  # 0.5% per month (simplified)

    def __init__(self, agency: str, account_number: str, owner: 'Client', interest_rate: Optional[float] = None):
        super().__init__(agency, account_number, owner)
        self._interest_rate = interest_rate or self.INTEREST_RATE

    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        self._reset_daily_limit_if_new_day()
        if self._daily_withdrawal_amount + amount > self.DAILY_WITHDRAWAL_LIMIT:
            raise DailyLimitExceededError(f"Daily withdrawal limit exceeded. Limit: R${self.DAILY_WITHDRAWAL_LIMIT:.2f}, already withdrawn: R${self._daily_withdrawal_amount:.2f}.")
        if self._balance - amount < self.MINIMUM_BALANCE:
            raise InsufficientFundsError(f"Insufficient funds. Minimum balance required: R${self.MINIMUM_BALANCE:.2f}. Current: R${self._balance:.2f}.")
        self._balance -= amount
        self._daily_withdrawal_amount += amount
        self._add_transaction(Transaction(amount, TransactionType.WITHDRAWAL))
        return True

    def apply_interest(self) -> None:
        """Apply monthly interest to the balance."""
        interest = self._balance * self._interest_rate
        self._balance += interest
        self._add_transaction(Transaction(interest, TransactionType.DEPOSIT))  # Treat as deposit

    def __str__(self) -> str:
        return f"[Savings] {super().__str__()} Interest rate: {self._interest_rate*100:.2f}%"


# ---------- Client ----------
class Client(ABC):
    def __init__(self, name: str, address: str):
        self._name = name
        self._address = address
        self._accounts: List[AbstractAccount] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    def add_account(self, account: AbstractAccount) -> None:
        self._accounts.append(account)

    def list_accounts(self) -> List[AbstractAccount]:
        return self._accounts.copy()

    @abstractmethod
    def get_identifier(self) -> str:
        pass

    def __str__(self) -> str:
        return f"Client: {self._name} ({self.get_identifier()})"


class Individual(Client):
    """PessoaFisica - CPF based client."""
    def __init__(self, name: str, cpf: str, address: str = ""):
        super().__init__(name, address)
        self._cpf = cpf
        if not validate_cpf(cpf):
            raise InvalidCPFError(f"Invalid CPF: {cpf}")

    @property
    def cpf(self) -> str:
        return self._cpf

    def get_identifier(self) -> str:
        return f"CPF: {self._cpf}"

    def __str__(self) -> str:
        return f"Person: {self._name} ({self._cpf})"


# ---------- Bank (Facade) ----------
class Bank:
    """Simple bank service to coordinate clients and accounts."""
    def __init__(self, name: str):
        self._name = name
        self._clients: List[Client] = []
        self._accounts: List[AbstractAccount] = []

    def add_client(self, client: Client) -> None:
        if client not in self._clients:
            self._clients.append(client)

    def open_account(self, client: Client, account_type: str, **kwargs) -> AbstractAccount:
        if client not in self._clients:
            self.add_client(client)
        agency = kwargs.get('agency', '0001')
        # generate simple account number (increment)
        account_number = str(len(self._accounts) + 1).zfill(5)
        if account_type.lower() == 'current':
            account = CurrentAccount(agency, account_number, client, kwargs.get('overdraft_limit'))
        elif account_type.lower() == 'savings':
            account = SavingsAccount(agency, account_number, client, kwargs.get('interest_rate'))
        else:
            raise ValueError("Invalid account type.")
        client.add_account(account)
        self._accounts.append(account)
        print(f"Account {account_number} ({account_type}) opened for {client.name}.")
        return account

    def find_account(self, account_number: str) -> AbstractAccount:
        for acc in self._accounts:
            if acc.account_number == account_number:
                return acc
        raise AccountNotFoundError(f"Account {account_number} not found.")

    def deposit(self, account_number: str, amount: float) -> None:
        acc = self.find_account(account_number)
        acc.deposit(amount)
        print(f"Deposit of R${amount:.2f} to account {account_number}. New balance: R${acc.balance:.2f}")

    def withdraw(self, account_number: str, amount: float) -> None:
        acc = self.find_account(account_number)
        try:
            acc.withdraw(amount)
            print(f"Withdrawal of R${amount:.2f} from account {account_number}. New balance: R${acc.balance:.2f}")
        except (InsufficientFundsError, DailyLimitExceededError) as e:
            print(f"Withdrawal failed: {e}")

    def print_statement(self, account_number: str) -> None:
        acc = self.find_account(account_number)
        print(f"Statement for account {account_number} (Owner: {acc.owner.name})")
        print("="*40)
        for line in acc.get_statement():
            print(line)
        print(f"Current balance: R${acc.balance:.2f}")
        print("="*40)


# ---------- Demo / CLI ----------
def main():
    bank = Bank("Python Bank")
    print("Welcome to Python Bank System")
    # sample CLI loop for demonstration
    while True:
        print("\nOptions:")
        print("1. Add client (Individual)")
        print("2. Open account")
        print("3. Deposit")
        print("4. Withdraw")
        print("5. Account statement")
        print("6. List all clients and accounts")
        print("7. Apply interest (savings)")  # simplified interest application
        print("0. Exit")
        choice = input("Choose: ").strip()
        if choice == '1':
            name = input("Name: ")
            cpf = input("CPF (numbers only): ")
            address = input("Address (optional): ")
            try:
                client = Individual(name, cpf, address)
                bank.add_client(client)
                print(f"Client {name} registered.")
            except InvalidCPFError as e:
                print(e)
        elif choice == '2':
            cpf = input("Client CPF: ")
            # find client by CPF (simple linear search)
            client = None
            for c in bank._clients:
                if isinstance(c, Individual) and c.cpf == cpf:
                    client = c
                    break
            if not client:
                print("Client not found.")
                continue
            acc_type = input("Account type (current/savings): ").strip().lower()
            if acc_type not in ('current', 'savings'):
                print("Invalid type.")
                continue
            bank.open_account(client, acc_type)
        elif choice == '3':
            acc_num = input("Account number: ")
            try:
                amount = float(input("Amount: R$"))
                bank.deposit(acc_num, amount)
            except ValueError as e:
                print(f"Error: {e}")
            except AccountNotFoundError as e:
                print(e)
        elif choice == '4':
            acc_num = input("Account number: ")
            try:
                amount = float(input("Amount: R$"))
                bank.withdraw(acc_num, amount)
            except ValueError as e:
                print(f"Error: {e}")
            except AccountNotFoundError as e:
                print(e)
        elif choice == '5':
            acc_num = input("Account number: ")
            try:
                bank.print_statement(acc_num)
            except AccountNotFoundError as e:
                print(e)
        elif choice == '6':
            print("\nAll clients and accounts:")
            for client in bank._clients:
                print(client)
                for acc in client.list_accounts():
                    print(f"  {acc}")
                print()
        elif choice == '7':
            acc_num = input("Savings account number: ")
            try:
                acc = bank.find_account(acc_num)
                if isinstance(acc, SavingsAccount):
                    acc.apply_interest()
                    print(f"Interest applied. New balance: R${acc.balance:.2f}")
                else:
                    print("Account is not a savings account.")
            except AccountNotFoundError as e:
                print(e)
        elif choice == '0':
            print("Thank you for using Python Bank.")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    main()