from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import textwrap


class Transaction(ABC):
    @property
    @abstractmethod
    def value(self) -> float:
        pass

    @abstractmethod
    def register(self, account: "Account") -> None:
        pass


class Deposit(Transaction):
    def __init__(self, value: float) -> None:
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def register(self, account: "Account") -> None:
        if account.deposit(self._value):
            account.history.add_transaction(self)


class Withdrawal(Transaction):
    def __init__(self, value: float) -> None:
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def register(self, account: "Account") -> None:
        if account.withdraw(self._value):
            account.history.add_transaction(self)


class History:
    def __init__(self) -> None:
        self._transactions: List[Transaction] = []

    @property
    def transactions(self) -> List[Transaction]:
        return self._transactions

    def add_transaction(self, transaction: Transaction) -> None:
        self._transactions.append(transaction)

    def generate_report(self, transaction_type: Optional[str] = None):
        for transaction in self._transactions:
            if transaction_type is None or transaction.__class__.__name__ == transaction_type:
                yield transaction

    def daily_transactions_count(self) -> int:
        today = datetime.now().date()
        count = 0
        for transaction in self._transactions:
            if hasattr(transaction, '_date') and transaction._date.date() == today:
                count += 1
        return count


class Account(ABC):
    def __init__(self, number: int, client: "Client") -> None:
        self._balance: float = 0.0
        self._number: int = number
        self._agency: str = "0001"
        self._client: "Client" = client
        self._history: History = History()

    @classmethod
    def new_account(cls, client: "Client", number: int) -> "Account":
        return cls(number, client)

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
    def client(self) -> "Client":
        return self._client

    @property
    def history(self) -> History:
        return self._history

    def deposit(self, value: float) -> bool:
        if value <= 0:
            print("\n@@@ Operation failed! The deposit value must be positive. @@@")
            return False
        self._balance += value
        print("\n=== Deposit successful! ===")
        return True

    @abstractmethod
    def withdraw(self, value: float) -> bool:
        pass

    def __str__(self) -> str:
        return (
            f"Agency:\t\t{self.agency}\n"
            f"Account:\t{self.number}\n"
            f"Holder:\t\t{self.client.name}\n"
        )


class CurrentAccount(Account):
    WITHDRAWAL_LIMIT = 500.0
    DAILY_WITHDRAWAL_LIMIT = 3

    def __init__(self, number: int, client: "Client", limit: float = 500.0, withdrawal_limit: int = 3) -> None:
        super().__init__(number, client)
        self._limit: float = limit
        self._withdrawal_limit: int = withdrawal_limit

    @classmethod
    def new_account(cls, client: "Client", number: int, limit: float = 500.0, withdrawal_limit: int = 3) -> "CurrentAccount":
        return cls(number, client, limit, withdrawal_limit)

    def withdraw(self, value: float) -> bool:
        withdrawals_today = len(
            [t for t in self._history.transactions if isinstance(t, Withdrawal)]
        )

        exceeded_limit = value > self._limit
        exceeded_withdrawals = withdrawals_today >= self._withdrawal_limit
        no_balance = value > self._balance

        if exceeded_limit:
            print("\n@@@ Operation failed! Withdrawal amount exceeds the limit. @@@")
            return False
        elif exceeded_withdrawals:
            print("\n@@@ Operation failed! Maximum number of daily withdrawals exceeded. @@@")
            return False
        elif no_balance:
            print("\n@@@ Operation failed! Insufficient balance. @@@")
            return False
        else:
            self._balance -= value
            print("\n=== Withdrawal successful! ===")
            return True

    def __str__(self) -> str:
        return (
            f"{'='*50}\n"
            f"Account Type:\tCurrent Account\n"
            f"{super().__str__()}"
            f"Balance:\tR$ {self._balance:.2f}\n"
            f"Limit:\t\tR$ {self._limit:.2f}\n"
        )


class SavingsAccount(Account):
    def __init__(self, number: int, client: "Client", interest_rate: float = 0.005) -> None:
        super().__init__(number, client)
        self._interest_rate: float = interest_rate

    @classmethod
    def new_account(cls, client: "Client", number: int, interest_rate: float = 0.005) -> "SavingsAccount":
        return cls(number, client, interest_rate)

    def withdraw(self, value: float) -> bool:
        if value > self._balance:
            print("\n@@@ Operation failed! Insufficient balance. @@@")
            return False
        self._balance -= value
        print("\n=== Withdrawal successful! ===")
        return True

    def apply_interest(self) -> None:
        self._balance += self._balance * self._interest_rate
        print(f"\n=== Interest applied! New balance: R$ {self._balance:.2f} ===")

    def __str__(self) -> str:
        return (
            f"{'='*50}\n"
            f"Account Type:\tSavings Account\n"
            f"{super().__str__()}"
            f"Balance:\tR$ {self._balance:.2f}\n"
            f"Interest Rate:\t{self._interest_rate * 100:.2f}%\n"
        )


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

    def perform_transaction(self, account: Account, transaction: Transaction) -> None:
        transaction.register(account)

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)

    def __str__(self) -> str:
        return f"Client at {self._address}"


class Individual(Client):
    def __init__(self, name: str, birth_date: str, cpf: str, address: str) -> None:
        super().__init__(address)
        self._name: str = name
        self._birth_date: str = birth_date
        self._cpf: str = cpf

    @property
    def name(self) -> str:
        return self._name

    @property
    def birth_date(self) -> str:
        return self._birth_date

    @property
    def cpf(self) -> str:
        return self._cpf

    def __str__(self) -> str:
        return (
            f"Name: {self._name}\n"
            f"CPF: {self._cpf}\n"
            f"Birth Date: {self._birth_date}\n"
            f"Address: {self._address}\n"
        )


class Bank:
    def __init__(self) -> None:
        self._clients: List[Individual] = []
        self._accounts: List[Account] = []
        self._account_counter: int = 1

    @property
    def clients(self) -> List[Individual]:
        return self._clients

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    def find_client_by_cpf(self, cpf: str) -> Optional[Individual]:
        filtered = [c for c in self._clients if c.cpf == cpf]
        return filtered[0] if filtered else None

    def find_account_by_client(self, client: Individual) -> Optional[Account]:
        filtered = [a for a in self._accounts if a.client == client]
        if not filtered:
            print("\n@@@ Client has no account! @@@")
            return None
        return filtered[0]

    def create_client(self) -> None:
        cpf = input("Enter CPF (numbers only): ").strip()
        if not self._validate_cpf(cpf):
            print("\n@@@ Invalid CPF format! @@@")
            return
        client = self.find_client_by_cpf(cpf)
        if client:
            print("\n@@@ A client with this CPF already exists! @@@")
            return
        name = input("Enter full name: ").strip()
        birth_date = input("Enter birth date (dd-mm-yyyy): ").strip()
        address = input("Enter address (street, number - neighborhood - city/state): ").strip()
        client = Individual(name=name, birth_date=birth_date, cpf=cpf, address=address)
        self._clients.append(client)
        print("\n=== Client created successfully! ===")

    def create_current_account(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! Please create a client first. @@@")
            return
        account = CurrentAccount.new_account(client=client, number=self._account_counter)
        self._accounts.append(account)
        client.add_account(account)
        self._account_counter += 1
        print(f"\n=== Current Account created successfully! Account number: {account.number} ===")

    def create_savings_account(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! Please create a client first. @@@")
            return
        account = SavingsAccount.new_account(client=client, number=self._account_counter)
        self._accounts.append(account)
        client.add_account(account)
        self._account_counter += 1
        print(f"\n=== Savings Account created successfully! Account number: {account.number} ===")

    def deposit(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! @@@")
            return
        value_str = input("Enter deposit amount: R$ ").strip()
        try:
            value = float(value_str)
        except ValueError:
            print("\n@@@ Invalid amount! @@@")
            return
        account = self.find_account_by_client(client)
        if not account:
            return
        transaction = Deposit(value)
        client.perform_transaction(account, transaction)

    def withdraw(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! @@@")
            return
        value_str = input("Enter withdrawal amount: R$ ").strip()
        try:
            value = float(value_str)
        except ValueError:
            print("\n@@@ Invalid amount! @@@")
            return
        account = self.find_account_by_client(client)
        if not account:
            return
        transaction = Withdrawal(value)
        client.perform_transaction(account, transaction)

    def show_statement(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! @@@")
            return
        account = self.find_account_by_client(client)
        if not account:
            return
        print("\n" + "=" * 50)
        print("BANK STATEMENT".center(50))
        print("=" * 50)
        transactions = account.history.transactions
        if not transactions:
            print("No transactions found.")
        else:
            for transaction in transactions:
                transaction_type = transaction.__class__.__name__
                print(f"{transaction_type}:\t\tR$ {transaction.value:.2f}")
        print(f"\nBalance:\t\tR$ {account.balance:.2f}")
        print("=" * 50)

    def list_accounts(self) -> None:
        if not self._accounts:
            print("\n@@@ No accounts registered! @@@")
            return
        print("\n" + "=" * 50)
        print("REGISTERED ACCOUNTS".center(50))
        print("=" * 50)
        for account in self._accounts:
            print(str(account))

    def list_clients(self) -> None:
        if not self._clients:
            print("\n@@@ No clients registered! @@@")
            return
        print("\n" + "=" * 50)
        print("REGISTERED CLIENTS".center(50))
        print("=" * 50)
        for client in self._clients:
            print(str(client))
            print("-" * 50)

    def _validate_cpf(self, cpf: str) -> bool:
        cpf_clean = cpf.replace(".", "").replace("-", "").strip()
        if not cpf_clean.isdigit():
            return False
        if len(cpf_clean) != 11:
            return False
        if len(set(cpf_clean)) == 1:
            return False
        return True

    def run(self) -> None:
        menu = textwrap.dedent("""
        ========================================
                    BANK SYSTEM MENU
        ========================================
        [d]  Deposit
        [w]  Withdraw
        [s]  Statement
        [nc] New Client
        [na] New Current Account
        [ns] New Savings Account
        [la] List Accounts
        [lc] List Clients
        [q]  Quit
        ========================================
        => """)

        while True:
            option = input(menu).strip().lower()

            if option == "d":
                self.deposit()
            elif option == "w":
                self.withdraw()
            elif option == "s":
                self.show_statement()
            elif option == "nc":
                self.create_client()
            elif option == "na":
                self.create_current_account()
            elif option == "ns":
                self.create_savings_account()
            elif option == "la":
                self.list_accounts()
            elif option == "lc":
                self.list_clients()
            elif option == "q":
                print("\nThank you for using our banking system. Goodbye!")
                break
            else:
                print("\n@@@ Invalid option! Please try again. @@@")


def main() -> None:
    bank = Bank()
    bank.run()


if __name__ == "__main__":
    main()