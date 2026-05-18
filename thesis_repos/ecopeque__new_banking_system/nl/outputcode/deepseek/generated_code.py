from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List

def validate_cpf(cpf: str) -> bool:
    """Validate CPF (Brazilian individual taxpayer registry identification)."""
    # Remove non-digits
    digits = [int(d) for d in cpf if d.isdigit()]
    if len(digits) != 11:
        return False
    # Check if all digits are same (invalid)
    if all(d == digits[0] for d in digits):
        return False
    # Calculate first check digit
    sum1 = sum(digits[i] * (10 - i) for i in range(9))
    d1 = (sum1 * 10) % 11
    if d1 == 10:
        d1 = 0
    if digits[9] != d1:
        return False
    # Calculate second check digit
    sum2 = sum(digits[i] * (11 - i) for i in range(10))
    d2 = (sum2 * 10) % 11
    if d2 == 10:
        d2 = 0
    if digits[10] != d2:
        return False
    return True

class InsufficientFundsError(Exception):
    pass

class DailyLimitExceededError(Exception):
    pass

class Client:
    def __init__(self, name: str, address: str = ""):
        self._name = name
        self._address = address
        self._accounts: List['AbstractAccount'] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str:
        return self._address

    def add_account(self, account: 'AbstractAccount'):
        self._accounts.append(account)

    @property
    def accounts(self) -> List['AbstractAccount']:
        return self._accounts

    def __str__(self):
        return f"Client: {self._name}"

class IndividualClient(Client):
    def __init__(self, name: str, cpf: str, address: str = ""):
        super().__init__(name, address)
        if not validate_cpf(cpf):
            raise ValueError(f"Invalid CPF: {cpf}")
        self._cpf = ''.join(filter(str.isdigit, cpf))
        # Format cpf as XXX.XXX.XXX-XX
        cpf_clean = self._cpf
        self._formatted_cpf = f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"

    @property
    def cpf(self) -> str:
        return self._formatted_cpf

    def __str__(self):
        return f"Individual: {self._name}, CPF: {self._formatted_cpf}"

class Transaction(ABC):
    def __init__(self, account: 'AbstractAccount', value: float):
        self._account = account
        self._value = value
        self._timestamp = datetime.now()

    @property
    def value(self) -> float:
        return self._value

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def account(self) -> 'AbstractAccount':
        return self._account

    @abstractmethod
    def __str__(self):
        pass

class Deposit(Transaction):
    def __str__(self):
        return (f"Deposit of R${self._value:.2f} "
                f"on {self._timestamp.strftime('%d/%m/%Y %H:%M:%S')}")

class Withdrawal(Transaction):
    def __str__(self):
        return (f"Withdrawal of R${self._value:.2f} "
                f"on {self._timestamp.strftime('%d/%m/%Y %H:%M:%S')}")

class AbstractAccount(ABC):
    def __init__(self, account_number: int, agency: str, client: Client):
        self._account_number = account_number
        self._agency = agency
        self._client = client
        self._balance = 0.0
        self._transactions: List[Transaction] = []
        client.add_account(self)

    @property
    def account_number(self) -> int:
        return self._account_number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def client(self) -> Client:
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def transactions(self) -> List[Transaction]:
        return self._transactions

    def deposit(self, value: float):
        if value <= 0:
            raise ValueError("Deposit value must be positive.")
        self._balance += value
        transaction = Deposit(self, value)
        self._transactions.append(transaction)

    def withdraw(self, value: float):
        if value <= 0:
            raise ValueError("Withdrawal value must be positive.")
        self._validate_withdraw(value)
        self._balance -= value
        transaction = Withdrawal(self, value)
        self._transactions.append(transaction)

    @abstractmethod
    def _validate_withdraw(self, value: float):
        """Check if withdrawal is allowed for this account type. Raises exception if not."""
        pass

    def get_statement(self) -> List[Transaction]:
        return self._transactions

    @abstractmethod
    def __str__(self):
        pass

class CurrentAccount(AbstractAccount):
    def __init__(self, account_number: int, agency: str, client: Client,
                 overdraft_limit: float = 500.0, daily_withdrawal_limit: float = 1000.0):
        super().__init__(account_number, agency, client)
        self._overdraft_limit = overdraft_limit
        self._daily_withdrawal_limit = daily_withdrawal_limit

    def _validate_withdraw(self, value: float):
        # Check overdraft limit (negative balance allowed up to limit)
        if self._balance - value < -self._overdraft_limit:
            raise InsufficientFundsError(
                f"Insufficient funds. Current balance: R${self._balance:.2f}, "
                f"overdraft limit: R${self._overdraft_limit:.2f}"
            )
        # Check daily withdrawal limit
        today = date.today()
        today_total = 0.0
        for t in self._transactions:
            if isinstance(t, Withdrawal) and t.timestamp.date() == today:
                today_total += t.value
        if today_total + value > self._daily_withdrawal_limit:
            raise DailyLimitExceededError(
                f"Daily withdrawal limit of R${self._daily_withdrawal_limit:.2f} exceeded. "
                f"Already withdrawn today: R${today_total:.2f}"
            )

    def __str__(self):
        return (f"Current Account #{self._account_number}, "
                f"Agency: {self._agency}, "
                f"Holder: {self._client.name}, "
                f"Balance: R${self._balance:.2f}")

class SavingsAccount(AbstractAccount):
    def __init__(self, account_number: int, agency: str, client: Client,
                 minimum_balance: float = 0.0):
        super().__init__(account_number, agency, client)
        self._minimum_balance = minimum_balance

    def _validate_withdraw(self, value: float):
        if self._balance - value < self._minimum_balance:
            raise InsufficientFundsError(
                f"Withdrawal would leave balance below the minimum required "
                f"of R${self._minimum_balance:.2f}. Current balance: R${self._balance:.2f}"
            )

    def __str__(self):
        return (f"Savings Account #{self._account_number}, "
                f"Agency: {self._agency}, "
                f"Holder: {self._client.name}, "
                f"Balance: R${self._balance:.2f}")

def main():
    print("===== PYTHON BANK SYSTEM =====")
    clients = []
    accounts = []
    next_acc_number = 1001

    while True:
        print("\nMenu:")
        print("1. Create individual client")
        print("2. Create current account")
        print("3. Create savings account")
        print("4. Deposit")
        print("5. Withdraw")
        print("6. Account statement")
        print("7. List all clients")
        print("8. Exit")
        choice = input("Choose an option: ").strip()

        try:
            if choice == '1':
                name = input("Name: ")
                cpf = input("CPF (digits only): ")
                address = input("Address (optional): ")
                client = IndividualClient(name, cpf, address)
                clients.append(client)
                print(f"Client created: {client}")

            elif choice == '2':
                if not clients:
                    print("No clients available. Create a client first.")
                    continue
                print("Select client index:")
                for i, c in enumerate(clients):
                    print(f"{i}: {c}")
                idx = int(input("Index: "))
                client = clients[idx]
                acc = CurrentAccount(next_acc_number, "001", client)
                next_acc_number += 1
                accounts.append(acc)
                print(f"Account created: {acc}")

            elif choice == '3':
                if not clients:
                    print("No clients available. Create a client first.")
                    continue
                print("Select client index:")
                for i, c in enumerate(clients):
                    print(f"{i}: {c}")
                idx = int(input("Index: "))
                client = clients[idx]
                acc = SavingsAccount(next_acc_number, "001", client)
                next_acc_number += 1
                accounts.append(acc)
                print(f"Account created: {acc}")

            elif choice == '4':
                if not accounts:
                    print("No accounts. Create one first.")
                    continue
                print("Select account index:")
                for i, a in enumerate(accounts):
                    print(f"{i}: {a}")
                idx = int(input("Index: "))
                acc = accounts[idx]
                amount = float(input("Deposit amount: R$ "))
                acc.deposit(amount)
                print(f"Deposit successful. New balance: R${acc.balance:.2f}")

            elif choice == '5':
                if not accounts:
                    print("No accounts. Create one first.")
                    continue
                print("Select account index:")
                for i, a in enumerate(accounts):
                    print(f"{i}: {a}")
                idx = int(input("Index: "))
                acc = accounts[idx]
                amount = float(input("Withdrawal amount: R$ "))
                acc.withdraw(amount)
                print(f"Withdrawal successful. New balance: R${acc.balance:.2f}")

            elif choice == '6':
                if not accounts:
                    print("No accounts. Create one first.")
                    continue
                print("Select account index:")
                for i, a in enumerate(accounts):
                    print(f"{i}: {a}")
                idx = int(input("Index: "))
                acc = accounts[idx]
                print(f"\nStatement for {acc}:")
                if not acc.transactions:
                    print("No transactions yet.")
                else:
                    for t in acc.transactions:
                        print(f"  {t}")

            elif choice == '7':
                if not clients:
                    print("No clients.")
                else:
                    for c in clients:
                        print(c)
                        if c.accounts:
                            print("  Accounts:")
                            for a in c.accounts:
                                print(f"    {a}")

            elif choice == '8':
                print("Goodbye!")
                break

            else:
                print("Invalid option.")

        except ValueError as e:
            print(f"Error: {e}")
        except InsufficientFundsError as e:
            print(f"Error: {e}")
        except DailyLimitExceededError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()