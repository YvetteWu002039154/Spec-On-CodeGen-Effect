from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional


class ValidationError(Exception):
    pass


class BusinessRuleError(Exception):
    pass


class AbstractTransaction(ABC):
    def __init__(self, amount: float) -> None:
        self._amount = self._validate_amount(amount)
        self._timestamp = datetime.now()

    @staticmethod
    def _validate_amount(amount: float) -> float:
        if not isinstance(amount, (int, float)):
            raise ValidationError("Amount must be numeric.")
        amount = float(amount)
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        return amount

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    @abstractmethod
    def type_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def register(self, account: AbstractAccount) -> bool:
        raise NotImplementedError


class Deposit(AbstractTransaction):
    @property
    def type_name(self) -> str:
        return "deposit"

    def register(self, account: AbstractAccount) -> bool:
        success = account.deposit(self.amount)
        if success:
            account.history.add_transaction(self)
        return success


class Withdrawal(AbstractTransaction):
    @property
    def type_name(self) -> str:
        return "withdrawal"

    def register(self, account: AbstractAccount) -> bool:
        success = account.withdraw(self.amount)
        if success:
            account.history.add_transaction(self)
        return success


class TransactionHistory:
    def __init__(self) -> None:
        self._transactions: List[AbstractTransaction] = []

    @property
    def transactions(self) -> List[AbstractTransaction]:
        return list(self._transactions)

    def add_transaction(self, transaction: AbstractTransaction) -> None:
        self._transactions.append(transaction)

    def transactions_on_date(self, target_date: date) -> List[AbstractTransaction]:
        return [t for t in self._transactions if t.timestamp.date() == target_date]

    def count_withdrawals_on_date(self, target_date: date) -> int:
        return sum(
            1
            for t in self._transactions
            if t.timestamp.date() == target_date and isinstance(t, Withdrawal)
        )


class AbstractAccount(ABC):
    def __init__(self, agency: str, number: int, client: Client) -> None:
        self._agency = self._validate_agency(agency)
        self._number = self._validate_number(number)
        self._client = client
        self._balance = 0.0
        self._history = TransactionHistory()

    @staticmethod
    def _validate_agency(agency: str) -> str:
        if not isinstance(agency, str) or not agency.strip():
            raise ValidationError("Agency must be a non-empty string.")
        return agency.strip()

    @staticmethod
    def _validate_number(number: int) -> int:
        if not isinstance(number, int) or number <= 0:
            raise ValidationError("Account number must be a positive integer.")
        return number

    @property
    def agency(self) -> str:
        return self._agency

    @property
    def number(self) -> int:
        return self._number

    @property
    def client(self) -> Client:
        return self._client

    @property
    def balance(self) -> float:
        return self._balance

    @property
    def history(self) -> TransactionHistory:
        return self._history

    def deposit(self, amount: float) -> bool:
        amount = AbstractTransaction._validate_amount(amount)
        self._balance += amount
        return True

    @abstractmethod
    def withdraw(self, amount: float) -> bool:
        raise NotImplementedError

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(agency={self.agency}, number={self.number}, balance={self.balance:.2f})"


class Account(AbstractAccount):
    def withdraw(self, amount: float) -> bool:
        amount = AbstractTransaction._validate_amount(amount)
        if amount > self.balance:
            raise BusinessRuleError("Insufficient balance.")
        self._balance -= amount
        return True


class CurrentAccount(Account):
    def __init__(
        self,
        agency: str,
        number: int,
        client: Client,
        withdrawal_limit: float = 500.0,
        daily_withdrawal_limit: int = 3,
    ) -> None:
        super().__init__(agency, number, client)
        if withdrawal_limit <= 0:
            raise ValidationError("Withdrawal limit must be greater than zero.")
        if daily_withdrawal_limit <= 0:
            raise ValidationError("Daily withdrawal limit must be greater than zero.")
        self._withdrawal_limit = float(withdrawal_limit)
        self._daily_withdrawal_limit = int(daily_withdrawal_limit)

    @property
    def withdrawal_limit(self) -> float:
        return self._withdrawal_limit

    @property
    def daily_withdrawal_limit(self) -> int:
        return self._daily_withdrawal_limit

    def withdraw(self, amount: float) -> bool:
        amount = AbstractTransaction._validate_amount(amount)
        if amount > self.withdrawal_limit:
            raise BusinessRuleError("Amount exceeds per-withdrawal limit.")
        today_withdrawals = self.history.count_withdrawals_on_date(date.today())
        if today_withdrawals >= self.daily_withdrawal_limit:
            raise BusinessRuleError("Daily withdrawal limit reached.")
        return super().withdraw(amount)


class SavingsAccount(Account):
    def __init__(self, agency: str, number: int, client: Client, minimum_balance: float = 0.0) -> None:
        super().__init__(agency, number, client)
        if minimum_balance < 0:
            raise ValidationError("Minimum balance cannot be negative.")
        self._minimum_balance = float(minimum_balance)

    @property
    def minimum_balance(self) -> float:
        return self._minimum_balance

    def withdraw(self, amount: float) -> bool:
        amount = AbstractTransaction._validate_amount(amount)
        if self.balance - amount < self.minimum_balance:
            raise BusinessRuleError("Withdrawal would violate minimum balance requirement.")
        return super().withdraw(amount)


class Client(ABC):
    def __init__(self, address: str) -> None:
        if not isinstance(address, str) or not address.strip():
            raise ValidationError("Address must be a non-empty string.")
        self._address = address.strip()
        self._accounts: List[AbstractAccount] = []

    @property
    def address(self) -> str:
        return self._address

    @property
    def accounts(self) -> List[AbstractAccount]:
        return list(self._accounts)

    def add_account(self, account: AbstractAccount) -> None:
        if account in self._accounts:
            raise BusinessRuleError("Account already linked to client.")
        self._accounts.append(account)

    def perform_transaction(self, account: AbstractAccount, transaction: AbstractTransaction) -> bool:
        if account not in self._accounts:
            raise BusinessRuleError("Account does not belong to client.")
        return transaction.register(account)


class Individual(Client):
    def __init__(self, name: str, birth_date: str, cpf: str, address: str) -> None:
        super().__init__(address)
        self._name = self._validate_name(name)
        self._birth_date = self._validate_birth_date(birth_date)
        self._cpf = self._validate_cpf(cpf)

    @staticmethod
    def _validate_name(name: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Name must be a non-empty string.")
        return name.strip()

    @staticmethod
    def _validate_birth_date(birth_date: str) -> str:
        if not isinstance(birth_date, str) or not birth_date.strip():
            raise ValidationError("Birth date must be a non-empty string.")
        return birth_date.strip()

    @staticmethod
    def _validate_cpf(cpf: str) -> str:
        if not isinstance(cpf, str):
            raise ValidationError("CPF must be a string.")
        digits = "".join(ch for ch in cpf if ch.isdigit())
        if len(digits) != 11:
            raise ValidationError("CPF must contain 11 digits.")
        if digits == digits[0] * 11:
            raise ValidationError("Invalid CPF.")

        sum1 = sum(int(digits[i]) * (10 - i) for i in range(9))
        check1 = (sum1 * 10) % 11
        check1 = 0 if check1 == 10 else check1
        if check1 != int(digits[9]):
            raise ValidationError("Invalid CPF.")

        sum2 = sum(int(digits[i]) * (11 - i) for i in range(10))
        check2 = (sum2 * 10) % 11
        check2 = 0 if check2 == 10 else check2
        if check2 != int(digits[10]):
            raise ValidationError("Invalid CPF.")

        return digits

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
        return f"Individual(name={self.name}, cpf={self.cpf})"


class Bank:
    def __init__(self) -> None:
        self._clients: List[Individual] = []
        self._accounts: List[AbstractAccount] = []
        self._next_account_number = 1

    @property
    def clients(self) -> List[Individual]:
        return list(self._clients)

    @property
    def accounts(self) -> List[AbstractAccount]:
        return list(self._accounts)

    def find_client_by_cpf(self, cpf: str) -> Optional[Individual]:
        digits = "".join(ch for ch in cpf if ch.isdigit())
        for client in self._clients:
            if client.cpf == digits:
                return client
        return None

    def create_individual_client(self, name: str, birth_date: str, cpf: str, address: str) -> Individual:
        normalized_cpf = "".join(ch for ch in cpf if ch.isdigit())
        if self.find_client_by_cpf(normalized_cpf) is not None:
            raise BusinessRuleError("Client with this CPF already exists.")
        client = Individual(name=name, birth_date=birth_date, cpf=cpf, address=address)
        self._clients.append(client)
        return client

    def create_current_account(
        self,
        client_cpf: str,
        agency: str = "0001",
        withdrawal_limit: float = 500.0,
        daily_withdrawal_limit: int = 3,
    ) -> CurrentAccount:
        client = self.find_client_by_cpf(client_cpf)
        if client is None:
            raise BusinessRuleError("Client not found.")
        account = CurrentAccount(
            agency=agency,
            number=self._next_account_number,
            client=client,
            withdrawal_limit=withdrawal_limit,
            daily_withdrawal_limit=daily_withdrawal_limit,
        )
        client.add_account(account)
        self._accounts.append(account)
        self._next_account_number += 1
        return account

    def create_savings_account(
        self,
        client_cpf: str,
        agency: str = "0001",
        minimum_balance: float = 0.0,
    ) -> SavingsAccount:
        client = self.find_client_by_cpf(client_cpf)
        if client is None:
            raise BusinessRuleError("Client not found.")
        account = SavingsAccount(
            agency=agency,
            number=self._next_account_number,
            client=client,
            minimum_balance=minimum_balance,
        )
        client.add_account(account)
        self._accounts.append(account)
        self._next_account_number += 1
        return account

    def find_account(self, account_number: int) -> Optional[AbstractAccount]:
        for account in self._accounts:
            if account.number == account_number:
                return account
        return None

    def deposit(self, account_number: int, amount: float) -> bool:
        account = self.find_account(account_number)
        if account is None:
            raise BusinessRuleError("Account not found.")
        transaction = Deposit(amount)
        return account.client.perform_transaction(account, transaction)

    def withdraw(self, account_number: int, amount: float) -> bool:
        account = self.find_account(account_number)
        if account is None:
            raise BusinessRuleError("Account not found.")
        transaction = Withdrawal(amount)
        return account.client.perform_transaction(account, transaction)

    def account_statement(self, account_number: int) -> str:
        account = self.find_account(account_number)
        if account is None:
            raise BusinessRuleError("Account not found.")
        lines = [
            f"Agency: {account.agency}",
            f"Account: {account.number}",
            f"Client: {account.client}",
            "Transactions:",
        ]
        if not account.history.transactions:
            lines.append("  No transactions recorded.")
        else:
            for transaction in account.history.transactions:
                lines.append(
                    f"  {transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
                    f"{transaction.type_name} - {transaction.amount:.2f}"
                )
        lines.append(f"Balance: {account.balance:.2f}")
        return "\n".join(lines)


def main() -> None:
    bank = Bank()

    menu = """
[d] Deposit
[w] Withdraw
[n] New client
[c] New current account
[s] New savings account
[e] Statement
[l] List clients
[a] List accounts
[q] Quit
=> """.strip()

    while True:
        option = input(menu + "\n").strip().lower()

        try:
            if option == "d":
                account_number = int(input("Account number: ").strip())
                amount = float(input("Amount: ").strip())
                bank.deposit(account_number, amount)
                print("Deposit completed successfully.")

            elif option == "w":
                account_number = int(input("Account number: ").strip())
                amount = float(input("Amount: ").strip())
                bank.withdraw(account_number, amount)
                print("Withdrawal completed successfully.")

            elif option == "n":
                name = input("Name: ").strip()
                birth_date = input("Birth date: ").strip()
                cpf = input("CPF: ").strip()
                address = input("Address: ").strip()
                client = bank.create_individual_client(name, birth_date, cpf, address)
                print(f"Client created successfully: {client}")

            elif option == "c":
                cpf = input("Client CPF: ").strip()
                account = bank.create_current_account(cpf)
                print(f"Current account created successfully: {account}")

            elif option == "s":
                cpf = input("Client CPF: ").strip()
                minimum_balance_input = input("Minimum balance (default 0): ").strip()
                minimum_balance = float(minimum_balance_input) if minimum_balance_input else 0.0
                account = bank.create_savings_account(cpf, minimum_balance=minimum_balance)
                print(f"Savings account created successfully: {account}")

            elif option == "e":
                account_number = int(input("Account number: ").strip())
                print(bank.account_statement(account_number))

            elif option == "l":
                if not bank.clients:
                    print("No clients registered.")
                else:
                    for client in bank.clients:
                        print(client)

            elif option == "a":
                if not bank.accounts:
                    print("No accounts registered.")
                else:
                    for account in bank.accounts:
                        print(account)

            elif option == "q":
                break

            else:
                print("Invalid option.")

        except (ValidationError, BusinessRuleError, ValueError) as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()