from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

class History:
    def __init__(self) -> None:
        self._transactions: List[dict] = []

    @property
    def transactions(self) -> List[dict]:
        return self._transactions

    def add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append({
            "type": transaction.__class__.__name__,
            "amount": transaction.amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

class Transaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        pass

    @abstractmethod
    def register(self, account: Account) -> None:
        pass

class Deposit(Transaction):
    def __init__(self, amount: float) -> None:
        self._amount: float = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: Account) -> None:
        if account.deposit(self.amount):
            account.history.add_transaction(self)

class Withdrawal(Transaction):
    def __init__(self, amount: float) -> None:
        self._amount: float = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: Account) -> None:
        if account.withdraw(self.amount):
            account.history.add_transaction(self)

class Account(ABC):
    def __init__(self, number: int, client: Client) -> None:
        self._balance: float = 0.0
        self._number: int = number
        self._agency: str = "0001"
        self._client: Client = client
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
    def client(self) -> Client:
        return self._client

    @property
    def history(self) -> History:
        return self._history

    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Deposit of R$ {amount:.2f} successful.")
            return True
        print("Deposit failed: Invalid amount.")
        return False

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

class CurrentAccount(Account):
    def __init__(self, number: int, client: Client, limit: float = 500.0, limit_withdrawals: int = 3) -> None:
        super().__init__(number, client)
        self._limit: float = limit
        self._limit_withdrawals: int = limit_withdrawals

    def withdraw(self, amount: float) -> bool:
        exceeded_balance = amount > (self._balance + self._limit)
        
        today = datetime.now().strftime("%Y-%m-%d")
        withdrawals_today = len([
            t for t in self.history.transactions 
            if t["type"] == "Withdrawal" and t["date"].startswith(today)
        ])
        exceeded_withdrawals = withdrawals_today >= self._limit_withdrawals

        if exceeded_balance:
            print("Withdrawal failed: Insufficient funds and limit.")
            return False
        elif exceeded_withdrawals:
            print("Withdrawal failed: Maximum daily withdrawals exceeded.")
            return False
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R$ {amount:.2f} successful.")
            return True
        
        print("Withdrawal failed: Invalid amount.")
        return False

class SavingsAccount(Account):
    def withdraw(self, amount: float) -> bool:
        if amount > self._balance:
            print("Withdrawal failed: Insufficient funds.")
            return False
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R$ {amount:.2f} successful.")
            return True
        
        print("Withdrawal failed: Invalid amount.")
        return False

class Client:
    def __init__(self, address: str) -> None:
        self._address: str = address
        self._accounts: List[Account] = []

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)
        print(f"Account {account.number} successfully added to client.")

    def perform_transaction(self, account: Account, transaction: Transaction) -> None:
        if account not in self._accounts:
            print("Transaction failed: Account does not belong to this client.")
            return
        transaction.register(account)

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str, address: str) -> None:
        super().__init__(address)
        if not self._validate_cpf(cpf):
            raise ValueError(f"Invalid CPF provided: {cpf}")
        self._cpf: str = cpf
        self._name: str = name
        self._birth_date: str = birth_date

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def name(self) -> str:
        return self._name

    @property
    def birth_date(self) -> str:
        return self._birth_date

    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        for i in range(9, 11):
            value = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
            digit = ((value * 10) % 11) % 10
            if digit != int(cpf[i]):
                return False
        return True

if __name__ == "__main__":
    try:
        client = Individual(cpf="11144477735", name="Alice Smith", birth_date="15-05-1985", address="456 Elm St")
        print(f"Client {client.name} created successfully.")
        
        current_account = CurrentAccount(number=1001, client=client, limit=500.0, limit_withdrawals=3)
        savings_account = SavingsAccount(number=2001, client=client)
        
        client.add_account(current_account)
        client.add_account(savings_account)
        
        print("\n--- Performing Transactions on Current Account ---")
        client.perform_transaction(current_account, Deposit(1000.0))
        client.perform_transaction(current_account, Withdrawal(200.0))
        client.perform_transaction(current_account, Withdrawal(200.0))
        client.perform_transaction(current_account, Withdrawal(200.0))
        client.perform_transaction(current_account, Withdrawal(200.0))
        
        print("\n--- Performing Transactions on Savings Account ---")
        client.perform_transaction(savings_account, Deposit(300.0))
        client.perform_transaction(savings_account, Withdrawal(400.0))
        client.perform_transaction(savings_account, Withdrawal(150.0))
        
        print("\n--- Account History ---")
        for acc in client.accounts:
            print(f"\nHistory for Account {acc.number} ({acc.__class__.__name__}):")
            for trans in acc.history.transactions:
                print(f" - {trans['date']} | {trans['type']} | R$ {trans['amount']:.2f}")
            print(f"Current Balance: R$ {acc.balance:.2f}")
            
    except ValueError as e:
        print(e)