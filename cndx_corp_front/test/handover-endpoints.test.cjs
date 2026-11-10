const assert = require("node:assert/strict");
const { test } = require("node:test");
const path = require("node:path");
const Module = require("node:module");
const { buildSync } = require("esbuild");

const project = path.resolve(__dirname, "..");
const compiled = buildSync({
  entryPoints: [path.join(project, "app/constants/api-endpoints.ts")],
  bundle: true, platform: "node", format: "cjs", write: false,
});
const endpointsModule = new Module("handover-endpoints");
endpointsModule._compile(compiled.outputFiles[0].text, "handover-endpoints.cjs");
const { API_ENDPOINTS } = endpointsModule.exports;

test("テスト用メールで検索URLを組み立ててもundefinedにならない", () => {
  const params = new URLSearchParams({
    org_id: "TEP", org_type_code: "01", user_role: "0",
    search_query: "handover-99009001@example.invalid", search_type: "email_address",
  });
  const url = new URL(
    `http://localhost:5000${API_ENDPOINTS.CONTACT_PERSON.API_CONTACT_PERSON_SEARCH}?${params}`,
  );
  assert.equal(url.pathname, "/api/contact-person/search");
  assert.equal(url.searchParams.get("search_query"), "handover-99009001@example.invalid");
  assert.equal(url.searchParams.get("search_type"), "email_address");
});

test("引継登録のAPI定義も存在する", () => {
  assert.equal(API_ENDPOINTS.CONTACT_PERSON.API_INDIVIDUAL_HANDOVER,
    "/api/contact-person/individual_handover");
  assert.equal(API_ENDPOINTS.CONTACT_PERSON.API_INCLUSIVE_HANDOVER,
    "/api/contact-person/inclusive_handover");
});
