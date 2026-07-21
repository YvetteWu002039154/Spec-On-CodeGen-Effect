import datetime
from decimal import Decimal


def _enum_tokens(enum_cls):
    """Member names and (string) values of an enum / Django choices, lowercased."""
    tokens = set()
    for member in enum_cls:
        tokens.add(str(member.name).lower())
        val = getattr(member, "value", None)
        if isinstance(val, str):
            tokens.add(val.lower())
    return tokens


def _future():
    return (datetime.date.today() + datetime.timedelta(days=7)).isoformat()


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def borrowing_price(self, borrow, expected, daily_fee):
        book = self.m.db.create_book("Dune", "Herbert", "HARD", 5, str(daily_fee))
        borrowing = {
            "book_id": book["id"],
            "borrow_date": borrow.isoformat(),
            "expected_return_date": expected.isoformat(),
            "actual_return_date": None,
        }
        return self.m.PaymentCalculator.calculate_payment(borrowing)

    def overdue_fine(self, borrow, expected, actual, daily_fee):
        book = self.m.db.create_book("Dune", "Herbert", "HARD", 5, str(daily_fee))
        borrowing = {
            "book_id": book["id"],
            "borrow_date": borrow.isoformat(),
            "expected_return_date": expected.isoformat(),
            "actual_return_date": actual.isoformat(),
        }
        return self.m.PaymentCalculator.calculate_fine(borrowing)

    def payment_type_vocab(self):
        return _enum_tokens(self.m.PaymentType)

    def payment_status_vocab(self):
        return _enum_tokens(self.m.PaymentStatus)

    def borrow_allowed(self, inventory):
        book = self.m.db.create_book("Dune", "Herbert", "HARD", inventory, "2.00")
        try:
            self.m.db.create_borrowing(1, book["id"], _future())
            return True
        except ValueError:
            return False


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def _borrowing(self, borrow, expected, daily_fee):
        book = self.m.Book(title="Dune", author="Herbert", inventory=5,
                           daily_fee=Decimal(str(daily_fee)))
        return self.m.Borrowing(book=book, borrow_date=borrow,
                                expected_return_date=expected)

    def borrowing_price(self, borrow, expected, daily_fee):
        return self.m.calculate_borrowing_amount(self._borrowing(borrow, expected, daily_fee))

    def overdue_fine(self, borrow, expected, actual, daily_fee):
        return self.m.calculate_fine_amount(self._borrowing(borrow, expected, daily_fee), actual)

    def payment_type_vocab(self):
        return _enum_tokens(self.m.Payment.Type)

    def payment_status_vocab(self):
        return _enum_tokens(self.m.Payment.Status)

    def borrow_allowed(self, inventory):
        self.m.Borrowing.validate_borrowing(inventory)
        return True


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def borrowing_price(self, borrow, expected, daily_fee):
        return self.m.calculate_borrowing_amount(
            self.m.Book(daily_fee=Decimal(str(daily_fee))), borrow, expected)

    def overdue_fine(self, borrow, expected, actual, daily_fee):
        return self.m.calculate_fine_amount(
            self.m.Book(daily_fee=Decimal(str(daily_fee))), expected, actual)

    def payment_type_vocab(self):
        return _enum_tokens(self.m.PaymentType)

    def payment_status_vocab(self):
        return _enum_tokens(self.m.PaymentStatus)

    def borrow_allowed(self, inventory):
        self.m.Borrowing.validate_borrowing(inventory)
        return True


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def borrowing_price(self, borrow, expected, daily_fee):
        return self.m.calculate_borrowing_amount(borrow, expected, daily_fee)

    def overdue_fine(self, borrow, expected, actual, daily_fee):
        return self.m.calculate_fine_amount(borrow, expected, actual, daily_fee)

    def payment_type_vocab(self):
        return _enum_tokens(self.m.PaymentType)

    def payment_status_vocab(self):
        return _enum_tokens(self.m.PaymentStatus)

    def borrow_allowed(self, inventory):
        self.m.Borrowing.validate_borrowing(inventory)
        return True


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
