from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

class Client:
    def __init__(self, name: str):
        self._name = name
        self._accounts: List['AbstractAccount'] = []

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    def add_account(self, account: 'AbstractAccount'):
        self._accounts.append(account)

    @property
    def accounts(self) -> List['AbstractAccount']:
        return list(self._accounts)

    def __str__(self):
        return f"Client: {self._name}"


class Individual(Client):
    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        # Remove non-digit characters
        digits = ''.join(filter(str.isdigit, cpf))
        if len(digits) != 11:
            return False
        if digits == digits[0] * 11:
            return False
        # Calculate first check digit
        sum1 = 0
        for i in range(9):
            sum1 += int(digits[i]) * (10 - i)
        remainder1 = sum1 % 11
        check1 = 0 if remainder1 < 2 else 11 - remainder1
        if int(digits[9]) != check1:
            return False
        # Calculate second check digit
        sum2 = 0
        for i in range(10):
            sum2 += int(digits[i]) * (11 - i)
        remainder2 = sum2 % 11
        check2 = 0 if remainder2 < 2 else 11 - remainder2
        return int(digits[10]) == check2

    def __init__(self, name: str, cpf: str):
        super().__init__(name)
        if not self.validate_cpf(cpf):
            raise ValueError("Invalid CPF")
        self._cpf = ''.join(filter(str.isdigit, cpf))

    @property
    def cpf(self) -> str:
        return self._cpf

    def __str__(self):
        return f"Individual: {self._name} (CPF: {self._cpf})"


class AbstractAccount(ABC):
    def __init__(self, agency: str, number: int, client: Client):
        self._agency = agency
        self._number = number
        self._client = client
        self._balance = 0.0
        self._transactions: List['AbstractTransaction'] = []
        client.add_account(self)

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
    def transactions(self) -> List['AbstractTransaction']:
        return list(self._transactions)

    def deposit(self, value: float):
        if value <= 0:
            raise ValueError("Deposit value must be positive.")
        trx = Deposit(value)
        trx.register(self)

    def withdraw(self, value: float):
        if value <= 0:
            raise ValueError("Withdrawal value must be positive.")
        trx = Withdrawal(value)
        trx.register(self)

    def _add_transaction(self, transaction: 'AbstractTransaction'):
        self._transactions.append(transaction)

    def _update_balance(self, amount: float):
        self._balance += amount

    @abstractmethod
    def can_withdraw(self, value: float) -> bool:
        pass

    def __str__(self):
        return f"Account {self._number} (Agency: {self._agency}) - Balance: {self._balance:.2f}"


class CurrentAccount(AbstractAccount):
    DAILY_WITHDRAWAL_LIMIT = 500.0

    def __init__(self, agency: str, number: int, client: Client):
        super().__init__(agency, number, client)

    def can_withdraw(self, value: float) -> bool:
        if value > self._balance:
            return False
        today = datetime.now().date()
        total_today = sum(
            t._value for t in self._transactions
            if isinstance(t, Withdrawal) and t._date.date() == today
        )
        return (total_today + value) <= self.DAILY_WITHDRAWAL_LIMIT

    def __str__(self):
        return f"Current{super().__str__()}"


class SavingsAccount(AbstractAccount):
    MAX_DAILY_WITHDRAWALS = 3

    def __init__(self, agency: str, number: int, client: Client):
        super().__init__(agency, number, client)

    def can_withdraw(self, value: float) -> bool:
        if value > self._balance:
            return False
        today = datetime.now().date()
        count_today = sum(
            1 for t in self._transactions
            if isinstance(t, Withdrawal) and t._date.date() == today
        )
        return count_today < self.MAX_DAILY_WITHDRAWALS

    def __str__(self):
        return f"Savings{super().__str__()}"


class AbstractTransaction(ABC):
    def __init__(self, value: float):
        self._value = value
        self._date = datetime.now()

    @property
    def value(self) -> float:
        return self._value

    @property
    def date(self) -> datetime:
        return self._date

    @abstractmethod
    def register(self, account: AbstractAccount):
        pass

    def __str__(self):
        return f"{self.__class__.__name__} of {self._value:.2f} on {self._date.strftime('%Y-%m-%d %H:%M:%S')}"


class Deposit(AbstractTransaction):
    def register(self, account: AbstractAccount):
        account._update_balance(self._value)
        account._add_transaction(self)


class Withdrawal(AbstractTransaction):
    def register(self, account: AbstractAccount):
        if not account.can_withdraw(self._value):
            raise ValueError(
                "Withdrawal denied: insufficient funds or limit exceeded."
            )
        account._update_balance(-self._value)
        account._add_transaction(self)


def find_client_by_cpf(clients: List[Client], cpf: str) -> Individual:
    cpf_clean = ''.join(filter(str.isdigit, cpf))
    for c in clients:
        if isinstance(c, Individual) and c.cpf == cpf_clean:
            return c
    return None

def find_account_by_number(clients: List[Client], number: int) -> AbstractAccount:
    for c in clients:
        for acc in c.accounts:
            if acc.number == number:
                return acc
    return None

def main():
    clients: List[Client] = []
    agency = "0001"
    next_account_number = 1

    print("=== Banking System ===")
    while True:
        print("\n1. Create client (Individual)")
        print("2. Create account")
        print("3. Deposit")
        print("4. Withdraw")
        print("5. Balance")
        print("6. Statement")
        print("7. Exit")
        option = input("Choose an option: ").strip()

        try:
            if option == '1':
                name = input("Name: ").strip()
                cpf = input("CPF: ").strip()
                client = Individual(name, cpf)
                clients.append(client)
                print(f"Client created: {client}")

            elif option == '2':
                cpf = input("Enter CPF of client: ").strip()
                client = find_client_by_cpf(clients, cpf)
                if not client:
                    print("Client not found.")
                    continue
                acc_type = input("Account type (current/savings): ").strip().lower()
                if acc_type not in ('current', 'savings'):
                    print("Invalid type.")
                    continue
                if acc_type == 'current':
                    acc = CurrentAccount(agency, next_account_number, client)
                else:
                    acc = SavingsAccount(agency, next_account_number, client)
                next_account_number += 1
                print(f"Account created: {acc}")

            elif option == '3':
                cpf_or_acc = input("Enter CPF or account number: ").strip()
                if cpf_or_acc.isdigit():
                    acc = find_account_by_number(clients, int(cpf_or_acc))
                else:
                    client = find_client_by_cpf(clients, cpf_or_acc)
                    if client:
                        print("Accounts:")
                        for a in client.accounts:
                            print(f"  {a.number} - {a.__class__.__name__}")
                        acc_num = input("Choose account number: ").strip()
                        acc = find_account_by_number(clients, int(acc_num))
                    else:
                        acc = None
                if not acc:
                    print("Account not found.")
                    continue
                amount = float(input("Deposit amount: ").strip())
                acc.deposit(amount)
                print(f"Deposit successful. New balance: {acc.balance:.2f}")

            elif option == '4':
                cpf_or_acc = input("Enter CPF or account number: ").strip()
                if cpf_or_acc.isdigit():
                    acc = find_account_by_number(clients, int(cpf_or_acc))
                else:
                    client = find_client_by_cpf(clients, cpf_or_acc)
                    if client:
                        print("Accounts:")
                        for a in client.accounts:
                            print(f"  {a.number} - {a.__class__.__name__}")
                        acc_num = input("Choose account number: ").strip()
                        acc = find_account_by_number(clients, int(acc_num))
                    else:
                        acc = None
                if not acc:
                    print("Account not found.")
                    continue
                amount = float(input("Withdrawal amount: ").strip())
                acc.withdraw(amount)
                print(f"Withdrawal successful. New balance: {acc.balance:.2f}")

            elif option == '5':
                cpf_or_acc = input("Enter CPF or account number: ").strip()
                if cpf_or_acc.isdigit():
                    acc = find_account_by_number(clients, int(cpf_or_acc))
                else:
                    client = find_client_by_cpf(clients, cpf_or_acc)
                    if client:
                        print("Accounts:")
                        for a in client.accounts:
                            print(f"  {a.number} - Balance: {a.balance:.2f}")
                        continue
                    else:
                        acc = None
                if acc:
                    print(f"Account {acc.number} balance: {acc.balance:.2f}")

            elif option == '6':
                cpf_or_acc = input("Enter CPF or account number: ").strip()
                if cpf_or_acc.isdigit():
                    acc = find_account_by_number(clients, int(cpf_or_acc))
                else:
                    client = find_client_by_cpf(clients, cpf_or_acc)
                    if client:
                        print("Accounts:")
                        for a in client.accounts:
                            print(f"  {a.number} - {a.__class__.__name__}")
                        acc_num = input("Choose account number: ").strip()
                        acc = find_account_by_number(clients, int(acc_num))
                    else:
                        acc = None
                if not acc:
                    print("Account not found.")
                    continue
                print(f"Statement for account {acc.number}:")
                if not acc.transactions:
                    print("No transactions.")
                else:
                    for t in acc.transactions:
                        print(f"  {t}")

            elif option == '7':
                print("Exiting...")
                break

            else:
                print("Invalid option.")

        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()