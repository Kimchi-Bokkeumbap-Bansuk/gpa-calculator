"""실행: python -m uvicorn main:app --reload"""

from decimal import Decimal
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from calculator import GRADE_TABLES, calculate_gpa

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="학점 계산기", description="사용자가 선택한 성적 기준에 따른 학습용 계산기")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


class Course(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    credits: Decimal = Field(gt=0, le=100, decimal_places=2, allow_inf_nan=False)
    grade: str = Field(min_length=1, max_length=2)

    @field_validator("credits", mode="before")
    @classmethod
    def reject_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("학점에는 숫자를 입력해 주세요.")
        return value


class CalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scale: Literal["4.5", "4.3"]
    courses: list[Course] = Field(max_length=1000)


def error_response(errors: list[dict]) -> JSONResponse:
    return JSONResponse(status_code=422, content={
        "message": "입력 내용을 확인해 주세요.", "errors": errors,
    })


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = []
    messages = {
        "name": "과목명을 1~100자로 입력해 주세요.",
        "credits": "학점은 0보다 크고 100 이하인 숫자로, 소수 둘째 자리까지 입력해 주세요.",
        "grade": "성적을 선택해 주세요.",
        "scale": "만점 기준은 4.5 또는 4.3을 선택해 주세요.",
        "courses": "과목 목록을 올바르게 보내 주세요. 최대 1,000개까지 입력할 수 있습니다.",
    }
    for error in exc.errors():
        location = error["loc"]
        field = location[-1]
        row = location[2] + 1 if len(location) > 2 and location[1] == "courses" and isinstance(location[2], int) else None
        message = messages.get(field, "요청 형식이 올바르지 않습니다. 입력 내용을 확인해 주세요.")
        if row:
            message = f"{row}번째 과목: {message}"
        errors.append({"row": row, "field": str(field), "message": message})
    return error_response(errors)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/grades")
def grade_tables():
    return {scale: {**{grade: str(score) for grade, score in table.items()}, "P": None}
            for scale, table in GRADE_TABLES.items()}


@app.post("/api/calculate")
def calculate(payload: CalculationRequest):
    errors = []
    for index, course in enumerate(payload.courses, 1):
        if course.grade not in GRADE_TABLES[payload.scale] and course.grade != "P":
            errors.append({"row": index, "field": "grade", "message":
                f"{index}번째 과목: {payload.scale} 만점에서 사용할 수 없는 성적입니다. 성적을 다시 선택해 주세요."})
    if errors:
        return error_response(errors)
    return calculate_gpa(payload.scale, payload.courses)
