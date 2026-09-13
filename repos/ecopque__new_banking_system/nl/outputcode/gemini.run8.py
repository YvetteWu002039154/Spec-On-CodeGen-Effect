import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional

class AbstractTransaction(ABC):
    @abstractmethod
    def register(self, account: 'Account') -> None:
        pass

class Deposit(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'Account') -> None:
        if account.deposit(self._amount):
            account.history.add_transaction({
                "type": "Deposit",
                "amount": self._amount,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

class Withdrawal(AbstractTransaction):
    def __init__(self, amount: float) -> None:
        self._amount = amount

    @property
    def amount(self) -> float:
        return self._amount

    def register(self, account: 'Account') -> None:
        if account.withdraw(self._amount):
            account.history.add_transaction({
                "type": "Withdrawal",
                "amount": self._amount,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

class History:
    def __init__(self) -> None:
        self._transactions: List[Dict[str, Any]] = []

    @property
    def transactions(self) -> List[Dict[str, Any]]:
        return self._transactions

    def add_transaction(self, transaction: Dict[str, Any]) -> None:
        self._transactions.append(transaction)

class AbstractAccount(ABC):
    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        pass

    @abstractmethod
    def deposit(self, amount: float) -> bool:
        pass

class Account(AbstractAccount):
    _account_sequence: int = 1

    def __init__(self, agency: str, client: 'Client') -> None:
        self._number = Account._account_sequence
        Account._account_sequence += 1
        self._agency = agency
        self._client = client
        self._balance: float = 0.0
        self._history = History()

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

    def withdraw(self, amount: float) -> bool:
        if amount <= 0:
            print("Error: Invalid withdrawal amount.")
            return False
        if amount > self._balance:
            print("Error: Insufficient balance.")
            return False
        self._balance -= amount
        print(f"Success: Withdrew ${amount:.2f}.")
        return True

    def deposit(self, amount: float) -> bool:
        if amount <= 0:
            print("Error: Invalid deposit amount.")
            return False
        self._balance += amount
        print(f"Success: Deposited ${amount:.2f}.")
        return True

class CurrentAccount(Account):
    def __init__(self, agency: str, client: 'Client', limit: float = 500.0, withdrawals_limit: int = 3) -> None:
        super().__init__(agency, client)
        self._limit = limit
        self._withdrawals_limit = withdrawals_limit

    def withdraw(self, amount: float) -> bool:
        today = datetime.now().strftime("%Y-%m-%d")
        withdrawals_today = sum(
            1 for t in self.history.transactions
            if t["type"] == "Withdrawal" and t["date"].startswith(today)
        )

        if withdrawals_today >= self._withdrawals_limit:
            print("Error: Daily withdrawal limit reached.")
            return False

        if amount > self._limit:
            print(f"Error: Amount exceeds the per-transaction limit of ${self._limit:.2f}.")
            return False

        return super().withdraw(amount)

class SavingsAccount(Account):
    def __init__(self, agency: str, client: 'Client') -> None:
        super().__init__(agency, client)

class Client:
    def __init__(self, address: str) -> None:
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

    def perform_transaction(self, account: Account, transaction: AbstractTransaction) -> None:
        if account in self._accounts:
            transaction.register(account)
        else:
            print("Error: Account does not belong to this client.")

class Individual(Client):
    def __init__(self, cpf: str, name: str, birth_date: str, address: str) -> None:
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
        cpf_clean = re.sub(r'\D', '', cpf)
        if len(cpf_clean) != 11:
            return False
        if cpf_clean == cpf_clean[0] * 11:
            return False
        
        sum_val = sum(int(cpf_clean[i]) * (10 - i) for i in range(9))
        rem = (sum_val * 10) % 11
        if rem == 10: rem = 0
        if rem != int(cpf_clean[9]):
            return False
            
        sum_val = sum(int(cpf_clean[i]) * (11 - i) for i in range(10))
        rem = (sum_val * 10) % 11
        if rem == 10: rem = 0
        if rem != int(cpf_clean[10]):
            return False
            
        return True

def get_client_by_cpf(cpf: str, clients: List[Individual]) -> Optional[Individual]:
    cpf_clean = re.sub(r'\D', '', cpf)
    for client in clients:
        if client.cpf == cpf_clean:
            return client
    return None

def get_account_by_number(number: int, accounts: List[Account]) -> Optional[Account]:
    for account in accounts:
        if account.number == number:
            return account
    return None

def main() -> None:
    clients: List[Individual] = []
    accounts: List[Account] = []
    agency = "0001"

    while True:
        print("\n" + "="*30)
        print("       BANKING SYSTEM")
        print("="*30)
        print("1. New Client (Individual)")
        print("2. New Current Account")
        print("3. New Savings Account")
        print("4. Deposit")
        print("5. Withdraw")
        print("6. Statement")
        print("7. Exit")
        print("="*30)
        
        choice = input("Select an option: ")

        if choice == '1':
            cpf = input("Enter CPF (numbers only): ")
            if get_client_by_cpf(cpf, clients):
                print("Error: Client with this CPF already exists.")
                continue
            name = input("Enter full name: ")
            birth_date = input("Enter birth date (DD-MM-YYYY): ")
            address = input("Enter address: ")
            try:
                client = Individual(cpf=cpf, name=name, birth_date=birth_date, address=address)
                clients.append(client)
                print("Success: Client created successfully.")
            except ValueError as e:
                print(f"Error: {e}")

        elif choice in ('2', '3'):
            cpf = input("Enter client CPF: ")
            client = get_client_by_cpf(cpf, clients)
            if not client:
                print("Error: Client not found.")
                continue
            
            if choice == '2':
                account = CurrentAccount(agency=agency, client=client)
                account_type = "Current Account"
            else:
                account = SavingsAccount(agency=agency, client=client)
                account_type = "Savings Account"
                
            client.add_account(account)
            accounts.append(account)
            print(f"Success: {account_type} created! Account Number: {account.number}")

        elif choice in ('4', '5'):
            acc_num_str = input("Enter account number: ")
            if not acc_num_str.isdigit():
                print("Error: Invalid account number.")
                continue
            account = get_account_by_number(int(acc_num_str), accounts)
            if not account:
                print("Error: Account not found.")
                continue
            
            amount_str = input("Enter amount: ")
            try:
                amount = float(amount_str)
            except ValueError:
                print("Error: Invalid amount.")
                continue
            
            if choice == '4':
                transaction = Deposit(amount)
            else:
                transaction = Withdrawal(amount)
                
            account.client.perform_transaction(account, transaction)

        elif choice == '6':
            acc_num_str = input("Enter account number: ")
            if not acc_num_str.isdigit():
                print("Error: Invalid account number.")
                continue
            account = get_account_by_number(int(acc_num_str), accounts)
            if not account:
                print("Error: Account not found.")
                continue
            
            print(f"\n--- Statement for Account {account.number} ---")
            transactions = account.history.transactions
            if not transactions:
                print("No transactions found.")
            else:
                for t in transactions:
                    print(f"{t['date']} | {t['type']}: ${t['amount']:.2f}")
            print(f"Current Balance: ${account.balance:.2f}")
            print("-" * 35)

        elif choice == '7':
            print("Exiting system. Goodbye!")
            break
        else:
            print("Error: Invalid option. Please try again.")

if __name__ == "__main__":
    main()