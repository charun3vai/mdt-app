from __future__ import annotations
from datetime import date

def calculate_age_display(dob: date, today: date | None = None) -> str:
    today = today or date.today()
    if dob > today:
        return "Invalid DOB"
    # months
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    # compute months precisely
    months_total = (today.year - dob.year) * 12 + (today.month - dob.month) - (1 if today.day < dob.day else 0)
    if years < 1:
        months = max(0, months_total)
        return f"{months} months"
    if years < 5:
        remaining_months = months_total - years * 12
        return f"{years} years {remaining_months} months"
    return f"{years} years"
