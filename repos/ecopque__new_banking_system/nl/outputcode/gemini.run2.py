import abc
from datetime import datetime
from typing import List, Dict, Any, Optional

class AbstractTransaction(abc.ABC):
    @property
    @abc.abstractmethod
    def amount(self) -> float:
        pass

    @abc.abstractmethod
    def register(self, account: 'AbstractAccount') -> None:
        pass

class Deposit(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'AbstractAccount') -> None:
        success = account.deposit(self.amount)
        if success:
            account.history.add_transaction(self)

class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'AbstractAccount') -> None:
        success = account.withdraw(self.amount)
        if success:
            account.history.add_transaction(self)

class History:
    def __init__(self):
        self._transactions: List[Dict[str, Any]] = []

    @property
    def transactions(self) -> List[Dict[str, Any]]:
        return self._transactions

    def add_transaction(self, transaction: AbstractTransaction) -> None:
        self._transactions.append({
            "type": transaction.__class__.__name__,
            "amount": transaction.amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

class AbstractAccount(abc.ABC):
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

    @abc.abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Deposit of ${amount:.2f} successful.")
            return True
        print("Operation failed: Invalid deposit amount.")
        return False

class CurrentAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client', limit: float = 500.0, limit_withdrawals: int = 3):
        super().__init__(number, client)
        self._limit = limit
        self._limit_withdrawals = limit_withdrawals

    def withdraw(self, amount: float) -> bool:
        exceeded_balance = amount > self.balance
        exceeded_limit = amount > self._limit
        
        today = datetime.now().strftime("%Y-%m-%d")
        num_withdrawals_today = sum(
            1 for t in self.history.transactions 
            if t['type'] == 'Withdrawal' and t['date'].startswith(today)
        )
        exceeded_withdrawals = num_withdrawals_today >= self._limit_withdrawals

        if exceeded_balance:
            print("Operation failed: Insufficient balance.")
            return False
        elif exceeded_limit:
            print(f"Operation failed: Amount exceeds the withdrawal limit of ${self._limit:.2f}.")
            return False
        elif exceeded_withdrawals:
            print("Operation failed: Maximum number of daily withdrawals exceeded.")
            return False
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of ${amount:.2f} successful.")
            return True
        else:
            print("Operation failed: Invalid withdrawal amount.")
            return False

class SavingsAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client'):
        super().__init__(number, client)

    def withdraw(self, amount: float) -> bool:
        exceeded_balance = amount > self.balance

        if exceeded_balance:
            print("Operation failed: Insufficient balance.")
            return False
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of ${amount:.2f} successful.")
            return True
        else:
            print("Operation failed: Invalid withdrawal amount.")
            return False

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
            print("Operation failed: Account does not belong to this client.")
            return
        transaction.register(account)

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str, address: str):
        super().__init__(address)
        if not self._validate_cpf(cpf):
            raise ValueError("Invalid CPF provided.")
        self._cpf = ''.join(filter(str.isdigit, cpf))
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

    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        if len(cpf_digits) != 11:
            return False
        if cpf_digits == cpf_digits[0] * 11:
            return False
        
        def calc_digit(cpf_partial: str) -> int:
            total = 0
            weight = len(cpf_partial) + 1
            for digit in cpf_partial:
                total += int(digit) * weight
                weight -= 1
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        digit1 = calc_digit(cpf_digits[:9])
        digit2 = calc_digit(cpf_digits[:9] + str(digit1))
        return cpf_digits[-2:] == f"{digit1}{digit2}"

if __name__ == "__main__":
    try:
        client1 = Individual(cpf="123.456.789-09", name="John Doe", birth_date="1990-01-01", address="123 Main St")
        print(f"Client {client1.name} created successfully.")
        
        current_account = CurrentAccount(number=1001, client=client1, limit=500.0, limit_withdrawals=3)
        savings_account = SavingsAccount(number=2001, client=client1)
        
        client1.add_account(current_account)
        client1.add_account(savings_account)
        
        print("\n--- Performing Transactions on Current Account ---")
        client1.perform_transaction(current_account, Deposit(1000.0))
        client1.perform_transaction(current_account, Withdrawal(200.0))
        client1.perform_transaction(current_account, Withdrawal(200.0))
        client1.perform_transaction(current_account, Withdrawal(200.0))
        client1.perform_transaction(current_account, Withdrawal(100.0)) 
        client1.perform_transaction(current_account, Withdrawal(600.0)) 
        
        print("\n--- Performing Transactions on Savings Account ---")
        client1.perform_transaction(savings_account, Deposit(300.0))
        client1.perform_transaction(savings_account, Withdrawal(400.0)) 
        client1.perform_transaction(savings_account, Withdrawal(150.0))
        
        print("\n--- Account History ---")
        for acc in client1.accounts:
            print(f"\nAccount Number: {acc.number} | Type: {acc.__class__.__name__} | Balance: ${acc.balance:.2f}")
            for tx in acc.history.transactions:
                print(f" - {tx['date']} | {tx['type']} | ${tx['amount']:.2f}")

    except ValueError as e:
        print(f"Error: {e}")