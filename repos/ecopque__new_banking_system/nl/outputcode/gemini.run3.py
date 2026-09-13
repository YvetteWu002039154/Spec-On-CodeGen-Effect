import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

class CPFValidator:
    @staticmethod
    def validate(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        for i in range(9, 11):
            value = sum((int(cpf[num]) * ((i + 1) - num) for num in range(0, i)))
            digit = ((value * 10) % 11) % 10
            if digit != int(cpf[i]):
                return False
        return True

class AbstractAccount(ABC):
    def __init__(self, number: str, client: 'Client'):
        self._balance: float = 0.0
        self._number: str = number
        self._branch: str = "0001"
        self._client: 'Client' = client
        self._history: 'History' = History()

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def number(self) -> str:
        return self._number

    @property
    def branch(self) -> str:
        return self._branch

    @property
    def client(self) -> 'Client':
        return self._client

    @property
    def history(self) -> 'History':
        return self._history

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Deposit of R$ {amount:.2f} successful.")
            return True
        print("Operation failed: Invalid deposit amount.")
        return False

class CurrentAccount(AbstractAccount):
    def __init__(self, number: str, client: 'Client', limit: float = 500.0, withdrawal_limit: int = 3):
        super().__init__(number, client)
        self._limit = limit
        self._withdrawal_limit = withdrawal_limit

    def withdraw(self, amount: float) -> bool:
        withdrawals_today = len([t for t in self.history.transactions if t['type'] == 'Withdrawal'])
        
        if amount <= 0:
            print("Operation failed: Invalid withdrawal amount.")
            return False
        if amount > self.balance + self._limit:
            print("Operation failed: Insufficient funds and limit.")
            return False
        if amount > self._limit:
            print(f"Operation failed: Amount exceeds the limit of R$ {self._limit:.2f}.")
            return False
        if withdrawals_today >= self._withdrawal_limit:
            print("Operation failed: Maximum daily withdrawals reached.")
            return False

        self._balance -= amount
        print(f"Withdrawal of R$ {amount:.2f} successful.")
        return True

class SavingsAccount(AbstractAccount):
    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            print("Operation failed: Invalid withdrawal amount.")
            return False
        if amount > self.balance:
            print("Operation failed: Insufficient funds.")
            return False

        self._balance -= amount
        print(f"Withdrawal of R$ {amount:.2f} successful.")
        return True

class AbstractTransaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        pass

    @abstractmethod
    def register(self, account: AbstractAccount) -> None:
        pass

class Deposit(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: AbstractAccount) -> None:
        if account.deposit(self.amount):
            account.history.add_transaction(self)

class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: AbstractAccount) -> None:
        if account.withdraw(self.amount):
            account.history.add_transaction(self)

class History:
    def __init__(self):
        self._transactions: List[dict] = []

    @property
    def transactions(self) -> List[dict]:
        return self._transactions

    def add_transaction(self, transaction: AbstractTransaction) -> None:
        self._transactions.append({
            "type": transaction.__class__.__name__,
            "amount": transaction.amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

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
        transaction.register(account)

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str, address: str):
        super().__init__(address)
        if not CPFValidator.validate(cpf):
            raise ValueError("Invalid CPF provided.")
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

def menu() -> str:
    menu_text = """
================ BANK SYSTEM ================
[1] New Client (Individual)
[2] New Account (Current)
[3] New Account (Savings)
[4] Deposit
[5] Withdraw
[6] Statement
[0] Exit
=============================================
=> """
    return input(menu_text)

def find_client_by_cpf(cpf: str, clients: List[Individual]) -> Optional[Individual]:
    for client in clients:
        if client.cpf == cpf:
            return client
    return None

def find_account_by_number(number: str, accounts: List[AbstractAccount]) -> Optional[AbstractAccount]:
    for account in accounts:
        if account.number == number:
            return account
    return None

def main():
    clients: List[Individual] = []
    accounts: List[AbstractAccount] = []
    account_counter = 1

    while True:
        choice = menu()

        if choice == '1':
            cpf = input("Enter CPF (numbers only): ")
            if find_client_by_cpf(cpf, clients):
                print("Error: Client with this CPF already exists.")
                continue
            name = input("Enter full name: ")
            birth_date = input("Enter birth date (DD-MM-YYYY): ")
            address = input("Enter address: ")
            try:
                client = Individual(cpf=cpf, name=name, birth_date=birth_date, address=address)
                clients.append(client)
                print("Client created successfully!")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice in ('2', '3'):
            cpf = input("Enter client CPF: ")
            client = find_client_by_cpf(cpf, clients)
            if not client:
                print("Error: Client not found.")
                continue
            
            account_number = str(account_counter)
            if choice == '2':
                account = CurrentAccount(number=account_number, client=client)
            else:
                account = SavingsAccount(number=account_number, client=client)
            
            client.add_account(account)
            accounts.append(account)
            account_counter += 1
            print(f"Account {account_number} created successfully for {client.name}.")

        elif choice == '4':
            acc_num = input("Enter account number: ")
            account = find_account_by_number(acc_num, accounts)
            if not account:
                print("Error: Account not found.")
                continue
            try:
                amount = float(input("Enter deposit amount: "))
                transaction = Deposit(amount)
                account.client.perform_transaction(account, transaction)
            except ValueError:
                print("Error: Invalid amount.")

        elif choice == '5':
            acc_num = input("Enter account number: ")
            account = find_account_by_number(acc_num, accounts)
            if not account:
                print("Error: Account not found.")
                continue
            try:
                amount = float(input("Enter withdrawal amount: "))
                transaction = Withdrawal(amount)
                account.client.perform_transaction(account, transaction)
            except ValueError:
                print("Error: Invalid amount.")

        elif choice == '6':
            acc_num = input("Enter account number: ")
            account = find_account_by_number(acc_num, accounts)
            if not account:
                print("Error: Account not found.")
                continue
            
            print(f"\n=== Statement for Account {account.number} ===")
            transactions = account.history.transactions
            if not transactions:
                print("No transactions found.")
            else:
                for t in transactions:
                    print(f"{t['date']} - {t['type']}: R$ {t['amount']:.2f}")
            print(f"Current Balance: R$ {account.balance:.2f}")
            print("===========================================")

        elif choice == '0':
            print("Exiting system...")
            sys.exit(0)
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()