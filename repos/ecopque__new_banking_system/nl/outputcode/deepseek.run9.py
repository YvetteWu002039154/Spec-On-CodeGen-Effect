from __future__ import annotations

import abc
import datetime
from typing import List, Optional, Union


class Transaction:
    def __init__(self, transaction_type: str, amount: float, balance_after: float) -> None:
        self._type = transaction_type  # "DEPOSIT" or "WITHDRAW"
        self._amount = amount
        self._timestamp = datetime.datetime.now()
        self._balance_after = balance_after

    @property
    def type(self) -> str:
        return self._type

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def balance_after(self) -> float:
        return self._balance_after

    def __str__(self) -> str:
        return (f"{self._timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                f"{self._type:9s} R$ {self._amount:,.2f}  "
                f"Balance: R$ {self._balance_after:,.2f}")


class Client(abc.ABC):
    def __init__(self, name: str, address: str = "") -> None:
        self._name = name
        self._address = address
        self._accounts: List[Account] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)

    @abc.abstractmethod
    def get_identifier(self) -> str:
        pass


class Individual(Client):
    def __init__(self, name: str, cpf: str, address: str = "") -> None:
        if not self.validate_cpf(cpf):
            raise ValueError("Invalid CPF.")
        super().__init__(name, address)
        self._cpf = cpf

    @property
    def cpf(self) -> str:
        return self._cpf

    def get_identifier(self) -> str:
        return self._cpf

    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        # Remove non-digit characters
        cpf_numbers = ''.join(filter(str.isdigit, cpf))
        if len(cpf_numbers) != 11:
            return False
        if cpf_numbers == cpf_numbers[0] * 11:
            return False

        # First verification digit
        sum_of_products = sum(int(cpf_numbers[i]) * (10 - i) for i in range(9))
        expected_digit1 = (sum_of_products * 10) % 11
        if expected_digit1 == 10:
            expected_digit1 = 0
        if expected_digit1 != int(cpf_numbers[9]):
            return False

        # Second verification digit
        sum_of_products = sum(int(cpf_numbers[i]) * (11 - i) for i in range(10))
        expected_digit2 = (sum_of_products * 10) % 11
        if expected_digit2 == 10:
            expected_digit2 = 0
        if expected_digit2 != int(cpf_numbers[10]):
            return False

        return True

    def __str__(self) -> str:
        return f"Client: {self._name} (CPF: {self._cpf})"


class Account(abc.ABC):
    _daily_limit: float = 0.0

    def __init__(self, number: int, client: Client, agency: str = "0001") -> None:
        self._number = number
        self._client = client
        self._agency = agency
        self._balance = 0.0
        self._transactions: List[Transaction] = []
        client.add_account(self)

    @property
    def number(self) -> int:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def client(self) -> Client:
        return self._client

    @property
    def transactions(self) -> List[Transaction]:
        return self._transactions

    def _daily_withdrawal_total(self) -> float:
        today = datetime.date.today()
        total = 0.0
        for t in self._transactions:
            if t.type == "WITHDRAW" and t.timestamp.date() == today:
                total += t.amount
        return total

    @abc.abstractmethod
    def _can_withdraw(self, amount: float) -> bool:
        pass

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self._balance += amount
        self._transactions.append(Transaction("DEPOSIT", amount, self._balance))

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if not self._can_withdraw(amount):
            raise ValueError("Withdrawal denied due to business rules.")
        self._balance -= amount
        self._transactions.append(Transaction("WITHDRAW", amount, self._balance))

    def get_balance(self) -> float:
        return self._balance

    def __str__(self) -> str:
        return (f"Account {self._number} | Agency: {self._agency} | "
                f"Client: {self._client.name} | Balance: R$ {self._balance:,.2f}")


class CurrentAccount(Account):
    _DAILY_LIMIT = 1000.0
    _OVERDRAFT_LIMIT = 500.0

    def __init__(self, number: int, client: Client, agency: str = "0001") -> None:
        super().__init__(number, client, agency)

    def _can_withdraw(self, amount: float) -> bool:
        # Check daily limit
        if self._daily_withdrawal_total() + amount > self._DAILY_LIMIT:
            return False
        # Check overdraft: balance - amount must be >= -OVERDRAFT_LIMIT
        if self._balance - amount < -self._OVERDRAFT_LIMIT:
            return False
        return True


class SavingsAccount(Account):
    _DAILY_LIMIT = 500.0

    def __init__(self, number: int, client: Client, agency: str = "0001") -> None:
        super().__init__(number, client, agency)

    def _can_withdraw(self, amount: float) -> bool:
        # Cannot go negative
        if self._balance - amount < 0:
            return False
        if self._daily_withdrawal_total() + amount > self._DAILY_LIMIT:
            return False
        return True


class Bank:
    def __init__(self, name: str) -> None:
        self._name = name
        self._clients: List[Client] = []
        self._accounts: List[Account] = []

    @property
    def name(self) -> str:
        return self._name

    def add_client(self, client: Client) -> None:
        if any(c.get_identifier() == client.get_identifier() for c in self._clients):
            raise ValueError(f"Client with identifier {client.get_identifier()} already exists.")
        self._clients.append(client)

    def find_client_by_cpf(self, cpf: str) -> Optional[Client]:
        for client in self._clients:
            if isinstance(client, Individual) and client.cpf == cpf:
                return client
        return None

    def create_account(self, client: Client, account_type: str, number: int, agency: str = "0001") -> Account:
        if account_type not in ("current", "savings"):
            raise ValueError("Invalid account type. Use 'current' or 'savings'.")
        if self.find_account_by_number(number) is not None:
            raise ValueError(f"Account number {number} already exists.")
        if account_type == "current":
            account: Account = CurrentAccount(number, client, agency)
        else:
            account = SavingsAccount(number, client, agency)
        self._accounts.append(account)
        return account

    def find_account_by_number(self, number: int) -> Optional[Account]:
        for acc in self._accounts:
            if acc.number == number:
                return acc
        return None

    def perform_deposit(self, account_number: int, amount: float) -> None:
        account = self.find_account_by_number(account_number)
        if not account:
            raise ValueError("Account not found.")
        account.deposit(amount)
        print(f"Deposit of R$ {amount:,.2f} to account {account_number} completed.")

    def perform_withdrawal(self, account_number: int, amount: float) -> None:
        account = self.find_account_by_number(account_number)
        if not account:
            raise ValueError("Account not found.")
        account.withdraw(amount)
        print(f"Withdrawal of R$ {amount:,.2f} from account {account_number} completed.")

    def list_accounts(self) -> List[Account]:
        return self._accounts

    def print_transaction_history(self, account_number: int) -> None:
        account = self.find_account_by_number(account_number)
        if not account:
            print("Account not found.")
            return
        print(f"\nTransaction history for account {account_number}:")
        if not account.transactions:
            print("No transactions yet.")
        for t in account.transactions:
            print(t)


def main() -> None:
    bank = Bank("MyBank")
    client1 = Individual("João Silva", "12345678909")
    bank.add_client(client1)
    acc1 = bank.create_account(client1, "current", 1001)
    acc2 = bank.create_account(client1, "savings", 2001)

    print("\n--- Deposits ---")
    bank.perform_deposit(1001, 2000.0)
    bank.perform_deposit(2001, 1500.0)

    print("\n--- Withdrawals ---")
    try:
        bank.perform_withdrawal(1001, 300.0)  # OK
        bank.perform_withdrawal(2001, 600.0)  # savings daily limit 500 -> blocked
    except ValueError as e:
        print(f"Error: {e}")

    print("\n--- Balance ---")
    print(f"Account {acc1.number}: R$ {acc1.get_balance():,.2f}")
    print(f"Account {acc2.number}: R$ {acc2.get_balance():,.2f}")

    print("\n--- History ---")
    bank.print_transaction_history(1001)
    bank.print_transaction_history(2001)


if __name__ == "__main__":
    main()