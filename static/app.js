"use strict";

const form = document.querySelector("#calculator");
const controls = document.querySelector("#controls");
const list = document.querySelector("#course-list");
const scale = document.querySelector("#scale");
const errors = document.querySelector("#errors");
const notice = document.querySelector("#scale-notice");
let tables = {};
let nextId = 0;

function clearErrors() {
  errors.hidden = true;
  errors.replaceChildren();
  list.querySelectorAll("[aria-invalid]").forEach((element) => element.removeAttribute("aria-invalid"));
}

function resetResult() {
  document.querySelector("#average").textContent = "—";
  document.querySelector("#included-credits").textContent = "—";
  document.querySelector("#result-scale").textContent = `/ ${scale.value}`;
  document.querySelector("#result-status").textContent = "현재 입력으로 계산해 주세요.";
}

function fillGrades(select, previous = "") {
  select.replaceChildren(new Option("선택", ""));
  for (const grade of Object.keys(tables[scale.value])) {
    select.add(new Option(grade, grade));
  }
  select.value = Object.hasOwn(tables[scale.value], previous) ? previous : "";
}

function updateRowLabels() {
  [...list.children].forEach((row, index) => {
    row.querySelector("label").textContent = `과목명 ${index + 1}`;
    row.querySelector(".remove-button").setAttribute("aria-label", `${index + 1}번째 과목 삭제`);
  });
  document.querySelector("#empty-list").hidden = list.children.length !== 0;
}

function addCourse(focus = true) {
  const id = ++nextId;
  const row = document.createElement("div");
  row.className = "course-row";
  // 이 HTML에는 사용자 입력을 넣지 않는다. 과목명은 input.value로만 다룬다.
  row.innerHTML = `
    <div class="course-field"><label for="name-${id}">과목명</label><input id="name-${id}" name="name" placeholder="예: 글쓰기" maxlength="100" required></div>
    <div class="course-field"><label for="credits-${id}">학점</label><input id="credits-${id}" name="credits" type="number" inputmode="decimal" min="0.01" max="100" step="0.01" placeholder="3" required></div>
    <div class="course-field"><label for="grade-${id}">성적</label><select id="grade-${id}" name="grade" required></select></div>
    <button class="remove-button" type="button" title="과목 삭제">×</button>`;
  fillGrades(row.querySelector("select"));
  row.querySelector(".remove-button").addEventListener("click", () => {
    const focusTarget = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    updateRowLabels();
    clearErrors();
    updateScaleNotice();
    resetResult();
    (focusTarget?.querySelector("input") || document.querySelector("#add-course")).focus();
  });
  list.append(row);
  updateRowLabels();
  resetResult();
  if (focus) row.querySelector("input").focus();
}

function renderTable() {
  const labels = document.querySelector("#grade-labels");
  const values = document.querySelector("#grade-values");
  labels.innerHTML = '<th scope="row">성적</th>';
  values.innerHTML = '<th scope="row">점수</th>';
  for (const [grade, score] of Object.entries(tables[scale.value])) {
    const label = document.createElement("th");
    label.scope = "col";
    label.textContent = grade;
    const value = document.createElement("td");
    value.textContent = score === null ? "제외" : Number(score).toFixed(1);
    labels.append(label);
    values.append(value);
  }
  document.querySelector("#table-label").textContent = `${scale.value} 만점 기준`;
}

function updateScaleNotice() {
  const invalid = [...list.children].flatMap((row, index) => row.querySelector("select").dataset.reselect ? [index + 1] : []);
  notice.hidden = invalid.length === 0;
  notice.textContent = `${invalid.join(", ")}번째 과목의 기존 성적은 ${scale.value} 만점에서 사용할 수 없습니다. 성적을 다시 선택해 주세요.`;
}

scale.addEventListener("change", () => {
  clearErrors();
  list.querySelectorAll("select").forEach((select) => {
    const previous = select.value;
    fillGrades(select, previous);
    if (previous && !select.value) select.dataset.reselect = "true";
    if (select.dataset.reselect) select.setAttribute("aria-invalid", "true");
  });
  updateScaleNotice();
  renderTable();
  resetResult();
});

list.addEventListener("input", (event) => {
  clearErrors();
  if (event.target.name === "grade" && event.target.value) delete event.target.dataset.reselect;
  updateScaleNotice();
  resetResult();
});
document.querySelector("#add-course").addEventListener("click", () => { clearErrors(); addCourse(); });

function showErrors(items) {
  errors.replaceChildren();
  items.forEach((item) => {
    const message = document.createElement("p");
    message.textContent = item.message;
    errors.append(message);
    const row = list.children[item.row - 1];
    if (row && ["name", "credits", "grade"].includes(item.field)) {
      row.querySelector(`[name="${item.field}"]`).setAttribute("aria-invalid", "true");
    }
  });
  errors.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();
  resetResult();
  const courses = [...list.children].map((row) => ({
    name: row.querySelector('[name="name"]').value.trim(),
    credits: row.querySelector('[name="credits"]').value,
    grade: row.querySelector('[name="grade"]').value,
  }));
  controls.disabled = true;
  form.setAttribute("aria-busy", "true");
  document.querySelector("#calculate").textContent = "계산 중…";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch("/api/calculate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scale: scale.value, courses }), signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) {
      showErrors(data.errors || [{ message: "계산을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요." }]);
      return;
    }
    document.querySelector("#average").textContent = data.average ?? "—";
    document.querySelector("#included-credits").textContent = `${data.included_credits} 학점`;
    document.querySelector("#result-status").textContent = data.message;
  } catch {
    showErrors([{ message: "서버에 연결하지 못했습니다. 터미널에서 서버가 실행 중인지 확인한 뒤 다시 계산해 주세요." }]);
  } finally {
    clearTimeout(timeout);
    controls.disabled = false;
    form.removeAttribute("aria-busy");
    document.querySelector("#calculate").textContent = "평균평점 계산하기 ↗";
    if (!errors.hidden) errors.focus();
  }
});

async function initialize() {
  const loading = document.querySelector("#loading");
  const retry = document.querySelector("#retry");
  loading.textContent = "성적 기준을 불러오는 중입니다…";
  retry.hidden = true;
  try {
    const response = await fetch("/api/grades", { signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error("성적표 요청 실패");
    tables = await response.json();
    addCourse(false);
    addCourse(false);
    renderTable();
    controls.disabled = false;
    loading.hidden = true;
  } catch {
    loading.textContent = "성적 기준을 불러오지 못했습니다. 서버 실행 상태를 확인하고 다시 시도해 주세요.";
    retry.hidden = false;
  }
}
document.querySelector("#retry").addEventListener("click", initialize);
initialize();
