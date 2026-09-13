from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

class AbstractTransaction(ABC):
    def __init__(self, amount: float):
        self._amount = amount
        self._created_at = datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @abstractmethod
    def execute(self, account: 'AbstractAccount') -> None:
        pass

class Deposit(AbstractTransaction):
    def execute(self, account: 'AbstractAccount') -> None:
        if account.deposit(self.amount):
            account.history.add_transaction(self)

class Withdrawal(AbstractTransaction):
    def execute(self, account: 'AbstractAccount') -> None:
        if account.withdraw(self.amount):
            account.history.add_transaction(self)

class History:
    def __init__(self):
        self._transactions: List[AbstractTransaction] = []

    @property
    def transactions(self) -> List[AbstractTransaction]:
        return self._transactions

    def add_transaction(self, transaction: AbstractTransaction) -> None:
        self._transactions.append(transaction)

class AbstractAccount(ABC):
    def __init__(self, number: int, client: 'Client'):
        self._balance: float = 0.0
        self._number: int = number
        self._agency: str = "0001"
        self._client: 'Client' = client
        self._history: History = History()

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def number(self) -> int:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def client(self) -> 'Client':
        return self._client

    @property
    def history(self) -> History:
        return self._history

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

    @abstractmethod
    def deposit(self, amount: float) -> bool:
        pass

class Account(AbstractAccount):
    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Success: Deposited R$ {amount:.2f}.")
            return True
        print("Error: Invalid deposit amount.")
        return False

    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            print("Error: Invalid withdrawal amount.")
            return False
        if amount > self._balance:
            print("Error: Insufficient funds.")
            return False
        
        self._balance -= amount
        print(f"Success: Withdrew R$ {amount:.2f}.")
        return True

class CurrentAccount(Account):
    def __init__(self, number: int, client: 'Client', limit: float = 500.0, withdrawal_limit: int = 3):
        super().__init__(number, client)
        self._limit = limit
        self._withdrawal_limit = withdrawal_limit

    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            print("Error: Invalid withdrawal amount.")
            return False

        today = datetime.now().date()
        withdrawals_today = sum(
            1 for t in self.history.transactions 
            if isinstance(t, Withdrawal) and t.created_at.date() == today
        )

        if withdrawals_today >= self._withdrawal_limit:
            print("Error: Daily withdrawal limit reached.")
            return False

        if amount > (self._balance + self._limit):
            print("Error: Insufficient funds and limit.")
            return False

        self._balance -= amount
        print(f"Success: Withdrew R$ {amount:.2f}.")
        return True

class SavingsAccount(Account):
    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            print("Error: Invalid withdrawal amount.")
            return False
        if amount > self._balance:
            print("Error: Insufficient funds. Savings accounts do not have an overdraft limit.")
            return False
        
        self._balance -= amount
        print(f"Success: Withdrew R$ {amount:.2f}.")
        return True

class Client:
    def __init__(self, address: str):
        self._address = address
        self._accounts: List[AbstractAccount] = []

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> List[AbstractAccount]:
        return self._accounts

    def add_account(self, account: AbstractAccount) -> None:
        self._accounts.append(account)
        print(f"Account {account.number} successfully added to client.")

    def perform_transaction(self, account: AbstractAccount, transaction: AbstractTransaction) -> None:
        if account not in self._accounts:
            print("Error: Account does not belong to this client.")
            return
        transaction.execute(account)

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str, address: str):
        super().__init__(address)
        if not self._validate_cpf(cpf):
            raise ValueError(f"Invalid CPF provided: {cpf}")
        self._cpf = ''.join(filter(str.isdigit, cpf))
        self._name = name
        self._birth_date = birth_date

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def name(self) -> str:
        return self._name

    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        if len(cpf_digits) != 11 or len(set(cpf_digits)) == 1:
            return False
        for i in range(9, 11):
            value = sum((int(cpf_digits[num]) * ((i + 1) - num) for num in range(0, i)))
            digit = ((value * 10) % 11) % 10
            if digit != int(cpf_digits[i]):
                return False
        return True

def print_statement(account: AbstractAccount) -> None:
    print(f"\n--- Statement for Account {account.number} ---")
    transactions = account.history.transactions
    if not transactions:
        print("No transactions found.")
    else:
        for t in transactions:
            t_type = "Deposit" if isinstance(t, Deposit) else "Withdrawal"
            print(f"{t.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {t_type}: R$ {t.amount:.2f}")
    print(f"Current Balance: R$ {account.balance:.2f}")
    print("-----------------------------------\n")

if __name__ == "__main__":
    try:
        client1 = Individual(cpf="123.456.789-09", name="John Doe", birth_date="1990-01-01", address="123 Main St")
        print(f"Client {client1.name} created successfully.")
    except ValueError as e:
        print(e)

    try:
        client_invalid = Individual(cpf="111.111.111-11", name="Invalid Doe", birth_date="1990-01-01", address="123 Main St")
    except ValueError as e:
        print(f"Expected Error Caught: {e}")

    account1 = CurrentAccount(number=1001, client=client1, limit=500.0, withdrawal_limit=3)
    client1.add_account(account1)

    account2 = SavingsAccount(number=1002, client=client1)
    client1.add_account(account2)

    print("\n--- Performing Transactions on Current Account ---")
    client1.perform_transaction(account1, Deposit(1000.0))
    client1.perform_transaction(account1, Withdrawal(200.0))
    client1.perform_transaction(account1, Withdrawal(150.0))
    client1.perform_transaction(account1, Withdrawal(50.0))
    client1.perform_transaction(account1, Withdrawal(10.0)) 
    
    print("\n--- Performing Transactions on Savings Account ---")
    client1.perform_transaction(account2, Deposit(300.0))
    client1.perform_transaction(account2, Withdrawal(400.0)) 
    client1.perform_transaction(account2, Withdrawal(100.0))

    print_statement(account1)
    print_statement(account2)