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

    @property
    def withdrawal_limit(self) -> float:
        return self._withdrawal_limit

    @property
    def daily_withdrawal_limit(self) -> int:
        return self._daily_withdrawal_limit

    def withdraw(self, value: float) -> bool:
        withdrawals_today = len(
            [t for t in self._history.transactions if isinstance(t, Withdrawal)]
        )

        if value > self._withdrawal_limit:
            print("\n@@@ Operation failed! Withdrawal amount exceeds the limit. @@@")
            return False

        if withdrawals_today >= self._daily_withdrawal_limit:
            print("\n@@@ Operation failed! Maximum number of daily withdrawals exceeded. @@@")
            return False

        return super().withdraw(value)

    def __str__(self) -> str:
        return f"Current Account\n{super().__str__()}"

    def __repr__(self) -> str:
        return (
            f"CurrentAccount("
            f"branch='{self._branch}', "
            f"account_number={self._account_number}, "
            f"client={self._client.name})"
        )


class SavingsAccount(Account):
    def __init__(self, client: "Client", branch: str = "0001",
                 interest_rate: float = 0.005) -> None:
        super().__init__(client, branch)
        self._interest_rate = interest_rate

    @property
    def interest_rate(self) -> float:
        return self._interest_rate

    def apply_interest(self) -> None:
        self._balance += self._balance * self._interest_rate
        print(f"\n=== Interest applied. New balance: R$ {self._balance:.2f} ===")

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

    def __str__(self) -> str:
        return f"Savings Account\n{super().__str__()}"

    def __repr__(self) -> str:
        return (
            f"SavingsAccount("
            f"branch='{self._branch}', "
            f"account_number={self._account_number}, "
            f"client={self._client.name})"
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
        return f"Client(address={self._address})"


class Individual(Client):
    def __init__(self, name: str, cpf: str, birth_date: str, address: str) -> None:
        super().__init__(address)
        self._name: str = name
        self._cpf: str = self._validate_cpf(cpf)
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

    @staticmethod
    def _validate_cpf(cpf: str) -> str:
        cpf_digits = "".join(filter(str.isdigit, cpf))
        if len(cpf_digits) != 11:
            raise ValueError(f"Invalid CPF: {cpf}. CPF must have 11 digits.")
        return cpf_digits

    @staticmethod
    def format_cpf(cpf: str) -> str:
        cpf_digits = "".join(filter(str.isdigit, cpf))
        if len(cpf_digits) == 11:
            return f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
        return cpf

    def __str__(self) -> str:
        return (
            f"Name: {self._name}\n"
            f"CPF: {self.format_cpf(self._cpf)}\n"
            f"Birth Date: {self._birth_date}\n"
            f"Address: {self._address}"
        )

    def __repr__(self) -> str:
        return f"Individual(name='{self._name}', cpf='{self._cpf}')"


class Bank:
    def __init__(self, name: str) -> None:
        self._name: str = name
        self._clients: List[Client] = []
        self._accounts: List[Account] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def clients(self) -> List[Client]:
        return self._clients

    @property
    def accounts(self) -> List[Account]:
        return self._accounts

    def add_client(self, client: Client) -> None:
        self._clients.append(client)

    def add_account(self, account: Account) -> None:
        self._accounts.append(account)

    def find_client_by_cpf(self, cpf: str) -> Optional[Individual]:
        cpf_digits = "".join(filter(str.isdigit, cpf))
        for client in self._clients:
            if isinstance(client, Individual) and client.cpf == cpf_digits:
                return client
        return None

    def find_account_by_number(self, account_number: int) -> Optional[Account]:
        for account in self._accounts:
            if account.account_number == account_number:
                return account
        return None

    def list_accounts(self) -> None:
        if not self._accounts:
            print("\n@@@ No accounts registered. @@@")
            return
        print("\n" + "=" * 50)
        print("ACCOUNTS LIST")
        print("=" * 50)
        for account in self._accounts:
            print(str(account))
            print("-" * 50)

    def list_clients(self) -> None:
        if not self._clients:
            print("\n@@@ No clients registered. @@@")
            return
        print("\n" + "=" * 50)
        print("CLIENTS LIST")
        print("=" * 50)
        for client in self._clients:
            print(str(client))
            print("-" * 50)

    def __str__(self) -> str:
        return f"Bank: {self._name} | Clients: {len(self._clients)} | Accounts: {len(self._accounts)}"


def display_menu() -> str:
    menu = """
    ================ MENU ================
    [d]\tDeposit
    [w]\tWithdraw
    [e]\tExtract (Statement)
    [nc]\tNew Client
    [na]\tNew Account
    [la]\tList Accounts
    [lc]\tList Clients
    [q]\tQuit
    => """
    return input(menu)


def get_client(bank: Bank) -> Optional[Individual]:
    cpf = input("Enter client CPF: ")
    client = bank.find_client_by_cpf(cpf)
    if not client:
        print("\n@@@ Client not found! @@@")
        return None
    return client


def get_account(client: Individual) -> Optional[Account]:
    if not client.accounts:
        print("\n@@@ Client has no accounts! @@@")
        return None
    if len(client.accounts) == 1:
        return client.accounts[0]
    print("\nAvailable accounts:")
    for i, account in enumerate(client.accounts):
        print(f"[{i}] Account {account.account_number} - {account.__class__.__name__}")
    try:
        index = int(input("Select account index: "))
        return client.accounts[index]
    except (ValueError, IndexError):
        print("\n@@@ Invalid selection! @@@")
        return None


def deposit(bank: Bank) -> None:
    client = get_client(bank)
    if not client:
        return
    account = get_account(client)
    if not account:
        return
    try:
        value = float(input("Enter deposit amount: R$ "))
    except ValueError:
        print("\n@@@ Invalid amount! @@@")
        return
    transaction = Deposit(value)
    client.perform_transaction(account, transaction)


def withdraw(bank: Bank) -> None:
    client = get_client(bank)
    if not client:
        return
    account = get_account(client)
    if not account:
        return
    try:
        value = float(input("Enter withdrawal amount: R$ "))
    except ValueError:
        print("\n@@@ Invalid amount! @@@")
        return
    transaction = Withdrawal(value)
    client.perform_transaction(account, transaction)


def show_statement(bank: Bank) -> None:
    client = get_client(bank)
    if not client:
        return
    account = get_account(client)
    if not account:
        return

    print("\n" + "=" * 50)
    print("ACCOUNT STATEMENT")
    print("=" * 50)
    print(str(account))
    print("-" * 50)

    transactions = account.history.transactions
    if not transactions:
        print("No transactions recorded.")
    else:
        for transaction in transactions:
            transaction_type = transaction.__class__.__name__
            print(f"{transaction_type}:\t\tR$ {transaction.value:.2f}")

    print("-" * 50)
    print(f"Balance:\t\tR$ {account.balance:.2f}")
    print("=" * 50)


def create_client(bank: Bank) -> None:
    cpf = input("Enter CPF (numbers only): ")
    existing = bank.find_client_by_cpf(cpf)
    if existing:
        print("\n@@@ A client with this CPF already exists! @@@")
        return

    name = input("Enter full name: ")
    birth_date = input("Enter birth date (dd-mm-yyyy): ")
    address = input("Enter address (street, number - neighborhood - city/state): ")

    try:
        client = Individual(name=name, cpf=cpf, birth_date=birth_date, address=address)
        bank.add_client(client)
        print(f"\n=== Client {name} created successfully! ===")
    except ValueError as e:
        print(f"\n@@@ Error: {e} @@@")


def create_account(bank: Bank) -> None:
    client = get_client(bank)
    if not client:
        return

    print("\nAccount type:")
    print("[1] Current Account")
    print("[2] Savings Account")
    account_type = input("=> ")

    if account_type == "1":
        account = CurrentAccount(client=client)
    elif account_type == "2":
        account = SavingsAccount(client=client)
    else:
        print("\n@@@ Invalid account type! @@@")
        return

    bank.add_account(account)
    client.add_account(account)
    print(f"\n=== Account {account.account_number} created successfully! ===")


def list_accounts(bank: Bank) -> None:
    bank.list_accounts()


def list_clients(bank: Bank) -> None:
    bank.list_clients()


def main() -> None:
    bank = Bank("Python Bank")

    while True:
        option = display_menu().strip().lower()

        if option == "d":
            deposit(bank)
        elif option == "w":
            withdraw(bank)
        elif option == "e":
            show_statement(bank)
        elif option == "nc":
            create_client(bank)
        elif option == "na":
            create_account(bank)
        elif option == "la":
            list_accounts(bank)
        elif option == "lc":
            list_clients(bank)
        elif option == "q":
            print("\nThank you for using Python Bank. Goodbye!")
            break
        else:
            print("\n@@@ Invalid option! Please try again. @@@")


if __name__ == "__main__":
    main()