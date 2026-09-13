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
            print("\n@@@ Operation failed! The value entered is invalid. @@@")
            return False
        self._balance += value
        print("\n=== Deposit successful! ===")
        return True

    @abstractmethod
    def withdraw(self, value: float) -> bool:
        pass


class CurrentAccount(Account):
    WITHDRAWAL_LIMIT = 500.0
    DAILY_WITHDRAWAL_LIMIT = 3

    def __init__(self, number: int, client: "Client", limit: float = 500.0, withdrawal_limit: int = 3) -> None:
        super().__init__(number, client)
        self._limit: float = limit
        self._withdrawal_limit: int = withdrawal_limit

    def withdraw(self, value: float) -> bool:
        number_of_withdrawals = len(
            [transaction for transaction in self.history.transactions
             if transaction.__class__.__name__ == "Withdrawal"]
        )

        exceeded_limit = value > self._limit
        exceeded_withdrawals = number_of_withdrawals >= self._withdrawal_limit

        if exceeded_limit:
            print("\n@@@ Operation failed! The withdrawal amount exceeds the limit. @@@")
            return False
        elif exceeded_withdrawals:
            print("\n@@@ Operation failed! Maximum number of withdrawals exceeded. @@@")
            return False
        elif value > self._balance:
            print("\n@@@ Operation failed! Insufficient balance. @@@")
            return False
        elif value <= 0:
            print("\n@@@ Operation failed! The value entered is invalid. @@@")
            return False
        else:
            self._balance -= value
            print("\n=== Withdrawal successful! ===")
            return True

    def __str__(self) -> str:
        return f"""\
            Agency:\t{self.agency}
            C/C:\t\t{self.number}
            Holder:\t{self.client.name}
        """


class SavingsAccount(Account):
    def __init__(self, number: int, client: "Client", interest_rate: float = 0.001) -> None:
        super().__init__(number, client)
        self._interest_rate: float = interest_rate

    def withdraw(self, value: float) -> bool:
        if value <= 0:
            print("\n@@@ Operation failed! The value entered is invalid. @@@")
            return False
        elif value > self._balance:
            print("\n@@@ Operation failed! Insufficient balance. @@@")
            return False
        else:
            self._balance -= value
            print("\n=== Withdrawal successful! ===")
            return True

    def apply_interest(self) -> None:
        self._balance += self._balance * self._interest_rate
        print(f"\n=== Interest applied. New balance: R$ {self._balance:.2f} ===")

    def __str__(self) -> str:
        return f"""\
            Agency:\t{self.agency}
            Savings:\t{self.number}
            Holder:\t{self.client.name}
        """


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
        return f"Individual(name={self._name}, cpf={self._cpf})"


def menu() -> str:
    menu_text = """\n
    ================ MENU ================
    [d]\tDeposit
    [s]\tWithdraw
    [e]\tStatement
    [nc]\tNew account
    [lc]\tList accounts
    [nu]\tNew user
    [q]\tQuit
    => """
    return input(textwrap.dedent(menu_text))


def filter_client(cpf: str, clients: List[Individual]) -> Optional[Individual]:
    filtered_clients = [client for client in clients if client.cpf == cpf]
    return filtered_clients[0] if filtered_clients else None


def recover_client_account(client: Individual) -> Optional[Account]:
    if not client.accounts:
        print("\n@@@ Client does not have an account! @@@")
        return None

    return client.accounts[0]


def deposit(clients: List[Individual]) -> None:
    cpf = input("Enter the client's CPF: ")
    client = filter_client(cpf, clients)

    if not client:
        print("\n@@@ Client not found! @@@")
        return

    value = float(input("Enter the deposit amount: "))
    transaction = Deposit(value)

    account = recover_client_account(client)
    if not account:
        return

    client.perform_transaction(account, transaction)


def withdraw(clients: List[Individual]) -> None:
    cpf = input("Enter the client's CPF: ")
    client = filter_client(cpf, clients)

    if not client:
        print("\n@@@ Client not found! @@@")
        return

    value = float(input("Enter the withdrawal amount: "))
    transaction = Withdrawal(value)

    account = recover_client_account(client)
    if not account:
        return

    client.perform_transaction(account, transaction)


def show_statement(clients: List[Individual]) -> None:
    cpf = input("Enter the client's CPF: ")
    client = filter_client(cpf, clients)

    if not client:
        print("\n@@@ Client not found! @@@")
        return

    account = recover_client_account(client)
    if not account:
        return

    print("\n================ STATEMENT ================")
    transactions = account.history.transactions

    statement = ""
    if not transactions:
        statement = "No transactions have been made."
    else:
        for transaction in transactions:
            statement += f"\n{transaction.__class__.__name__}:\n\tR$ {transaction.value:.2f}"

    print(statement)
    print(f"\nBalance:\n\tR$ {account.balance:.2f}")
    print("==========================================")


def create_client(clients: List[Individual]) -> None:
    cpf = input("Enter the CPF (numbers only): ")
    client = filter_client(cpf, clients)

    if client:
        print("\n@@@ There is already a client with this CPF! @@@")
        return

    name = input("Enter the full name: ")
    birth_date = input("Enter the birth date (dd-mm-yyyy): ")
    address = input("Enter the address (street, number - neighborhood - city/state abbreviation): ")

    client = Individual(name=name, birth_date=birth_date, cpf=cpf, address=address)
    clients.append(client)

    print("\n=== Client created successfully! ===")


def create_account(account_number: int, clients: List[Individual], accounts: List[Account]) -> None:
    cpf = input("Enter the client's CPF: ")
    client = filter_client(cpf, clients)

    if not client:
        print("\n@@@ Client not found, account creation flow terminated! @@@")
        return

    account_type = input("Enter account type ([cc] Current Account / [cp] Savings Account): ").strip().lower()

    if account_type == "cc":
        account = CurrentAccount.new_account(client=client, number=account_number)
    elif account_type == "cp":
        account = SavingsAccount.new_account(client=client, number=account_number)
    else:
        print("\n@@@ Invalid account type! @@@")
        return

    accounts.append(account)
    client.add_account(account)

    print("\n=== Account created successfully! ===")


def list_accounts(accounts: List[Account]) -> None:
    for account in accounts:
        print("=" * 100)
        print(textwrap.dedent(str(account)))


def validate_cpf(cpf: str) -> bool:
    cpf = ''.join(filter(str.isdigit, cpf))

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    sum_digits = sum(int(cpf[i]) * (10 - i) for i in range(9))
    first_digit = (sum_digits * 10 % 11) % 10
    if first_digit != int(cpf[9]):
        return False

    sum_digits = sum(int(cpf[i]) * (11 - i) for i in range(10))
    second_digit = (sum_digits * 10 % 11) % 10
    if second_digit != int(cpf[10]):
        return False

    return True


def main() -> None:
    clients: List[Individual] = []
    accounts: List[Account] = []

    while True:
        option = menu()

        if option == "d":
            deposit(clients)

        elif option == "s":
            withdraw(clients)

        elif option == "e":
            show_statement(clients)

        elif option == "nu":
            create_client(clients)

        elif option == "nc":
            account_number = len(accounts) + 1
            create_account(account_number, clients, accounts)

        elif option == "lc":
            list_accounts(accounts)

        elif option == "q":
            print("\nThank you for using our bank. Goodbye!")
            break

        else:
            print("\n@@@ Invalid operation, please select the desired operation again. @@@")


if __name__ == "__main__":
    main()