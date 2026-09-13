from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional


class Transaction(ABC):
    @property
    @abstractmethod
    def value(self) -> float:
        pass

    @abstractmethod
    def register(self, account: "AbstractAccount") -> None:
        pass


class Deposit(Transaction):
    def __init__(self, value: float) -> None:
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def register(self, account: "AbstractAccount") -> None:
        if account.deposit(self._value):
            account.history.add_transaction(self)


class Withdrawal(Transaction):
    def __init__(self, value: float) -> None:
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def register(self, account: "AbstractAccount") -> None:
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


class AbstractAccount(ABC):
    @property
    @abstractmethod
    def balance(self) -> float:
        pass

    @property
    @abstractmethod
    def account_number(self) -> int:
        pass

    @property
    @abstractmethod
    def branch(self) -> str:
        pass

    @property
    @abstractmethod
    def client(self) -> "Client":
        pass

    @property
    @abstractmethod
    def history(self) -> History:
        pass

    @abstractmethod
    def withdraw(self, value: float) -> bool:
        pass

    @abstractmethod
    def deposit(self, value: float) -> bool:
        pass


class Account(AbstractAccount):
    _account_counter: int = 1

    def __init__(self, client: "Client", branch: str = "0001") -> None:
        self._balance: float = 0.0
        self._account_number: int = Account._account_counter
        Account._account_counter += 1
        self._branch: str = branch
        self._client: "Client" = client
        self._history: History = History()

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def account_number(self) -> int:
        return self._account_number

    @property
    def branch(self) -> str:
        return self._branch

    @property
    def client(self) -> "Client":
        return self._client

    @property
    def history(self) -> History:
        return self._history

    @classmethod
    def new_account(cls, client: "Client", branch: str = "0001") -> "Account":
        return cls(client, branch)

    def withdraw(self, value: float) -> bool:
        if value <= 0:
            print("\n@@@ Operation failed! The value entered is invalid. @@@")
            return False
        if value > self._balance:
            print("\n@@@ Operation failed! Insufficient balance. @@@")
            return False
        self._balance -= value
        print("\n=== Withdrawal successful! ===")
        return True

    def deposit(self, value: float) -> bool:
        if value <= 0:
            print("\n@@@ Operation failed! The value entered is invalid. @@@")
            return False
        self._balance += value
        print("\n=== Deposit successful! ===")
        return True

    def __str__(self) -> str:
        return (
            f"Branch:\t\t{self._branch}\n"
            f"Account:\t{self._account_number}\n"
            f"Holder:\t\t{self._client.name}"
        )


class CurrentAccount(Account):
    WITHDRAWAL_LIMIT: float = 500.0
    DAILY_WITHDRAWAL_LIMIT: int = 3

    def __init__(self, client: "Client", branch: str = "0001",
                 withdrawal_limit: float = 500.0,
                 daily_withdrawal_limit: int = 3) -> None:
        super().__init__(client, branch)
        self._withdrawal_limit = withdrawal_limit
        self._daily_withdrawal_limit = daily_withdrawal_limit

    def withdraw(self, value: float) -> bool:
        daily_withdrawals = len(
            [t for t in self._history.transactions if isinstance(t, Withdrawal)]
        )

        exceeded_limit = value > self._withdrawal_limit
        exceeded_daily = daily_withdrawals >= self._daily_withdrawal_limit

        if exceeded_limit:
            print("\n@@@ Operation failed! Withdrawal amount exceeds the limit. @@@")
            return False
        elif exceeded_daily:
            print("\n@@@ Operation failed! Maximum number of daily withdrawals exceeded. @@@")
            return False
        else:
            return super().withdraw(value)

    def __str__(self) -> str:
        return f"Current Account\n{super().__str__()}"


class SavingsAccount(Account):
    def __init__(self, client: "Client", branch: str = "0001",
                 interest_rate: float = 0.001) -> None:
        super().__init__(client, branch)
        self._interest_rate = interest_rate

    @property
    def interest_rate(self) -> float:
        return self._interest_rate

    def apply_interest(self) -> None:
        self._balance += self._balance * self._interest_rate
        print(f"\n=== Interest applied! New balance: R$ {self._balance:.2f} ===")

    def __str__(self) -> str:
        return f"Savings Account\n{super().__str__()}"


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

    @property
    def name(self) -> str:
        return ""


class Individual(Client):
    def __init__(self, name: str, cpf: str, birth_date: str, address: str) -> None:
        super().__init__(address)
        self._name: str = name
        self._cpf: str = cpf
        self._birth_date: str = birth_date

    @property
    def name(self) -> str:
        return self._name

    @property
    def cpf(self) -> str:
        return self._cpf

    @property
    def birth_date(self) -> str:
        return self._birth_date

    def __str__(self) -> str:
        return (
            f"Name: {self._name}\n"
            f"CPF: {self._cpf}\n"
            f"Birth Date: {self._birth_date}\n"
            f"Address: {self._address}"
        )


class Bank:
    def __init__(self) -> None:
        self._clients: List[Client] = []
        self._accounts: List[Account] = []

    @property
    def clients(self) -> List[Client]:
        return self._clients

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    def find_client_by_cpf(self, cpf: str) -> Optional[Individual]:
        for client in self._clients:
            if isinstance(client, Individual) and client.cpf == cpf:
                return client
        return None

    def add_client(self, client: Client) -> None:
        self._clients.append(client)

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)

    def create_individual_client(self) -> None:
        cpf = input("Enter CPF (numbers only): ").strip()
        existing = self.find_client_by_cpf(cpf)
        if existing:
            print("\n@@@ A client with this CPF already exists! @@@")
            return

        if not self._validate_cpf(cpf):
            print("\n@@@ Invalid CPF! @@@")
            return

        name = input("Enter full name: ").strip()
        birth_date = input("Enter birth date (dd-mm-yyyy): ").strip()
        address = input("Enter address (street, number - neighborhood - city/state): ").strip()

        client = Individual(name=name, cpf=cpf, birth_date=birth_date, address=address)
        self.add_client(client)
        print(f"\n=== Client '{name}' created successfully! ===")

    def create_current_account(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! @@@")
            return

        account = CurrentAccount(client=client)
        client.add_account(account)
        self.add_account(account)
        print(f"\n=== Current Account {account.account_number} created successfully! ===")

    def create_savings_account(self) -> None:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! @@@")
            return

        account = SavingsAccount(client=client)
        client.add_account(account)
        self.add_account(account)
        print(f"\n=== Savings Account {account.account_number} created successfully! ===")

    def _get_client_and_account(self) -> Optional[tuple]:
        cpf = input("Enter client CPF: ").strip()
        client = self.find_client_by_cpf(cpf)
        if not client:
            print("\n@@@ Client not found! @@@")
            return None

        if not client.accounts:
            print("\n@@@ Client has no accounts! @@@")
            return None

        if len(client.accounts) == 1:
            return client, client.accounts[0]

        print("\nAvailable accounts:")
        for i, acc in enumerate(client.accounts, 1):
            print(f"  {i}. Account {acc.account_number} - {acc.__class__.__name__}")

        try:
            choice = int(input("Select account number: ")) - 1
            if 0 <= choice < len(client.accounts):
                return client, client.accounts[choice]
            else:
                print("\n@@@ Invalid selection! @@@")
                return None
        except ValueError:
            print("\n@@@ Invalid input! @@@")
            return None

    def deposit(self) -> None:
        result = self._get_client_and_account()
        if not result:
            return
        client, account = result

        try:
            value = float(input("Enter deposit amount: R$ "))
        except ValueError:
            print("\n@@@ Invalid amount! @@@")
            return

        transaction = Deposit(value)
        client.perform_transaction(account, transaction)

    def withdraw(self) -> None:
        result = self._get_client_and_account()
        if not result:
            return
        client, account = result

        try:
            value = float(input("Enter withdrawal amount: R$ "))
        except ValueError:
            print("\n@@@ Invalid amount! @@@")
            return

        transaction = Withdrawal(value)
        client.perform_transaction(account, transaction)

    def show_statement(self) -> None:
        result = self._get_client_and_account()
        if not result:
            return
        _, account = result

        print("\n================ STATEMENT ================")
        transactions = account.history.transactions
        if not transactions:
            print("No transactions have been performed.")
        else:
            for transaction in transactions:
                transaction_type = transaction.__class__.__name__
                print(f"{transaction_type}:\tR$ {transaction.value:.2f}")
        print(f"\nBalance:\tR$ {account.balance:.2f}")
        print("===========================================")

    def list_accounts(self) -> None:
        if not self._accounts:
            print("\n@@@ No accounts registered! @@@")
            return
        print("\n================ ACCOUNTS ================")
        for account in self._accounts:
            print("=" * 40)
            print(account)
        print("=" * 40)

    def list_clients(self) -> None:
        if not self._clients:
            print("\n@@@ No clients registered! @@@")
            return
        print("\n================ CLIENTS ================")
        for client in self._clients:
            print("=" * 40)
            print(client)
        print("=" * 40)

    @staticmethod
    def _validate_cpf(cpf: str) -> bool:
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11:
            return False
        if cpf == cpf[0] * 11:
            return False

        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        remainder1 = (sum1 * 10) % 11
        if remainder1 == 10 or remainder1 == 11:
            remainder1 = 0
        if remainder1 != int(cpf[9]):
            return False

        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        remainder2 = (sum2 * 10) % 11
        if remainder2 == 10 or remainder2 == 11:
            remainder2 = 0
        if remainder2 != int(cpf[10]):
            return False

        return True


def display_menu() -> str:
    menu = """
    ================ MENU ================
    [d]\tDeposit
    [w]\tWithdraw
    [s]\tStatement
    [nc]\tNew Client
    [na]\tNew Current Account
    [ns]\tNew Savings Account
    [la]\tList Accounts
    [lc]\tList Clients
    [q]\tQuit
    => """
    return input(menu).strip().lower()


def main() -> None:
    bank = Bank()

    while True:
        option = display_menu()

        if option == "d":
            bank.deposit()

        elif option == "w":
            bank.withdraw()

        elif option == "s":
            bank.show_statement()

        elif option == "nc":
            bank.create_individual_client()

        elif option == "na":
            bank.create_current_account()

        elif option == "ns":
            bank.create_savings_account()

        elif option == "la":
            bank.list_accounts()

        elif option == "lc":
            bank.list_clients()

        elif option == "q":
            print("\nThank you for using our banking system. Goodbye!")
            break

        else:
            print("\n@@@ Invalid operation! Please select a valid option. @@@")


if __name__ == "__main__":
    main()