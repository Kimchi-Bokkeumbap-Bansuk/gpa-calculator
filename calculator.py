"""성적 기준과 계산 로직. 마지막 결과에만 일반 반올림을 적용한다."""

from decimal import Decimal, ROUND_HALF_UP, localcontext

GRADE_TABLES = {
    "4.5": dict(zip(
        ["A+", "A0", "B+", "B0", "C+", "C0", "D+", "D0", "F"],
        map(Decimal, ["4.5", "4.0", "3.5", "3.0", "2.5", "2.0", "1.5", "1.0", "0"]),
    )),
    "4.3": dict(zip(
        ["A+", "A0", "A-", "B+", "B0", "B-", "C+", "C0", "C-", "D+", "D0", "D-", "F"],
        map(Decimal, ["4.3", "4.0", "3.7", "3.3", "3.0", "2.7", "2.3", "2.0", "1.7", "1.3", "1.0", "0.7", "0"]),
    )),
}


def calculate_gpa(scale: str, courses: list) -> dict:
    """검증된 과목 목록을 받아 P를 제외하고 F를 포함한 가중평균을 반환한다."""
    with localcontext() as context:
        context.prec = 50
        credits = Decimal("0")
        weighted = Decimal("0")
        for course in courses:
            if course.grade == "P":
                continue
            credits += course.credits
            weighted += course.credits * GRADE_TABLES[scale][course.grade]
        average = (weighted / credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if credits else None
        return {
            "average": str(average) if average is not None else None,
            "included_credits": format(credits.normalize(), "f"),
            "status": "ok" if credits else "empty",
            "message": "계산 완료" if credits else "계산 대상 없음",
        }
