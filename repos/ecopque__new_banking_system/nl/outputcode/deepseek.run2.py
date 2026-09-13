from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional


class Client(ABC):
    def __init__(self, name: str, address: str) -> None:
        self._name = name
        self._address = address
        self._accounts: List["Account"] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    def add_account(self, account: "Account") -> None:
        self._accounts.append(account)

    @property
    def accounts(self) -> List["Account"]:
        return self._accounts.copy()


class Individual(Client):
    def __init__(self, name: str, address: str, cpf: str) -> None:
        super().__init__(name, address)
        if not self.validate_cpf(cpf):
            raise ValueError("Invalid CPF")
        self._cpf = cpf

    @property
    def cpf(self) -> str:
        return self._cpf

    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        # Remove non-digit characters
        digits = ''.join(filter(str.isdigit, cpf))
        if len(digits) != 11:
            return False
        if digits == digits[0] * 11:
            return False

        def calculate_digit(base: str, factor: int) -> int:
            total = sum(int(base[i]) * (factor - i) for i in range(len(base)))
            remainder = (total * 10) % 11
            return 0 if remainder == 10 else remainder

        if calculate_digit(digits[:9], 10) != int(digits[9]):
            return False
        if calculate_digit(digits[:10], 11) != int(digits[10]):
            return False
        return True


class Account(ABC):
    def __init__(self, number: str, agency: str, client: Client, balance: float = 0.0) -> None:
        self._number = number
        self._agency = agency
        self._balance = balance
        self._client = client
        self._transactions: List["Transaction"] = []
        self._withdrawal_count_today: int = 0
        self._last_withdrawal_date: Optional[date] = None
        client.add_account(self)

    @property
    def number(self) -> str:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if value < 0:
            raise ValueError("Balance cannot be negative")
        self._balance = value

    @property
    def client(self) -> Client:
        return self._client

    @property
    def transactions(self) -> List["Transaction"]:
        return self._transactions.copy()

    def _reset_withdrawal_count_if_new_day(self) -> None:
        today = date.today()
        if self._last_withdrawal_date != today:
            self._withdrawal_count_today = 0
            self._last_withdrawal_date = today

    def _record_transaction(self, transaction: "Transaction") -> None:
        self._transactions.append(transaction)

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        deposit_transaction = Deposit(amount, self)
        self._record_transaction(deposit_transaction)

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        pass


class CurrentAccount(Account):
    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self._reset_withdrawal_count_if_new_day()
        # No daily limit for current account
        self.balance -= amount
        withdrawal_transaction = Withdrawal(amount, self)
        self._record_transaction(withdrawal_transaction)


class SavingsAccount(Account):
    MAX_DAILY_WITHDRAWALS = 3

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self._reset_withdrawal_count_if_new_day()
        if self._withdrawal_count_today >= self.MAX_DAILY_WITHDRAWALS:
            raise ValueError(f"Daily withdrawal limit of {self.MAX_DAILY_WITHDRAWALS} reached")
        self.balance -= amount
        self._withdrawal_count_today += 1
        withdrawal_transaction = Withdrawal(amount, self)
        self._record_transaction(withdrawal_transaction)


class Transaction(ABC):
    def __init__(self, amount: float, account: Account) -> None:
        self._amount = amount
        self._timestamp = datetime.now()
        self._account = account

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def account(self) -> Account:
        return self._account

    @abstractmethod
    def __str__(self) -> str:
        pass


class Deposit(Transaction):
    def __str__(self) -> str:
        return (f"Deposit of ${self._amount:.2f} at {self._timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                f"to account {self._account.number}")


class Withdrawal(Transaction):
    def __str__(self) -> str:
        return (f"Withdrawal of ${self._amount:.2f} at {self._timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                f"from account {self._account.number}")


def main() -> None:
    # Create individual client
    client = Individual("Maria Silva", "Rua das Flores, 123", "123.456.789-09")
    print(f"Client: {client.name}, CPF: {client.cpf}")

    # Create accounts
    current = CurrentAccount("00123-4", "0001", client, 1000.0)
    savings = SavingsAccount("00567-8", "0001", client, 2000.0)
    print(f"Current account balance: ${current.balance:.2f}")
    print(f"Savings account balance: ${savings.balance:.2f}")

    # Perform operations
    try:
        current.deposit(500)
        print("Deposited $500 to current account")
    except ValueError as e:
        print(e)

    try:
        current.withdraw(200)
        print("Withdrew $200 from current account")
    except ValueError as e:
        print(e)

    try:
        current.withdraw(2000)  # Should fail due to insufficient balance
    except ValueError as e:
        print(f"Error: {e}")

    try:
        savings.withdraw(100)
        savings.withdraw(100)
        savings.withdraw(100)
        savings.withdraw(100)  # Third? Actually MAX_DAILY_WITHDRAWALS=3, fourth should fail
    except ValueError as e:
        print(f"Error: {e}")

    # Print transaction history
    print("\nTransaction history (current account):")
    for t in current.transactions:
        print(t)

    print("\nTransaction history (savings account):")
    for t in savings.transactions:
        print(t)

    # Demonstrate CPF validation
    try:
        invalid_client = Individual("Joao", "Rua B", "111.111.111-11")
    except ValueError as e:
        print(f"\nCPF validation error: {e}")


if __name__ == "__main__":
    main()