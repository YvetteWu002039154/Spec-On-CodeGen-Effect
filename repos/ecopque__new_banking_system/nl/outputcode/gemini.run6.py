from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

class History:
    def __init__(self) -> None:
        self._transactions: List[Dict[str, Any]] = []

    @property
    def transactions(self) -> List[Dict[str, Any]]:
        return self._transactions

    def add_transaction(self, transaction: 'AbstractTransaction') -> None:
        self._transactions.append({
            "type": transaction.__class__.__name__,
            "amount": transaction.amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

class AbstractTransaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        pass

    @abstractmethod
    def register(self, account: 'AbstractAccount') -> None:
        pass

class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'AbstractAccount') -> None:
        success = account.deposit(self.amount)
        if success:
            account.history.add_transaction(self)

class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'AbstractAccount') -> None:
        success = account.withdraw(self.amount)
        if success:
            account.history.add_transaction(self)

class AbstractAccount(ABC):
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

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Deposit of R$ {amount:.2f} successful.")
            return True
        print("Operation failed: Invalid amount.")
        return False

class CurrentAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client', limit: float = 500.0, limit_withdrawals: int = 3) -> None:
        super().__init__(number, client)
        self._limit = limit
        self._limit_withdrawals = limit_withdrawals

    def withdraw(self, amount: float) -> bool:
        exceeded_balance = amount > self.balance
        exceeded_limit = amount > self._limit

        today = datetime.now().strftime("%Y-%m-%d")
        daily_withdrawals = sum(
            1 for t in self.history.transactions
            if t["type"] == "Withdrawal" and t["date"].startswith(today)
        )
        exceeded_withdrawals = daily_withdrawals >= self._limit_withdrawals

        if exceeded_balance:
            print("Operation failed: Insufficient balance.")
        elif exceeded_limit:
            print("Operation failed: Amount exceeds withdrawal limit.")
        elif exceeded_withdrawals:
            print("Operation failed: Maximum number of daily withdrawals exceeded.")
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R$ {amount:.2f} successful.")
            return True
        else:
            print("Operation failed: Invalid amount.")
        return False

class SavingsAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client') -> None:
        super().__init__(number, client)

    def withdraw(self, amount: float) -> bool:
        exceeded_balance = amount > self.balance

        if exceeded_balance:
            print("Operation failed: Insufficient balance.")
        elif amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R$ {amount:.2f} successful.")
            return True
        else:
            print("Operation failed: Invalid amount.")
        return False

class Client:
    def __init__(self, address: str) -> None:
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
    def __init__(self, cpf: str, name: str, birth_date: str, address: str) -> None:
        super().__init__(address)
        if not self._validate_cpf(cpf):
            raise ValueError("Invalid CPF.")
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

    def _validate_cpf(self, cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False

        def calc_digit(cpf_partial: str) -> int:
            total = sum(int(digit) * weight for digit, weight in zip(cpf_partial, range(len(cpf_partial) + 1, 1, -1)))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        digit1 = calc_digit(cpf[:9])
        digit2 = calc_digit(cpf[:9] + str(digit1))
        return cpf[-2:] == f"{digit1}{digit2}"

if __name__ == "__main__":
    try:
        client1 = Individual(cpf="123.456.789-09", name="John Doe", birth_date="1990-01-01", address="123 Main St")
    except ValueError as e:
        print(f"Error creating client: {e}")
        client1 = Individual(cpf="00000000191", name="John Doe", birth_date="1990-01-01", address="123 Main St")

    print(f"Client created: {client1.name} - CPF: {client1.cpf}")

    current_account = CurrentAccount(number=1001, client=client1, limit=500.0, limit_withdrawals=2)
    savings_account = SavingsAccount(number=2001, client=client1)

    client1.add_account(current_account)
    client1.add_account(savings_account)

    print("\n--- Performing Transactions on Current Account ---")
    client1.perform_transaction(current_account, Deposit(1000.0))
    client1.perform_transaction(current_account, Withdrawal(200.0))
    client1.perform_transaction(current_account, Withdrawal(600.0)) 
    client1.perform_transaction(current_account, Withdrawal(100.0)) 
    client1.perform_transaction(current_account, Withdrawal(50.0))  

    print("\n--- Performing Transactions on Savings Account ---")
    client1.perform_transaction(savings_account, Deposit(300.0))
    client1.perform_transaction(savings_account, Withdrawal(400.0)) 
    client1.perform_transaction(savings_account, Withdrawal(150.0)) 

    print("\n--- Transaction History: Current Account ---")
    for txn in current_account.history.transactions:
        print(f"{txn['date']} - {txn['type']}: R$ {txn['amount']:.2f}")
    print(f"Final Balance: R$ {current_account.balance:.2f}")

    print("\n--- Transaction History: Savings Account ---")
    for txn in savings_account.history.transactions:
        print(f"{txn['date']} - {txn['type']}: R$ {txn['amount']:.2f}")
    print(f"Final Balance: R$ {savings_account.balance:.2f}")