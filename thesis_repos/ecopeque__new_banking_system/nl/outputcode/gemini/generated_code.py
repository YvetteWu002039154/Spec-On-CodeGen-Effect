import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

class History:
    def __init__(self) -> None:
        self._transactions: List[Dict[str, Any]] = []

    @property
    def transactions(self) -> List[Dict[str, Any]]:
        return self._transactions

    def add_transaction(self, transaction: 'Transaction') -> None:
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
    def register(self, account: 'Account') -> None:
        pass

class Deposit(Transaction):
    def __init__(self, amount: float) -> None:
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'Account') -> None:
        success = account.deposit(self.amount)
        if success:
            account.history.add_transaction(self)

class Withdrawal(Transaction):
    def __init__(self, amount: float) -> None:
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'Account') -> None:
        success = account.withdraw(self.amount)
        if success:
            account.history.add_transaction(self)

class Account(ABC):
    def __init__(self, number: int, client: 'Client') -> None:
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
    def __init__(self, number: int, client: 'Client', limit: float = 500.0, limit_withdrawals: int = 3) -> None:
        super().__init__(number, client)
        self._limit: float = limit
        self._limit_withdrawals: int = limit_withdrawals

    def withdraw(self, amount: float) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        daily_withdrawals = [
            t for t in self.history.transactions
            if t["type"] == "Withdrawal" and t["date"].startswith(today)
        ]
        
        exceeded_balance = amount > self.balance
        exceeded_limit = amount > self._limit
        exceeded_withdrawals = len(daily_withdrawals) >= self._limit_withdrawals

        if exceeded_balance:
            print("Withdrawal failed: Insufficient balance.")
        elif exceeded_limit:
            print("Withdrawal failed: Amount exceeds the daily limit per withdrawal.")
        elif exceeded_withdrawals:
            print("Withdrawal failed: Maximum number of daily withdrawals exceeded.")
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R$ {amount:.2f} successful.")
            return True
        else:
            print("Withdrawal failed: Invalid amount.")
        return False

class SavingsAccount(Account):
    def __init__(self, number: int, client: 'Client') -> None:
        super().__init__(number, client)

    def withdraw(self, amount: float) -> bool:
        if amount > self.balance:
            print("Withdrawal failed: Insufficient balance.")
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R$ {amount:.2f} successful.")
            return True
        else:
            print("Withdrawal failed: Invalid amount.")
        return False

class Client(ABC):
    def __init__(self, address: str) -> None:
        self._address: str = address
        self._accounts: List[Account] = []

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
            raise ValueError(f"Invalid CPF provided for client {name}.")
        self._cpf: str = re.sub(r'\D', '', cpf)
        self._name: str = name
        self._birth_date: str = birth_date

    @property
    def cpf(self) -> str:
        return self._cpf

    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        cpf_clean = re.sub(r'\D', '', cpf)
        if len(cpf_clean) != 11 or len(set(cpf_clean)) == 1:
            return False
        
        for i in range(9, 11):
            value = sum((int(cpf_clean[num]) * ((i + 1) - num) for num in range(0, i)))
            digit = ((value * 10) % 11) % 10
            if digit != int(cpf_clean[i]):
                return False
        return True

if __name__ == "__main__":
    try:
        client1 = Individual(cpf="123.456.789-09", name="John Doe", birth_date="1990-01-01", address="123 Main St")
        
        current_account = CurrentAccount(number=1001, client=client1)
        savings_account = SavingsAccount(number=2001, client=client1)
        
        client1.add_account(current_account)
        client1.add_account(savings_account)
        
        print("\n--- Performing Transactions on Current Account ---")
        client1.perform_transaction(current_account, Deposit(1000.0))
        client1.perform_transaction(current_account, Withdrawal(200.0))
        client1.perform_transaction(current_account, Withdrawal(600.0)) 
        client1.perform_transaction(current_account, Withdrawal(100.0))
        client1.perform_transaction(current_account, Withdrawal(100.0))
        client1.perform_transaction(current_account, Withdrawal(50.0))  
        
        print("\n--- Performing Transactions on Savings Account ---")
        client1.perform_transaction(savings_account, Deposit(500.0))
        client1.perform_transaction(savings_account, Withdrawal(600.0)) 
        client1.perform_transaction(savings_account, Withdrawal(500.0)) 
        
        print("\n--- Account History: Current Account ---")
        for tx in current_account.history.transactions:
            print(f"{tx['date']} - {tx['type']}: R$ {tx['amount']:.2f}")
        print(f"Final Balance: R$ {current_account.balance:.2f}")
        
        print("\n--- Account History: Savings Account ---")
        for tx in savings_account.history.transactions:
            print(f"{tx['date']} - {tx['type']}: R$ {tx['amount']:.2f}")
        print(f"Final Balance: R$ {savings_account.balance:.2f}")

        print("\n--- Testing Invalid CPF ---")
        invalid_client = Individual(cpf="111.111.111-11", name="Jane Doe", birth_date="1995-05-05", address="456 Elm St")

    except ValueError as e:
        print(f"Error: {e}")