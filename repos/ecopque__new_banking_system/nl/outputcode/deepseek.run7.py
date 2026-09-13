import abc
import datetime
from typing import List, Optional


class CPFValidator:
    """Validates Brazilian CPF numbers."""

    @staticmethod
    def _clean(cpf: str) -> str:
        return ''.join(filter(str.isdigit, cpf))

    @staticmethod
    def validate(cpf: str) -> bool:
        clean = CPFValidator._clean(cpf)
        if len(clean) != 11:
            return False
        if clean == clean[0] * 11:
            return False

        # First check digit
        total = sum(int(clean[i]) * (10 - i) for i in range(9))
        remainder = (total * 10) % 11
        if remainder == 10:
            remainder = 0
        if remainder != int(clean[9]):
            return False

        # Second check digit
        total = sum(int(clean[i]) * (11 - i) for i in range(10))
        remainder = (total * 10) % 11
        if remainder == 10:
            remainder = 0
        if remainder != int(clean[10]):
            return False

        return True


class Transaction:
    """Represents a single banking operation."""

    def __init__(self, type_: str, amount: float, balance_after: float):
        self.type = type_
        self.amount = amount
        self.timestamp = datetime.datetime.now()
        self.balance_after = balance_after

    def __str__(self) -> str:
        return (f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"{self.type:8s} | {self.amount:10.2f} | Balance: {self.balance_after:10.2f}")


class Client:
    """Base class for bank clients."""

    def __init__(self, name: str, address: str = ""):
        self._name = name
        self._address = address
        self._accounts: List['Account'] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    def add_account(self, account: 'Account') -> None:
        self._accounts.append(account)

    @property
    def accounts(self) -> List['Account']:
        return self._accounts.copy()

    def get_account_by_number(self, number: str) -> Optional['Account']:
        for acc in self._accounts:
            if acc.number == number:
                return acc
        return None


class Individual(Client):
    """Concrete client representing a physical person with CPF."""

    def __init__(self, name: str, cpf: str, address: str = ""):
        if not CPFValidator.validate(cpf):
            raise ValueError("Invalid CPF")
        super().__init__(name, address)
        self._cpf = CPFValidator._clean(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf


class Account(abc.ABC):
    """Abstract base class for all bank accounts."""

    def __init__(self, number: str, client: Client):
        self._number = number
        self._client = client
        self._balance: float = 0.0
        self._transactions: List[Transaction] = []
        self._creation_date = datetime.date.today()

    @property
    def number(self) -> str:
        return self._number

    @property
    def client(self) -> Client:
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    def deposit(self, amount: float) -> Transaction:
        """Add funds to the account. Common implementation for all account types."""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount
        t = Transaction("deposit", amount, self._balance)
        self._transactions.append(t)
        return t

    @abc.abstractmethod
    def withdraw(self, amount: float) -> Transaction:
        """Withdraw funds, implementation varies by account type."""
        ...

    def get_statement(self) -> List[Transaction]:
        """Return a copy of the transaction history."""
        return self._transactions.copy()

    def __str__(self) -> str:
        return f"Account {self._number} - Balance: {self._balance:.2f}"


class CurrentAccount(Account):
    """Account with overdraft and daily withdrawal limit."""

    def __init__(self, number: str, client: Client,
                 overdraft_limit: float = 500.0,
                 daily_withdrawal_limit: float = 1000.0):
        super().__init__(number, client)
        self._overdraft_limit = overdraft_limit
        self._daily_withdrawal_limit = daily_withdrawal_limit
        self._daily_withdrawal_amount: float = 0.0
        self._last_withdrawal_date: Optional[datetime.date] = None

    @property
    def overdraft_limit(self) -> float:
        return self._overdraft_limit

    def withdraw(self, amount: float) -> Transaction:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        today = datetime.date.today()
        if self._last_withdrawal_date != today:
            self._daily_withdrawal_amount = 0.0
            self._last_withdrawal_date = today

        if self._daily_withdrawal_amount + amount > self._daily_withdrawal_limit:
            raise ValueError("Daily withdrawal limit exceeded")

        if self._balance + self._overdraft_limit < amount:
            raise ValueError("Insufficient funds (including overdraft)")

        self._balance -= amount
        self._daily_withdrawal_amount += amount
        t = Transaction("withdrawal", amount, self._balance)
        self._transactions.append(t)
        return t


class SavingsAccount(Account):
    """Account that does not allow negative balance."""

    def __init__(self, number: str, client: Client, min_balance: float = 0.0):
        super().__init__(number, client)
        if min_balance < 0:
            raise ValueError("Minimum balance cannot be negative")
        self._min_balance = min_balance

    def withdraw(self, amount: float) -> Transaction:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        if self._balance - amount < self._min_balance:
            raise ValueError("Insufficient funds to maintain minimum balance")

        self._balance -= amount
        t = Transaction("withdrawal", amount, self._balance)
        self._transactions.append(t)
        return t


class Bank:
    """Central bank manager that holds clients and accounts."""

    def __init__(self):
        self._clients: List[Client] = []
        self._account_counter: int = 1000

    def _generate_account_number(self) -> str:
        self._account_counter += 1
        return f"{self._account_counter:05d}-{self._account_counter % 10}"

    def add_client(self, client: Client) -> None:
        self._clients.append(client)

    def find_client_by_cpf(self, cpf: str) -> Optional[Client]:
        clean = CPFValidator._clean(cpf)
        for client in self._clients:
            if isinstance(client, Individual) and client.cpf == clean:
                return client
        return None

    def open_current_account(self, client: Client,
                             overdraft_limit: float = 500.0,
                             daily_limit: float = 1000.0) -> CurrentAccount:
        number = self._generate_account_number()
        account = CurrentAccount(number, client, overdraft_limit, daily_limit)
        client.add_account(account)
        return account

    def open_savings_account(self, client: Client,
                             min_balance: float = 0.0) -> SavingsAccount:
        number = self._generate_account_number()
        account = SavingsAccount(number, client, min_balance)
        client.add_account(account)
        return account

    def find_account_by_number(self, number: str) -> Optional[Account]:
        for client in self._clients:
            acc = client.get_account_by_number(number)
            if acc:
                return acc
        return None


def main() -> None:
    """Simple command-line interface."""
    bank = Bank()
    print("Welcome to the Python Bank System")
    while True:
        print("\nMenu:")
        print("1. Create individual client")
        print("2. Open current account")
        print("3. Open savings account")
        print("4. Deposit")
        print("5. Withdraw")
        print("6. Show balance")
        print("7. Print statement")
        print("8. Exit")
        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                name = input("Name: ").strip()
                cpf = input("CPF (numbers only): ").strip()
                address = input("Address (optional): ").strip()
                client = Individual(name, cpf, address)
                bank.add_client(client)
                print(f"Client {name} (CPF: {client.cpf}) created successfully.")

            elif choice == "2":
                cpf = input("Client CPF: ").strip()
                client = bank.find_client_by_cpf(cpf)
                if not client:
                    print("Client not found.")
                    continue
                overdraft = input("Overdraft limit (press Enter for 500): ").strip()
                overdraft = float(overdraft) if overdraft else 500.0
                daily = input("Daily withdrawal limit (press Enter for 1000): ").strip()
                daily = float(daily) if daily else 1000.0
                account = bank.open_current_account(client, overdraft, daily)
                print(f"Current account {account.number} created for {client.name}.")

            elif choice == "3":
                cpf = input("Client CPF: ").strip()
                client = bank.find_client_by_cpf(cpf)
                if not client:
                    print("Client not found.")
                    continue
                min_bal = input("Minimum balance (press Enter for 0): ").strip()
                min_bal = float(min_bal) if min_bal else 0.0
                account = bank.open_savings_account(client, min_bal)
                print(f"Savings account {account.number} created for {client.name}.")

            elif choice == "4":
                acc_num = input("Account number: ").strip()
                account = bank.find_account_by_number(acc_num)
                if not account:
                    print("Account not found.")
                    continue
                amount = float(input("Amount to deposit: ").strip())
                account.deposit(amount)
                print(f"Deposited {amount:.2f}. New balance: {account.balance:.2f}")

            elif choice == "5":
                acc_num = input("Account number: ").strip()
                account = bank.find_account_by_number(acc_num)
                if not account:
                    print("Account not found.")
                    continue
                amount = float(input("Amount to withdraw: ").strip())
                account.withdraw(amount)
                print(f"Withdrew {amount:.2f}. New balance: {account.balance:.2f}")

            elif choice == "6":
                acc_num = input("Account number: ").strip()
                account = bank.find_account_by_number(acc_num)
                if not account:
                    print("Account not found.")
                    continue
                print(f"Account {account.number} balance: {account.balance:.2f}")

            elif choice == "7":
                acc_num = input("Account number: ").strip()
                account = bank.find_account_by_number(acc_num)
                if not account:
                    print("Account not found.")
                    continue
                print(f"Statement for account {account.number}:")
                for t in account.get_statement():
                    print(t)

            elif choice == "8":
                print("Goodbye!")
                break

            else:
                print("Invalid option. Try again.")

        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()