const assert = require("node:assert/strict");
const { test } = require("node:test");
const path = require("node:path");
const Module = require("node:module");
const { buildSync } = require("esbuild");

const project = path.resolve(__dirname, "..");
const compiled = buildSync({
  entryPoints: [path.join(project, "app/lib/validations/mgmg03.ts")],
  bundle: true, platform: "node", format: "cjs", write: false,
  tsconfig: path.join(project, "tsconfig.json"),
});
const validationModule = new Module("handover-validation");
validationModule._compile(compiled.outputFiles[0].text, "handover-validation.cjs");
const { canRegisterHandover, canTransferReportData, isFutureHandoverDate,
  handoverSearchResponseSchema } = validationModule.exports;

test("引継はEP管理者・本店管理者のみ利用できる", () => {
  for (const orgType of ["01", "02", "03", "04", "05", "06"]) {
    for (const role of ["0", "1", "9"]) {
      assert.equal(canRegisterHandover({ org_type_code: orgType, role }),
        (orgType === "01" && role === "0") || (orgType === "02" && role === "9"));
    }
  }
  assert.equal(canRegisterHandover(undefined), false);
});

test("異なるBNK組織間でのみ過去データを引き継げる", () => {
  assert.equal(canTransferReportData("BNK0001", "BNK0002"), true);
  for (const [from, to] of [["", ""], ["BNK0001", "BNK0001"],
    ["TCS0001", "BNK0002"], ["BNK0001", "REP0002"]]) {
    assert.equal(canTransferReportData(from, to), false);
  }
});

test("実施日は有効な未来日のみ許可し、当日・過去・存在しない日を拒否する", () => {
  const today = new Date(2026, 10, 4, 12);
  assert.equal(isFutureHandoverDate("2026/11/05", today), true);
  assert.equal(isFutureHandoverDate("2028/02/29", today), true);
  for (const date of ["", "20261105", "2026-11-05", "2026/11/04", "2026/11/03",
    "2027/02/29", "2026/11/31", "2026/13/01", "2026/1/05"]) {
    assert.equal(isFutureHandoverDate(date, today), false, date);
  }
});

test("検索結果はAPI-04の契約で検証し、壊れた応答を空結果と扱わない", () => {
  const manager = { email_address: "sales@example.com", company_name: "組織A",
    org_id: "BNK0001", user_name: "担当者A", user_id: "00000001" };
  assert.equal(handoverSearchResponseSchema.safeParse({ manager_list: [manager] }).success, true);
  assert.equal(handoverSearchResponseSchema.safeParse({ manager_list: [] }).success, true);
  for (const response of [null, {}, { message: "error" },
    { manager_list: [{ ...manager, user_id: "" }] }]) {
    assert.equal(handoverSearchResponseSchema.safeParse(response).success, false);
  }
});
