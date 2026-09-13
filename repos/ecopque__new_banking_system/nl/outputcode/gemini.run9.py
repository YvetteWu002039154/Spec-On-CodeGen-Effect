import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional

class Transaction(ABC):
    @property
    @abstractmethod
    def amount(self) -> float:
        pass

    @abstractmethod
    def register(self, account: 'Account') -> None:
        pass

class Deposit(Transaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'Account') -> None:
        success = account.deposit(self.amount)
        if success:
            account.history.add_transaction(self)

class Withdrawal(Transaction):
    def __init__(self, amount: float):
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'Account') -> None:
        success = account.withdraw(self.amount)
        if success:
            account.history.add_transaction(self)

class History:
    def __init__(self):
        self._transactions: List[Dict[str, str | float]] = []

    @property
    def transactions(self) -> List[Dict[str, str | float]]:
        return self._transactions

    def add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append({
            "type": transaction.__class__.__name__,
            "amount": transaction.amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

class Account(ABC):
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

    def deposit(self, amount: float) -> bool:
        if amount > 0:
            self._balance += amount
            print(f"Deposit of R${amount:.2f} successful.")
            return True
        print("Deposit failed: Invalid amount.")
        return False

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

class CurrentAccount(Account):
    def __init__(self, number: int, client: 'Client', agency: str = "0001", limit: float = 500.0, withdrawal_limit: int = 3):
        super().__init__(number, client, agency)
        self._limit = limit
        self._withdrawal_limit = withdrawal_limit

    def withdraw(self, amount: float) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        withdrawals_today = len([
            t for t in self.history.transactions 
            if t["type"] == "Withdrawal" and str(t["date"]).startswith(today)
        ])
        
        if withdrawals_today >= self._withdrawal_limit:
            print("Withdrawal failed: Daily withdrawal limit reached.")
            return False
        
        if amount > self._limit:
            print(f"Withdrawal failed: Amount exceeds the limit of R${self._limit:.2f}.")
            return False

        if amount > self._balance:
            print("Withdrawal failed: Insufficient balance.")
            return False
        
        if amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R${amount:.2f} successful.")
            return True
        
        print("Withdrawal failed: Invalid amount.")
        return False

class SavingsAccount(Account):
    def __init__(self, number: int, client: 'Client', agency: str = "0001"):
        super().__init__(number, client, agency)

    def withdraw(self, amount: float) -> bool:
        if amount > self._balance:
            print("Withdrawal failed: Insufficient balance.")
            return False
        
        if amount > 0:
            self._balance -= amount
            print(f"Withdrawal of R${amount:.2f} successful.")
            return True
        
        print("Withdrawal failed: Invalid amount.")
        return False

class Client:
    def __init__(self, address: str):
        self._address = address
        self._accounts: List[Account] = []

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)

    def perform_transaction(self, account: Account, transaction: Transaction) -> None:
        if account in self._accounts:
            transaction.register(account)
        else:
            print("Transaction failed: Account does not belong to this client.")

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str, address: str):
        super().__init__(address)
        if not self._validate_cpf(cpf):
            raise ValueError("Invalid CPF.")
        self._cpf = re.sub(r'\D', '', cpf)
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
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False
        
        def calc_digit(cpf_partial: str) -> int:
            total = sum(int(digit) * weight for digit, weight in zip(cpf_partial, range(len(cpf_partial) + 1, 1, -1)))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        digit1 = calc_digit(cpf[:9])
        digit2 = calc_digit(cpf[:9] + str(digit1))
        return cpf == cpf[:9] + str(digit1) + str(digit2)

def find_client(cpf: str, clients: List[Individual]) -> Optional[Individual]:
    cpf_clean = re.sub(r'\D', '', cpf)
    for client in clients:
        if client.cpf == cpf_clean:
            return client
    return None

def find_account(number: int, accounts: List[Account]) -> Optional[Account]:
    for account in accounts:
        if account.number == number:
            return account
    return None

def main():
    clients: List[Individual] = []
    accounts: List[Account] = []
    account_counter = 1

    while True:
        print("\n--- Banking System Menu ---")
        print("1. Create Client (Individual)")
        print("2. Create Account (Current)")
        print("3. Create Account (Savings)")
        print("4. Deposit")
        print("5. Withdraw")
        print("6. Statement (History)")
        print("7. Exit")
        
        choice = input("Select an option: ")
        
        if choice == '1':
            cpf = input("Enter CPF (11 digits): ")
            name = input("Enter Name: ")
            birth_date = input("Enter Birth Date (DD/MM/YYYY): ")
            address = input("Enter Address: ")
            
            if find_client(cpf, clients):
                print("Client with this CPF already exists.")
                continue
                
            try:
                client = Individual(cpf=cpf, name=name, birth_date=birth_date, address=address)
                clients.append(client)
                print("Client created successfully.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice in ['2', '3']:
            cpf = input("Enter Client CPF: ")
            client = find_client(cpf, clients)
            
            if not client:
                print("Client not found.")
                continue
                
            if choice == '2':
                account = CurrentAccount(number=account_counter, client=client)
                print(f"Current Account created successfully. Account Number: {account_counter}")
            else:
                account = SavingsAccount(number=account_counter, client=client)
                print(f"Savings Account created successfully. Account Number: {account_counter}")
                
            client.add_account(account)
            accounts.append(account)
            account_counter += 1

        elif choice in ['4', '5']:
            acc_num_str = input("Enter Account Number: ")
            if not acc_num_str.isdigit():
                print("Invalid account number.")
                continue
                
            account = find_account(int(acc_num_str), accounts)
            if not account:
                print("Account not found.")
                continue
                
            amount_str = input("Enter Amount: ")
            try:
                amount = float(amount_str)
            except ValueError:
                print("Invalid amount.")
                continue
                
            if choice == '4':
                transaction = Deposit(amount)
            else:
                transaction = Withdrawal(amount)
                
            account.client.perform_transaction(account, transaction)

        elif choice == '6':
            acc_num_str = input("Enter Account Number: ")
            if not acc_num_str.isdigit():
                print("Invalid account number.")
                continue
                
            account = find_account(int(acc_num_str), accounts)
            if not account:
                print("Account not found.")
                continue
                
            print(f"\n--- Statement for Account {account.number} ---")
            transactions = account.history.transactions
            if not transactions:
                print("No transactions found.")
            else:
                for t in transactions:
                    print(f"{t['date']} - {t['type']}: R${t['amount']:.2f}")
            print(f"Current Balance: R${account.balance:.2f}")
            print("-----------------------------------")

        elif choice == '7':
            print("Exiting system...")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()