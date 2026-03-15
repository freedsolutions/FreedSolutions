import test from "node:test";
import assert from "node:assert/strict";
import { buildSetupQuestions } from "../src/config.js";

test("buildSetupQuestions reports missing LinkedIn and Notion config", () => {
  const questions = buildSetupQuestions({
    linkedin: {},
    notion: {},
    crm: {}
  });

  const ids = questions.map((question) => question.id);
  assert(ids.includes("linkedin-client-id"));
  assert(ids.includes("linkedin-client-secret"));
  assert(ids.includes("notion-api-key"));
  assert(ids.includes("intake-id"));
  assert(ids.includes("companies-id"));
  assert(ids.includes("contacts-id"));
});
