from typing import Optional


def calculate_gpa(math: Optional[float], programming: Optional[float], database: Optional[float]) -> Optional[float]:
    """Calculate GPA from subject grades (0-100 scale → 0.0-4.0 GPA)."""
    grades = [g for g in [math, programming, database] if g is not None]

    if not grades:
        return None

    avg = sum(grades) / len(grades)

    if avg >= 90:
        return 4.0
    elif avg >= 80:
        return 3.0
    elif avg >= 70:
        return 2.0
    elif avg >= 60:
        return 1.0
    else:
        return 0.0
