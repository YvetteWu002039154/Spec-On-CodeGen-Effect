from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Union

class AbstractTransaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        pass

    @abstractmethod
    def register(self, account: 'AbstractAccount') -> None:
        pass

class Deposit(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'AbstractAccount') -> None:
        if account.deposit(self.amount):
            account.history.add_transaction(self)

class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'AbstractAccount') -> None:
        if account.withdraw(self.amount):
            account.history.add_transaction(self)

class History:
    def __init__(self):
        self._transactions: List[Dict[str, Union[str, float]]] = []

    @property
    def transactions(self) -> List[Dict[str, Union[str, float]]]:
        return self._transactions

    def add_transaction(self, transaction: AbstractTransaction) -> None:
        self._transactions.append({
            "type": transaction.__class__.__name__,
            "amount": transaction.amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

class AbstractAccount(ABC):
    def __init__(self, number: int, client: 'Client', agency: str = "0001"):
        self._balance: float = 0.0
        self._number: int = number
        self._agency: str = agency
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

    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Deposit of ${amount:.2f} successful. New balance: ${self._balance:.2f}")
            return True
        print("Deposit failed. Amount must be positive.")
        return False

class CurrentAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client', agency: str = "0001", limit: float = 1000.0, withdrawal_limit: int = 3, max_withdrawal_amount: float = 500.0):
        super().__init__(number, client, agency)
        self._limit = limit
        self._withdrawal_limit = withdrawal_limit
        self._max_withdrawal_amount = max_withdrawal_amount
        self._withdrawals_count = 0

    def withdraw(self, amount: float) -> bool:
        exceeded_balance = amount > (self._balance + self._limit)
        exceeded_limit = amount > self._max_withdrawal_amount
        exceeded_withdrawals = self._withdrawals_count >= self._withdrawal_limit

        if exceeded_balance:
            print("Withdrawal failed. Insufficient funds including overdraft limit.")
            return False
        elif exceeded_limit:
            print(f"Withdrawal failed. Maximum amount per withdrawal is ${self._max_withdrawal_amount:.2f}.")
            return False
        elif exceeded_withdrawals:
            print("Withdrawal failed. Maximum daily withdrawals exceeded.")
            return False
        elif amount > 0:
            self._balance -= amount
            self._withdrawals_count += 1
            print(f"Withdrawal of ${amount:.2f} successful. New balance: ${self._balance:.2f}")
            return True
        
        print("Withdrawal failed. Amount must be positive.")
        return False

class SavingsAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client', agency: str = "0001"):
        super().__init__(number, client, agency)

    def withdraw(self, amount: float) -> bool:
        if amount > self._balance:
            print("Withdrawal failed. Insufficient funds. Savings accounts do not have an overdraft limit.")
            return False
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of ${amount:.2f} successful. New balance: ${self._balance:.2f}")
            return True
        
        print("Withdrawal failed. Amount must be positive.")
        return False

class Client:
    def __init__(self):
        self._accounts: List[AbstractAccount] = []

    @property
    def accounts(self) -> List[AbstractAccount]:
        return self._accounts

    def perform_transaction(self, account: AbstractAccount, transaction: AbstractTransaction) -> None:
        if account in self._accounts:
            transaction.register(account)
        else:
            print("Transaction failed. Account does not belong to this client.")

    def add_account(self, account: AbstractAccount) -> None:
        self._accounts.append(account)
        print(f"Account {account.number} successfully added to client.")

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str):
        super().__init__()
        if not self._validate_cpf(cpf):
            raise ValueError(f"Invalid CPF provided: {cpf}")
        self._cpf = cpf
        self._name = name
        self._birth_date = birth_date

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def name(self) -> str:
        return self._name

    @property
    def birth_date(self) -> str:
        return self._birth_date

    def _validate_cpf(self, cpf: str) -> bool:
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        if len(cpf_digits) != 11 or len(set(cpf_digits)) == 1:
            return False
        
        sum_val = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
        digit1 = 11 - (sum_val % 11)
        digit1 = 0 if digit1 > 9 else digit1
        if int(cpf_digits[9]) != digit1:
            return False
            
        sum_val = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
        digit2 = 11 - (sum_val % 11)
        digit2 = 0 if digit2 > 9 else digit2
        if int(cpf_digits[10]) != digit2:
            return False
            
        return True

if __name__ == "__main__":
    print("--- Banking System Simulation ---")
    
    try:
        client1 = Individual(cpf="12345678909", name="John Doe", birth_date="1990-01-01")
        print(f"Client {client1.name} created successfully.")
    except ValueError as e:
        print(e)

    current_account = CurrentAccount(number=1001, client=client1)
    savings_account = SavingsAccount(number=2001, client=client1)

    client1.add_account(current_account)
    client1.add_account(savings_account)

    print("\n--- Current Account Operations ---")
    client1.perform_transaction(current_account, Deposit(1000.0))
    client1.perform_transaction(current_account, Withdrawal(200.0))
    client1.perform_transaction(current_account, Withdrawal(600.0))
    client1.perform_transaction(current_account, Withdrawal(100.0))
    client1.perform_transaction(current_account, Withdrawal(50.0))
    client1.perform_transaction(current_account, Withdrawal(1500.0))

    print("\n--- Savings Account Operations ---")
    client1.perform_transaction(savings_account, Deposit(500.0))
    client1.perform_transaction(savings_account, Withdrawal(600.0))
    client1.perform_transaction(savings_account, Withdrawal(200.0))

    print("\n--- Transaction History: Current Account ---")
    for tx in current_account.history.transactions:
        print(f"{tx['date']} - {tx['type']}: ${tx['amount']:.2f}")

    print("\n--- Transaction History: Savings Account ---")
    for tx in savings_account.history.transactions:
        print(f"{tx['date']} - {tx['type']}: ${tx['amount']:.2f}")