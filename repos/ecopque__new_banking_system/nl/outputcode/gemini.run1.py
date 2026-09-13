import sys
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class AbstractTransaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        pass

    @abstractmethod
    def execute(self, account: 'AbstractAccount') -> None:
        pass

class Deposit(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount
        self._timestamp = datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    def execute(self, account: 'AbstractAccount') -> None:
        if account.deposit(self.amount):
            account.history.add_transaction(self)

    def __str__(self) -> str:
        return f"[{self._timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Deposit: R$ {self.amount:.2f}"

class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount
        self._timestamp = datetime.now()

    @property
    def amount(self) -> float:
        return self._amount

    def execute(self, account: 'AbstractAccount') -> None:
        if account.withdraw(self.amount):
            account.history.add_transaction(self)

    def __str__(self) -> str:
        return f"[{self._timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Withdrawal: R$ {self.amount:.2f}"

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

    def deposit(self, amount: float) -> bool:
        if amount <= 0:
            print("Operation failed: Invalid deposit amount.")
            return False
        self._balance += amount
        return True

class CurrentAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client', limit: float = 500.0, withdrawal_limit: int = 3):
        super().__init__(number, client)
        self._limit = limit
        self._withdrawal_limit = withdrawal_limit

    def withdraw(self, amount: float) -> bool:
        today = datetime.now().date()
        withdrawals_today = len([
            t for t in self.history.transactions 
            if isinstance(t, Withdrawal) and t._timestamp.date() == today
        ])
        
        if withdrawals_today >= self._withdrawal_limit:
            print("Operation failed: Maximum daily withdrawals reached.")
            return False
        
        if amount > self._limit:
            print("Operation failed: Amount exceeds the withdrawal limit.")
            return False
        
        if amount > self.balance:
            print("Operation failed: Insufficient balance.")
            return False
        
        if amount <= 0:
            print("Operation failed: Invalid withdrawal amount.")
            return False
            
        self._balance -= amount
        return True

class SavingsAccount(AbstractAccount):
    def __init__(self, number: int, client: 'Client'):
        super().__init__(number, client)

    def withdraw(self, amount: float) -> bool:
        if amount > self.balance:
            print("Operation failed: Insufficient balance.")
            return False
        
        if amount <= 0:
            print("Operation failed: Invalid withdrawal amount.")
            return False
            
        self._balance -= amount
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

    def perform_transaction(self, account: AbstractAccount, transaction: AbstractTransaction) -> None:
        if account not in self._accounts:
            print("Operation failed: Account does not belong to this client.")
            return
        transaction.execute(account)

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

def main():
    clients: List[Client] = []
    accounts: List[AbstractAccount] = []
    account_counter = 1

    def find_client(cpf: str) -> Optional[Individual]:
        cpf_digits = ''.join(filter(str.isdigit, cpf))
        for client in clients:
            if isinstance(client, Individual) and client.cpf == cpf_digits:
                return client
        return None

    def find_account(number: int) -> Optional[AbstractAccount]:
        for account in accounts:
            if account.number == number:
                return account
        return None

    while True:
        print("\n--- Banking System Menu ---")
        print("1. Create Client (Individual)")
        print("2. Create Current Account")
        print("3. Create Savings Account")
        print("4. Deposit")
        print("5. Withdraw")
        print("6. Statement")
        print("7. Exit")
        
        try:
            choice = input("Select an option: ")
        except EOFError:
            break

        if choice == '1':
            cpf = input("Enter CPF (numbers only): ")
            if find_client(cpf):
                print("Error: Client with this CPF already exists.")
                continue
            name = input("Enter Name: ")
            birth_date = input("Enter Birth Date (DD/MM/YYYY): ")
            address = input("Enter Address: ")
            try:
                client = Individual(cpf, name, birth_date, address)
                clients.append(client)
                print("Client created successfully.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice in ('2', '3'):
            cpf = input("Enter Client CPF: ")
            client = find_client(cpf)
            if not client:
                print("Error: Client not found.")
                continue
            
            if choice == '2':
                account = CurrentAccount(number=account_counter, client=client)
            else:
                account = SavingsAccount(number=account_counter, client=client)
            
            client.add_account(account)
            accounts.append(account)
            print(f"Account created successfully. Agency: {account.agency} | Account Number: {account_counter}")
            account_counter += 1

        elif choice == '4':
            try:
                acc_num = int(input("Enter Account Number: "))
                account = find_account(acc_num)
                if not account:
                    print("Error: Account not found.")
                    continue
                amount = float(input("Enter deposit amount: "))
                transaction = Deposit(amount)
                account.client.perform_transaction(account, transaction)
                print("Deposit operation processed.")
            except ValueError:
                print("Error: Invalid input format.")

        elif choice == '5':
            try:
                acc_num = int(input("Enter Account Number: "))
                account = find_account(acc_num)
                if not account:
                    print("Error: Account not found.")
                    continue
                amount = float(input("Enter withdrawal amount: "))
                transaction = Withdrawal(amount)
                account.client.perform_transaction(account, transaction)
                print("Withdrawal operation processed.")
            except ValueError:
                print("Error: Invalid input format.")

        elif choice == '6':
            try:
                acc_num = int(input("Enter Account Number: "))
                account = find_account(acc_num)
                if not account:
                    print("Error: Account not found.")
                    continue
                print(f"\n--- Statement for Account {account.number} ---")
                if not account.history.transactions:
                    print("No transactions found.")
                else:
                    for t in account.history.transactions:
                        print(t)
                print(f"Current Balance: R$ {account.balance:.2f}")
                print("-----------------------------------")
            except ValueError:
                print("Error: Invalid input format.")

        elif choice == '7':
            print("Exiting system.")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()