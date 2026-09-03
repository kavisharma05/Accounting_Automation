from decimal import Decimal

from app.core.exceptions import ValidationError
from app.models.entities import JournalEntryLine


def validate_balanced_lines(lines: list[JournalEntryLine]) -> None:
    if len(lines) < 2:
        raise ValidationError("Journal entry requires at least two lines")

    total_debit = sum(Decimal(str(line.debit or 0)) for line in lines)
    total_credit = sum(Decimal(str(line.credit or 0)) for line in lines)

    if total_debit != total_credit:
        raise ValidationError(
            f"Debits ({total_debit}) must equal credits ({total_credit})"
        )

    if total_debit == 0:
        raise ValidationError("Journal entry amounts cannot be zero")


def validate_line_amounts(debit: Decimal, credit: Decimal) -> None:
    if debit < 0 or credit < 0:
        raise ValidationError("Debit and credit must be non-negative")
    if debit > 0 and credit > 0:
        raise ValidationError("Line cannot have both debit and credit")
