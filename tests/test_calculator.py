from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from calculator import calculate_gpa
from main import Course, app

client = TestClient(app)


def course(credits=3, grade="A+", name="과목"):
    return {"name": name, "credits": credits, "grade": grade}


@pytest.mark.parametrize("courses,average,credits", [
    ([course(3, "A+"), course(1, "B0")], "4.13", "4"),
    ([course(3, "A+"), course(3, "F")], "2.25", "6"),
    ([course(3, "A+"), course(1, "B0"), course(9, "P")], "4.13", "4"),
    ([course(3, "P"), course(1, "P")], None, "0"),
    ([], None, "0"),
    ([course(3, "F")], "0.00", "3"),
    ([course("0.1", "A+"), course("0.2", "B0")], "3.50", "0.3"),
    # 중간 반올림 없이 4.1245를 바로 반올림하면 4.12이다.
    ([course("24.90", "A+"), course("0.10", "A0"), course("75", "A0")], "4.12", "100"),
])
def test_logic_and_api(courses, average, credits):
    expected = {"average": average, "included_credits": credits,
                "status": "empty" if average is None else "ok",
                "message": "계산 대상 없음" if average is None else "계산 완료"}
    assert calculate_gpa("4.5", [Course(**item) for item in courses]) == expected
    response = client.post("/api/calculate", json={"scale": "4.5", "courses": courses})
    assert response.status_code == 200
    assert response.json() == expected


EXPECTED_TABLES = {
    "4.5": {"A+": "4.5", "A0": "4.0", "B+": "3.5", "B0": "3.0", "C+": "2.5", "C0": "2.0", "D+": "1.5", "D0": "1.0", "F": "0"},
    "4.3": {"A+": "4.3", "A0": "4.0", "A-": "3.7", "B+": "3.3", "B0": "3.0", "B-": "2.7", "C+": "2.3", "C0": "2.0", "C-": "1.7", "D+": "1.3", "D0": "1.0", "D-": "0.7", "F": "0"},
}


@pytest.mark.parametrize("scale,grade,score", [
    (scale, grade, score) for scale, table in EXPECTED_TABLES.items() for grade, score in table.items()
])
def test_every_grade(scale, grade, score):
    response = client.post("/api/calculate", json={"scale": scale, "courses": [course(3, grade), course(2, "P")]})
    assert response.status_code == 200
    assert response.json()["average"] == f"{Decimal(score):.2f}"
    assert response.json()["included_credits"] == "3"


@pytest.mark.parametrize("value", [0, -1, "0", "-0.01", "abc", "", "NaN", "Infinity", "-Infinity", "1e99999", "0.001", 101, True, False, None, [], {}])
def test_invalid_credits(value):
    response = client.post("/api/calculate", json={"scale": "4.5", "courses": [course(value)]})
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["field"] == "credits"
    assert error["row"] == 1
    assert "학점" in error["message"]


@pytest.mark.parametrize("field,value", [("name", ""), ("name", "   "), ("name", "가" * 101), ("name", 123), ("grade", ""), ("grade", None), ("grade", "Z"), ("grade", "A-")])
def test_invalid_name_or_grade(field, value):
    item = course()
    item[field] = value
    response = client.post("/api/calculate", json={"scale": "4.5", "courses": [item]})
    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == field


@pytest.mark.parametrize("field", ["name", "credits", "grade"])
def test_missing_course_field(field):
    item = course()
    del item[field]
    response = client.post("/api/calculate", json={"scale": "4.5", "courses": [item]})
    assert response.status_code == 422
    assert response.json()["errors"][0]["row"] == 1


@pytest.mark.parametrize("payload", [None, [], {}, {"scale": "5", "courses": []}, {"scale": "4.5"}, {"scale": "4.5", "courses": None}, {"scale": "4.5", "courses": [None]}, {"scale": "4.5", "courses": [course()] * 1001}])
def test_invalid_request(payload):
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 422
    assert response.json()["message"] == "입력 내용을 확인해 주세요."


def test_malformed_json():
    response = client.post("/api/calculate", content='{broken', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert "요청 형식" in response.json()["errors"][0]["message"]


def test_scale_change_requires_reselection():
    payload = {"scale": "4.3", "courses": [course(3, "A-")]}
    assert client.post("/api/calculate", json=payload).json()["average"] == "3.70"
    payload["scale"] = "4.5"
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 422
    assert "다시 선택" in response.json()["errors"][0]["message"]


def test_grade_table_endpoint():
    response = client.get("/api/grades")
    assert response.status_code == 200
    assert response.json() == {scale: {**table, "P": None} for scale, table in EXPECTED_TABLES.items()}


@pytest.mark.parametrize("path,content_type", [("/", "text/html"), ("/static/styles.css", "text/css"), ("/static/app.js", "javascript")])
def test_served_files(path, content_type):
    response = client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]
    assert response.content
