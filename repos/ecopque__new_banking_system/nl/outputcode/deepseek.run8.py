import abc
import datetime
import enum
from typing import Dict, List, Optional


class TransactionType(enum.Enum):
    DEPOSIT = 'DEPOSIT'
    WITHDRAW = 'WITHDRAW'


class AbstractTransaction(abc.ABC):
    @abc.abstractmethod
    def type(self) -> TransactionType:
        ...

    @abc.abstractmethod
    def amount(self) -> float:
        ...

    @abc.abstractmethod
    def timestamp(self) -> datetime.datetime:
        ...


class Transaction(AbstractTransaction):
    _number: int = 0

    def __init__(self, transaction_type: TransactionType, amount: float):
        Transaction._number += 1
        self._id = Transaction._number
        self._type = transaction_type
        self._amount = amount
        self._timestamp = datetime.datetime.now()

    @property
    def id(self) -> int:
        return self._id

    @property
    def type(self) -> TransactionType:
        return self._type

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __str__(self) -> str:
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} {self.type.value} R${self.amount:.2f}"


class Client(abc.ABC):
    def __init__(self, name: str, address: str):
        self._name = name
        self._address = address
        self._accounts: List['AbstractAccount'] = []

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def address(self) -> str:
        return self._address

    @address.setter
    def address(self, value: str):
        self._address = value

    @property
    def accounts(self) -> List['AbstractAccount']:
        return self._accounts.copy()

    def add_account(self, account: 'AbstractAccount'):
        self._accounts.append(account)

    @abc.abstractmethod
    def id_document(self) -> str:
        ...


class PessoaFisica(Client):
    def __init__(self, name: str, address: str, cpf: str):
        super().__init__(name, address)
        self._cpf = self._validate_cpf(cpf)

    @property
    def cpf(self) -> str:
        return self._cpf

    @staticmethod
    def _validate_cpf(cpf: str) -> str:
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11:
            raise ValueError("CPF must contain 11 digits")
        if cpf == cpf[0] * 11:
            raise ValueError("Invalid CPF")
        # first digit
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        d1 = (soma * 10 % 11) % 10
        # second digit
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        d2 = (soma * 10 % 11) % 10
        if d1 != int(cpf[9]) or d2 != int(cpf[10]):
            raise ValueError("Invalid CPF")
        return cpf

    @property
    def id_document(self) -> str:
        return self._cpf


class AbstractAccount(abc.ABC):
    def __init__(self, number: int, owner: Client, opening_balance: float = 0.0):
        self._number = number
        self._owner = owner
        self._balance = opening_balance
        self._transactions: List[Transaction] = []
        self._owner.add_account(self)

    @property
    def number(self) -> int:
        return self._number

    @property
    def owner(self) -> Client:
        return self._owner

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def transactions(self) -> List[Transaction]:
        return self._transactions.copy()

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self._balance += amount
        self._transactions.append(Transaction(TransactionType.DEPOSIT, amount))

    @abc.abstractmethod
    def withdraw(self, amount: float) -> None:
        ...

    def _daily_withdraw_summary(self) -> tuple[int, float]:
        """Return (count, total) of today's withdrawals."""
        today = datetime.date.today()
        today_withdrawals = [
            t for t in self._transactions
            if t.type == TransactionType.WITHDRAW
               and t.timestamp.date() == today
        ]
        return len(today_withdrawals), sum(t.amount for t in today_withdrawals)

    @abc.abstractmethod
    def _max_daily_withdraw_amount(self) -> float:
        ...

    @abc.abstractmethod
    def _max_daily_withdraw_count(self) -> int:
        ...

    def statement(self) -> str:
        lines = [f"Account {self.number} | Owner: {self.owner.name} | Balance: R${self.balance:.2f}"]
        lines.append("Transactions:")
        for t in self._transactions:
            lines.append(f"  {t}")
        return "\n".join(lines)


class ContaCorrente(AbstractAccount):
    OVERDRAFT_LIMIT: float = 1000.0
    DAILY_WITHDRAW_LIMIT: float = 2000.0
    DAILY_WITHDRAW_COUNT_LIMIT: int = 5

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        count, daily_total = self._daily_withdraw_summary()
        if count >= self._max_daily_withdraw_count():
            raise ValueError("Daily withdrawal count limit reached")
        if daily_total + amount > self._max_daily_withdraw_amount():
            raise ValueError("Daily withdrawal amount limit exceeded")
        if self._balance + self.OVERDRAFT_LIMIT < amount:
            raise ValueError("Insufficient funds (including overdraft)")
        self._balance -= amount
        self._transactions.append(Transaction(TransactionType.WITHDRAW, amount))

    def _max_daily_withdraw_amount(self) -> float:
        return self.DAILY_WITHDRAW_LIMIT

    def _max_daily_withdraw_count(self) -> int:
        return self.DAILY_WITHDRAW_COUNT_LIMIT


class ContaPoupanca(AbstractAccount):
    DAILY_WITHDRAW_LIMIT: float = 1000.0
    DAILY_WITHDRAW_COUNT_LIMIT: int = 2

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        count, daily_total = self._daily_withdraw_summary()
        if count >= self._max_daily_withdraw_count():
            raise ValueError("Daily withdrawal count limit reached")
        if daily_total + amount > self._max_daily_withdraw_amount():
            raise ValueError("Daily withdrawal amount limit exceeded")
        if amount > self._balance:
            raise ValueError("Insufficient funds (no overdraft for savings)")
        self._balance -= amount
        self._transactions.append(Transaction(TransactionType.WITHDRAW, amount))

    def _max_daily_withdraw_amount(self) -> float:
        return self.DAILY_WITHDRAW_LIMIT

    def _max_daily_withdraw_count(self) -> int:
        return self.DAILY_WITHDRAW_COUNT_LIMIT


class Bank:
    def __init__(self):
        self._clients: Dict[str, PessoaFisica] = {}  # key: cpf without punctuation
        self._accounts: Dict[int, AbstractAccount] = {}
        self._next_account_number = 1001

    def create_client(self, name: str, address: str, cpf: str) -> PessoaFisica:
        cpf = PessoaFisica._validate_cpf(cpf)  # raises on invalid
        if cpf in self._clients:
            raise ValueError("Client with this CPF already exists")
        client = PessoaFisica(name, address, cpf)
        self._clients[cpf] = client
        return client

    def create_account(self, cpf: str, account_type: str, opening_balance: float = 0.0) -> AbstractAccount:
        cpf = ''.join(filter(str.isdigit, cpf))
        client = self._clients.get(cpf)
        if not client:
            raise ValueError("Client not found")
        number = self._next_account_number
        self._next_account_number += 1
        if account_type.lower() in ('current', 'corrente'):
            account = ContaCorrente(number, client, opening_balance)
        elif account_type.lower() in ('savings', 'poupanca'):
            account = ContaPoupanca(number, client, opening_balance)
        else:
            raise ValueError("Unknown account type")
        self._accounts[number] = account
        return account

    def deposit(self, account_number: int, amount: float) -> None:
        account = self._get_account(account_number)
        account.deposit(amount)

    def withdraw(self, account_number: int, amount: float) -> None:
        account = self._get_account(account_number)
        account.withdraw(amount)

    def get_statement(self, account_number: int) -> str:
        account = self._get_account(account_number)
        return account.statement()

    def get_client_accounts(self, cpf: str) -> List[AbstractAccount]:
        cpf = ''.join(filter(str.isdigit, cpf))
        client = self._clients.get(cpf)
        if not client:
            raise ValueError("Client not found")
        return client.accounts

    def _get_account(self, account_number: int) -> AbstractAccount:
        account = self._accounts.get(account_number)
        if not account:
            raise ValueError("Account not found")
        return account


def main():
    bank = Bank()
    while True:
        print("\n--- Banking System ---")
        print("1. Create client (Pessoa Física)")
        print("2. Create account")
        print("3. Deposit")
        print("4. Withdraw")
        print("5. Account statement")
        print("6. List client accounts")
        print("7. Exit")
        choice = input("Choose an option: ").strip()

        try:
            if choice == '1':
                name = input("Name: ").strip()
                address = input("Address: ").strip()
                cpf = input("CPF: ").strip()
                client = bank.create_client(name, address, cpf)
                print(f"Client created successfully: {client.name} (CPF: {client.cpf})")

            elif choice == '2':
                cpf = input("Client CPF: ").strip()
                acc_type = input("Account type (current/savings): ").strip().lower()
                balance = input("Opening balance (default 0): ").strip()
                balance = float(balance) if balance else 0.0
                account = bank.create_account(cpf, acc_type, balance)
                print(f"Account {account.number} ({account.__class__.__name__}) created for {account.owner.name}")

            elif choice == '3':
                acc_number = int(input("Account number: ").strip())
                amount = float(input("Amount to deposit: ").strip())
                bank.deposit(acc_number, amount)
                print("Deposit successful.")

            elif choice == '4':
                acc_number = int(input("Account number: ").strip())
                amount = float(input("Amount to withdraw: ").strip())
                bank.withdraw(acc_number, amount)
                print("Withdrawal successful.")

            elif choice == '5':
                acc_number = int(input("Account number: ").strip())
                print(bank.get_statement(acc_number))

            elif choice == '6':
                cpf = input("Client CPF: ").strip()
                accounts = bank.get_client_accounts(cpf)
                if not accounts:
                    print("No accounts found.")
                else:
                    for acc in accounts:
                        print(f"Account {acc.number} ({acc.__class__.__name__}) Balance: R${acc.balance:.2f}")

            elif choice == '7':
                print("Exiting...")
                break

            else:
                print("Invalid option.")

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()