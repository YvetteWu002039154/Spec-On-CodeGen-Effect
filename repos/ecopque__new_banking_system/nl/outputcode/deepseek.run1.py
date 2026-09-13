import abc
import datetime
from typing import List, Optional


class CPF:
    """Brazilian CPF (Cadastro de Pessoas Físicas) validation and representation."""

    def __init__(self, number: str) -> None:
        self._number = self._clean(number)
        if not self._validate():
            raise ValueError("Invalid CPF")

    @staticmethod
    def _clean(number: str) -> str:
        return ''.join(filter(str.isdigit, number))

    def _validate(self) -> bool:
        if len(self._number) != 11 or self._number == self._number[0] * 11:
            return False

        # calculate first check digit
        sum_ = sum(int(self._number[i]) * (10 - i) for i in range(9))
        digit1 = (sum_ * 10 % 11) % 10

        # calculate second check digit
        sum_ = sum(int(self._number[i]) * (11 - i) for i in range(10))
        digit2 = (sum_ * 10 % 11) % 10

        return self._number[9] == str(digit1) and self._number[10] == str(digit2)

    def __str__(self) -> str:
        return self.format()

    def format(self) -> str:
        return f"{self._number[:3]}.{self._number[3:6]}.{self._number[6:9]}-{self._number[9:]}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CPF):
            return self._number == other._number
        return False

    def __hash__(self) -> int:
        return hash(self._number)


class Address:
    def __init__(self, street: str, city: str, state: str, zip_code: str) -> None:
        self.street = street
        self.city = city
        self.state = state
        self.zip_code = zip_code

    def __str__(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"


class Client:
    """Base class for bank clients."""

    def __init__(self, name: str, address: Address) -> None:
        self._name = name
        self._address = address
        self._accounts: List["AbstractAccount"] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> Address:
        return self._address

    def add_account(self, account: "AbstractAccount") -> None:
        self._accounts.append(account)

    @property
    def accounts(self) -> List["AbstractAccount"]:
        return list(self._accounts)

    def __repr__(self) -> str:
        return f"Client({self._name})"


class Individual(Client):
    """Individual client (Pessoa Física) identified by CPF."""

    def __init__(self, name: str, address: Address, cpf: CPF) -> None:
        super().__init__(name, address)
        self._cpf = cpf

    @property
    def cpf(self) -> CPF:
        return self._cpf

    def __repr__(self) -> str:
        return f"Individual({self._name}, CPF: {self._cpf})"


class AbstractTransaction(abc.ABC):
    """Abstract base for financial transactions."""

    @abc.abstractmethod
    def value(self) -> float:
        pass

    @abc.abstractmethod
    def description(self) -> str:
        pass

    @abc.abstractmethod
    def timestamp(self) -> datetime.datetime:
        pass


class Transaction(AbstractTransaction):
    """Concrete transaction recording a deposit or withdrawal."""

    def __init__(self, amount: float, operation: str) -> None:
        self._amount = amount
        if operation not in ("DEPOSIT", "WITHDRAW"):
            raise ValueError("Operation must be DEPOSIT or WITHDRAW")
        self._operation = operation
        self._timestamp = datetime.datetime.now()

    @property
    def value(self) -> float:
        return self._amount

    @property
    def description(self) -> str:
        return f"{self._operation}: ${self._amount:.2f}"

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __str__(self) -> str:
        return f"[{self._timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.description}"


class AbstractAccount(abc.ABC):
    """Abstract account interface."""

    @abc.abstractmethod
    def deposit(self, amount: float) -> None:
        pass

    @abc.abstractmethod
    def withdraw(self, amount: float) -> None:
        pass

    @abc.abstractmethod
    def balance(self) -> float:
        pass

    @abc.abstractmethod
    def statement(self) -> List[Transaction]:
        pass


class Account(AbstractAccount):
    """
    Base account implementing common behavior: deposit, daily withdrawal limit,
    transaction history. Withdrawal specifics are delegated to subclasses via
    _can_withdraw().
    """

    _DAILY_WITHDRAWAL_LIMIT = 3  # maximum number of withdrawals per day per account

    def __init__(self, number: str, agency: str, client: Client) -> None:
        self._number = number
        self._agency = agency
        self._client = client
        self._balance = 0.0
        self._transactions: List[Transaction] = []
        self._withdrawal_count_today = 0
        self._last_withdrawal_date: Optional[datetime.date] = None

    @property
    def number(self) -> str:
        return self._number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def client(self) -> Client:
        return self._client

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount
        self._transactions.append(Transaction(amount, "DEPOSIT"))

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        self._enforce_daily_limit()
        if not self._can_withdraw(amount):
            raise ValueError("Insufficient funds or limit exceeded")
        self._balance -= amount
        self._transactions.append(Transaction(amount, "WITHDRAW"))
        self._record_withdrawal()

    def _enforce_daily_limit(self) -> None:
        today = datetime.date.today()
        if self._last_withdrawal_date != today:
            self._last_withdrawal_date = today
            self._withdrawal_count_today = 0
        if self._withdrawal_count_today >= self._DAILY_WITHDRAWAL_LIMIT:
            raise ValueError("Daily withdrawal limit reached")

    def _record_withdrawal(self) -> None:
        self._withdrawal_count_today += 1

    @abc.abstractmethod
    def _can_withdraw(self, amount: float) -> bool:
        """Check whether the account's business rules allow this withdrawal."""
        pass

    @property
    def balance(self) -> float:
        return self._balance

    def statement(self) -> List[Transaction]:
        return list(self._transactions)

    def __str__(self) -> str:
        return (f"Account {self._number} (Agency: {self._agency}, "
                f"Client: {self._client.name}, Balance: ${self._balance:.2f})")


class CurrentAccount(Account):
    """Current account (Conta Corrente) with overdraft protection up to a limit."""

    OVERDRAFT_LIMIT = 500.0  # negative balance allowed up to this amount

    def _can_withdraw(self, amount: float) -> bool:
        return self._balance - amount >= -self.OVERDRAFT_LIMIT

    def __str__(self) -> str:
        return "Current" + super().__str__()


class SavingsAccount(Account):
    """Savings account (Conta Poupança) – balance cannot go negative."""

    def _can_withdraw(self, amount: float) -> bool:
        return self._balance >= amount

    def __str__(self) -> str:
        return "Savings" + super().__str__()


class Bank:
    """Main bank system responsible for managing clients and accounts."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._clients: List[Client] = []
        self._accounts: List[Account] = []
        self._next_account_number = 1000

    def add_client(self, client: Client) -> None:
        # avoid duplicate CPF for individuals
        if isinstance(client, Individual):
            existing = self.find_client_by_cpf(client.cpf)
            if existing is not None:
                raise ValueError("Client with this CPF already exists")
        self._clients.append(client)

    def find_client_by_cpf(self, cpf: CPF) -> Optional[Individual]:
        for client in self._clients:
            if isinstance(client, Individual) and client.cpf == cpf:
                return client
        return None

    def open_account(self, client: Client, account_type: str) -> Account:
        if client not in self._clients:
            raise ValueError("Client is not registered in this bank")
        number = str(self._next_account_number)
        self._next_account_number += 1
        agency = "0001"  # fixed agency for simplicity
        if account_type.lower() in ("current", "corrente", "cc"):
            account = CurrentAccount(number, agency, client)
        elif account_type.lower() in ("savings", "poupanca", "cp"):
            account = SavingsAccount(number, agency, client)
        else:
            raise ValueError("Unknown account type. Use 'current' or 'savings'.")
        client.add_account(account)
        self._accounts.append(account)
        return account

    def deposit(self, account_number: str, amount: float) -> None:
        account = self._find_account(account_number)
        account.deposit(amount)

    def withdraw(self, account_number: str, amount: float) -> None:
        account = self._find_account(account_number)
        account.withdraw(amount)

    def show_statement(self, account_number: str) -> None:
        account = self._find_account(account_number)
        print(f"Statement for account {account_number}:")
        for t in account.statement():
            print(f"  {t}")
        print(f"Current balance: ${account.balance:.2f}")

    def _find_account(self, account_number: str) -> Account:
        for acc in self._accounts:
            if acc.number == account_number:
                return acc
        raise ValueError("Account not found")

    def list_clients(self) -> None:
        print("Registered clients:")
        for c in self._clients:
            if isinstance(c, Individual):
                print(f"  {c.name} - CPF: {c.cpf}")
            else:
                print(f"  {c.name}")
            for a in c.accounts:
                print(f"    -> {a}")

    def list_accounts(self) -> None:
        print("All accounts:")
        for a in self._accounts:
            print(f"  {a}")


def main():
    bank = Bank("Python Bank")
    while True:
        print("\n===== PYTHON BANK =====")
        print("1. Register individual client")
        print("2. Open account")
        print("3. Deposit")
        print("4. Withdraw")
        print("5. Statement")
        print("6. List clients")
        print("7. List accounts")
        print("0. Exit")
        option = input("Choose an option: ").strip()

        try:
            if option == "1":
                name = input("Full name: ").strip()
                street = input("Street: ").strip()
                city = input("City: ").strip()
                state = input("State: ").strip()
                zip_code = input("ZIP Code: ").strip()
                cpf_raw = input("CPF (numbers only): ").strip()
                cpf = CPF(cpf_raw)
                address = Address(street, city, state, zip_code)
                client = Individual(name, address, cpf)
                bank.add_client(client)
                print(f"Client {client.name} registered successfully.")

            elif option == "2":
                cpf_raw = input("Client CPF: ").strip()
                cpf = CPF(cpf_raw)
                client = bank.find_client_by_cpf(cpf)
                if client is None:
                    print("Client not found. Register first.")
                    continue
                acc_type = input("Account type (current/savings): ").strip().lower()
                account = bank.open_account(client, acc_type)
                print(f"Account {account.number} opened for {client.name}.")

            elif option == "3":
                acc_num = input("Account number: ").strip()
                amount = float(input("Amount to deposit: "))
                bank.deposit(acc_num, amount)
                print(f"Deposit of ${amount:.2f} successful.")

            elif option == "4":
                acc_num = input("Account number: ").strip()
                amount = float(input("Amount to withdraw: "))
                bank.withdraw(acc_num, amount)
                print(f"Withdrawal of ${amount:.2f} successful.")

            elif option == "5":
                acc_num = input("Account number: ").strip()
                bank.show_statement(acc_num)

            elif option == "6":
                bank.list_clients()

            elif option == "7":
                bank.list_accounts()

            elif option == "0":
                print("Goodbye!")
                break

            else:
                print("Invalid option. Try again.")

        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()