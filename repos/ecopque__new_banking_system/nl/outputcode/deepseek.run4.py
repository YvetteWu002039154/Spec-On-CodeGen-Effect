from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional
import re

class CPFValidator:
    @staticmethod
    def validate(cpf: str) -> bool:
        # Remove non-digits
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False
        # First digit
        sum_ = sum(int(cpf[i]) * (10 - i) for i in range(9))
        first_digit = (sum_ * 10) % 11
        if first_digit == 10:
            first_digit = 0
        if int(cpf[9]) != first_digit:
            return False
        # Second digit
        sum_ = sum(int(cpf[i]) * (11 - i) for i in range(10))
        second_digit = (sum_ * 10) % 11
        if second_digit == 10:
            second_digit = 0
        if int(cpf[10]) != second_digit:
            return False
        return True

class Client(ABC):
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

    @address.setter
    def address(self, value: str):
        self._address = value

    def add_account(self, account: 'Account'):
        self._accounts.append(account)

    @property
    def accounts(self) -> List['Account']:
        return self._accounts

    @abstractmethod
    def get_id(self) -> str:
        pass

class Individual(Client):
    def __init__(self, name: str, cpf: str, address: str = ""):
        super().__init__(name, address)
        cpf_clean = re.sub(r'\D', '', cpf)
        if not CPFValidator.validate(cpf_clean):
            raise ValueError("Invalid CPF")
        self._cpf = cpf_clean

    @property
    def cpf(self) -> str:
        return self._cpf

    def get_id(self) -> str:
        return self._cpf

    def __str__(self):
        return f"Individual: {self._name}, CPF: {self._cpf}"

class Transaction(ABC):
    def __init__(self, amount: float, date_time: datetime):
        self._amount = amount
        self._date_time = date_time

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def date_time(self) -> datetime:
        return self._date_time

    @abstractmethod
    def get_type(self) -> str:
        pass

    @abstractmethod
    def __str__(self):
        pass

class Deposit(Transaction):
    def __init__(self, amount: float, date_time: datetime = None):
        super().__init__(amount, date_time if date_time else datetime.now())

    def get_type(self) -> str:
        return "DEPOSIT"

    def __str__(self):
        return f"Deposit of ${self._amount:.2f} on {self._date_time.strftime('%Y-%m-%d %H:%M:%S')}"

class Withdrawal(Transaction):
    def __init__(self, amount: float, date_time: datetime = None):
        super().__init__(amount, date_time if date_time else datetime.now())

    def get_type(self) -> str:
        return "WITHDRAWAL"

    def __str__(self):
        return f"Withdrawal of ${self._amount:.2f} on {self._date_time.strftime('%Y-%m-%d %H:%M:%S')}"

class Account(ABC):
    def __init__(self, number: str, owner: Client, daily_limit: float = 1000.0):
        self._number = number
        self._owner = owner
        self._balance = 0.0
        self._transactions: List[Transaction] = []
        self._daily_limit = daily_limit
        self._creation_date = date.today()

    @property
    def number(self) -> str:
        return self._number

    @property
    def owner(self) -> Client:
        return self._owner

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def daily_limit(self) -> float:
        return self._daily_limit

    @daily_limit.setter
    def daily_limit(self, value: float):
        self._daily_limit = value

    def _get_daily_withdrawal_total(self) -> float:
        today = date.today()
        total = 0.0
        for transaction in self._transactions:
            if isinstance(transaction, Withdrawal) and transaction.date_time.date() == today:
                total += transaction.amount
        return total

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount
        self._transactions.append(Deposit(amount))
        print(f"Deposit of ${amount:.2f} successful. New balance: ${self._balance:.2f}")

    @abstractmethod
    def withdraw(self, amount: float) -> None:
        pass

    def get_transactions(self) -> List[Transaction]:
        return self._transactions.copy()

    def get_statement(self) -> str:
        statement = f"Account: {self._number} | Balance: ${self._balance:.2f}\n"
        statement += "Transactions:\n"
        for t in self._transactions:
            statement += f"  {t}\n"
        return statement

class CheckingAccount(Account):
    OVERDRAFT_LIMIT = 500.0

    def __init__(self, number: str, owner: Client, daily_limit: float = 1000.0):
        super().__init__(number, owner, daily_limit)

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        today_total = self._get_daily_withdrawal_total()
        if today_total + amount > self._daily_limit:
            raise ValueError(f"Daily withdrawal limit exceeded. Remaining: ${self._daily_limit - today_total:.2f}")
        if self._balance - amount < -CheckingAccount.OVERDRAFT_LIMIT:
            raise ValueError("Overdraft limit exceeded")
        self._balance -= amount
        self._transactions.append(Withdrawal(amount))
        print(f"Withdrawal of ${amount:.2f} successful. New balance: ${self._balance:.2f}")

class SavingsAccount(Account):
    def __init__(self, number: str, owner: Client, daily_limit: float = 1000.0):
        super().__init__(number, owner, daily_limit)

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        today_total = self._get_daily_withdrawal_total()
        if today_total + amount > self._daily_limit:
            raise ValueError(f"Daily withdrawal limit exceeded. Remaining: ${self._daily_limit - today_total:.2f}")
        if self._balance - amount < 0:
            raise ValueError("Insufficient funds - savings account cannot go negative")
        self._balance -= amount
        self._transactions.append(Withdrawal(amount))
        print(f"Withdrawal of ${amount:.2f} successful. New balance: ${self._balance:.2f}")

class Bank:
    def __init__(self, name: str):
        self._name = name
        self._clients: List[Client] = []
        self._accounts: List[Account] = []
        self._account_counter = 0

    def _generate_account_number(self) -> str:
        self._account_counter += 1
        return f"{self._account_counter:06d}"

    def add_client(self, client: Client):
        if client not in self._clients:
            self._clients.append(client)
            print(f"Client {client.name} added.")
        else:
            print("Client already exists.")

    def create_checking_account(self, owner: Client) -> CheckingAccount:
        if owner not in self._clients:
            raise ValueError("Client not registered with bank")
        number = self._generate_account_number()
        account = CheckingAccount(number, owner)
        owner.add_account(account)
        self._accounts.append(account)
        print(f"Checking account {number} created for {owner.name}.")
        return account

    def create_savings_account(self, owner: Client) -> SavingsAccount:
        if owner not in self._clients:
            raise ValueError("Client not registered with bank")
        number = self._generate_account_number()
        account = SavingsAccount(number, owner)
        owner.add_account(account)
        self._accounts.append(account)
        print(f"Savings account {number} created for {owner.name}.")
        return account

    def find_account(self, number: str) -> Optional[Account]:
        for acc in self._accounts:
            if acc.number == number:
                return acc
        return None

    def deposit(self, account_number: str, amount: float):
        account = self.find_account(account_number)
        if account is None:
            raise ValueError("Account not found")
        account.deposit(amount)

    def withdraw(self, account_number: str, amount: float):
        account = self.find_account(account_number)
        if account is None:
            raise ValueError("Account not found")
        account.withdraw(amount)

    def statement(self, account_number: str) -> str:
        account = self.find_account(account_number)
        if account is None:
            raise ValueError("Account not found")
        return account.get_statement()

def main():
    bank = Bank("PythonBank")
    while True:
        print("\n--- PythonBank Menu ---")
        print("1. Register new individual client")
        print("2. Create checking account")
        print("3. Create savings account")
        print("4. Deposit")
        print("5. Withdraw")
        print("6. Account statement")
        print("7. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            name = input("Name: ")
            cpf = input("CPF: ")
            address = input("Address (optional): ")
            try:
                client = Individual(name, cpf, address)
                bank.add_client(client)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "2":
            cpf = input("Client CPF: ")
            # Find client by CPF
            clients_with_cpf = [c for c in bank._clients if isinstance(c, Individual) and c.cpf == re.sub(r'\D', '', cpf)]
            if not clients_with_cpf:
                print("Client not found.")
                continue
            owner = clients_with_cpf[0]
            try:
                bank.create_checking_account(owner)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "3":
            cpf = input("Client CPF: ")
            clients_with_cpf = [c for c in bank._clients if isinstance(c, Individual) and c.cpf == re.sub(r'\D', '', cpf)]
            if not clients_with_cpf:
                print("Client not found.")
                continue
            owner = clients_with_cpf[0]
            try:
                bank.create_savings_account(owner)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "4":
            acc_number = input("Account number: ")
            amount = float(input("Amount: "))
            try:
                bank.deposit(acc_number, amount)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "5":
            acc_number = input("Account number: ")
            amount = float(input("Amount: "))
            try:
                bank.withdraw(acc_number, amount)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "6":
            acc_number = input("Account number: ")
            try:
                statement = bank.statement(acc_number)
                print(statement)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == "7":
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    main()