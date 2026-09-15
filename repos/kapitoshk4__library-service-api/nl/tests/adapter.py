from datetime import date, timedelta
from decimal import Decimal


class ClaudeDriver:
    """Rules are static methods over a borrowing dict; books live in `db`."""

    def __init__(self, module):
        self.m = module

    def _book(self, fee):
        return self.m.db.create_book("T", "A", "c", 5, str(fee))

    def borrowing_price(self, borrow, expected, fee):
        b = self._book(fee)
        return self.m.PaymentCalculator.calculate_payment({
            "book_id": b["id"],
            "borrow_date": borrow.isoformat(),
            "expected_return_date": expected.isoformat(),
        })

    def overdue_fine(self, borrow, expected, actual, fee):
        b = self._book(fee)
        return self.m.PaymentCalculator.calculate_fine({
            "book_id": b["id"],
            "borrow_date": borrow.isoformat(),
            "expected_return_date": expected.isoformat(),
            "actual_return_date": actual.isoformat(),
        })

    # No enum type is defined; the vocabulary is the membership test inside
    # Validators (payment_type in ("PAYMENT","FINE") / status in (...)).
    def payment_type_vocab(self):
        return {"payment", "fine"} if self.m.Validator.validate_payment_type("FINE") else set()

    def payment_status_vocab(self):
        return {t for t in ("pending", "paid", "expired")
                if self.m.Validator.validate_payment_status(t.upper())}

    def borrow_allowed(self, inventory):
        b = self.m.db.create_book("T", "A", "c", inventory, "1.00")
        try:
            self.m.db.create_borrowing(1, b["id"], (date.today() + timedelta(7)).isoformat())
            return True
        except Exception:
            return False


class _Stub:
    """Duck-typed stand-in for gpt's Django model instances: its pricing
    functions only read attributes, never the database."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


class GptDriver:
    """Django, but the rules are module-level pure functions."""

    def __init__(self, module):
        self.m = module

    def _borrowing(self, borrow, expected, fee):
        return _Stub(borrow_date=borrow, expected_return_date=expected,
                     book=_Stub(daily_fee=Decimal(str(fee)), inventory=5))

    def borrowing_price(self, borrow, expected, fee):
        return self.m.calculate_borrowing_amount(self._borrowing(borrow, expected, fee))

    def overdue_fine(self, borrow, expected, actual, fee):
        return self.m.calculate_fine_amount(self._borrowing(borrow, expected, fee), actual)

    # Django TextChoices nested on the model: Payment.Type / Payment.Status
    def payment_type_vocab(self):
        return {str(v.value).lower() for v in self.m.Payment.Type}

    def payment_status_vocab(self):
        return {str(v.value).lower() for v in self.m.Payment.Status}

    def borrow_allowed(self, inventory):
        s = self.m.BorrowingSerializer()
        try:
            s.validate({"book": _Stub(inventory=inventory),
                        "expected_return_date": date.today() + timedelta(7)})
            return True
        except Exception:
            return False


class DeepseekDriver:
    """Django, and the most DB-bound of the four.

    Three contract behaviours are not reachable without a live database:
      * there is no price computation at all outside the request cycle;
      * the fine is computed inside a DRF viewset action, and multiplies a
        separate per-book `fine_per_day` column rather than daily_fee x 2;
      * the stock check calls Book.available_copies(), which runs an ORM query
        (`self.borrowings.filter(...)`) and therefore needs a saved instance.
    The driver builds unsaved model instances and uses the generation's own
    methods where they are callable. The remaining failures are a property of
    where this generation put its logic, not of the harness — recorded here so
    the score is attributable."""

    def __init__(self, module):
        self.m = module

    def _borrowing(self, borrow, expected, fee, actual=None):
        book = self.m.Book(title="T", author="A", inventory=5,
                           daily_fee=Decimal(str(fee)))
        b = self.m.Borrowing(borrow_date=borrow, expected_return_date=expected,
                             actual_return_date=actual)
        b.book = book
        return b

    def borrowing_price(self, borrow, expected, fee):
        b = self._borrowing(borrow, expected, fee)
        calc = getattr(b, "calculate_amount", None) or getattr(b, "total_price", None)
        return Decimal(str(calc() if callable(calc) else 0))

    def overdue_fine(self, borrow, expected, actual, fee):
        b = self._borrowing(borrow, expected, fee, actual)
        if not b.is_overdue:
            return Decimal("0.00")
        return Decimal(str(b.book.fine_per_day)) * Decimal(b.overdue_days())

    def payment_type_vocab(self):
        return {str(t[0]).lower() for t in self.m.Payment.PAYMENT_TYPE_CHOICES}

    def payment_status_vocab(self):
        return {str(t[0]).lower() for t in self.m.Payment.STATUS_CHOICES}

    _tables_ready = False

    def _ensure_tables(self):
        """This repo's loader bootstraps Django but does NOT create tables, so
        the stock check — Book.available_copies() runs an ORM query — needs them
        built once before it can be driven."""
        if DeepseekDriver._tables_ready:
            return
        from django.db import connection
        with connection.schema_editor() as se:
            for model in (self.m.Book, self.m.Borrowing, self.m.Payment):
                try:
                    se.create_model(model)
                except Exception:      # already created by an earlier test
                    pass
        DeepseekDriver._tables_ready = True

    def borrow_allowed(self, inventory):
        self._ensure_tables()
        book = self.m.Book.objects.create(title="T", author="A",
                                          inventory=inventory,
                                          daily_fee=Decimal("1.00"))
        s = self.m.BorrowingCreateSerializer()
        try:
            s.validate({"book": book,
                        "expected_return_date": date.today() + timedelta(7)})
            return True
        except Exception:
            return False


class GeminiDriver:
    """FastAPI: the rules are inline in the endpoint bodies, and the return
    endpoint hardcodes date.today(), so an overdue case is created by dating the
    borrowing into the past rather than by passing a return date."""

    def __init__(self, module):
        self.m = module

    def _reset(self, fee, inventory=5):
        self.m.books_db.clear()
        self.m.borrowings_db.clear()
        self.m.payments_db.clear()
        self.m.books_db[1] = self.m.Book(id=1, title="T", author="A",
                                         inventory=inventory,
                                         daily_fee=float(fee))
        return _Stub(id=1, is_admin=True)

    def borrowing_price(self, borrow, expected, fee):
        user = self._reset(fee)
        days = (expected - borrow).days
        self.m.create_borrowing(self.m.BorrowingCreate(book_id=1, days=days), user)
        return Decimal(str(next(iter(self.m.payments_db.values())).amount))

    def overdue_fine(self, borrow, expected, actual, fee):
        user = self._reset(fee)
        overdue = (actual - expected).days
        self.m.create_borrowing(self.m.BorrowingCreate(book_id=1, days=1), user)
        bid = next(iter(self.m.borrowings_db))
        # the endpoint compares against date.today(), so back-date the due date
        self.m.borrowings_db[bid].expected_return_date = date.today() - timedelta(overdue)
        self.m.payments_db.clear()
        self.m.return_borrowing(bid, user)
        fines = [p for p in self.m.payments_db.values()
                 if str(getattr(p.type, "value", p.type)).lower() == "fine"]
        return Decimal(str(fines[0].amount)) if fines else Decimal("0.00")

    def payment_type_vocab(self):
        return {str(v.value).lower() for v in self.m.PaymentType}

    def payment_status_vocab(self):
        return {str(v.value).lower() for v in self.m.PaymentStatus}

    def borrow_allowed(self, inventory):
        user = self._reset("1.00", inventory=inventory)
        try:
            self.m.create_borrowing(self.m.BorrowingCreate(book_id=1, days=7), user)
            return True
        except Exception:
            return False


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
