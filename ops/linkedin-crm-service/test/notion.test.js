import test from "node:test";
import assert from "node:assert/strict";
import { buildEqualsFilter, buildPropertyPatch } from "../src/notion.js";

test("buildPropertyPatch handles relation and title properties", () => {
  const titlePatch = buildPropertyPatch({ type: "title", name: "Name" }, "Example Company");
  const relationPatch = buildPropertyPatch({ type: "relation", name: "Company" }, ["abc", "def"]);

  assert.equal(titlePatch.title[0].text.content, "Example Company");
  assert.deepEqual(relationPatch.relation, [{ id: "abc" }, { id: "def" }]);
});

test("buildEqualsFilter supports URL properties", () => {
  const filter = buildEqualsFilter(
    "LinkedIn URL",
    { type: "url", name: "LinkedIn URL" },
    "https://www.linkedin.com/company/example"
  );

  assert.deepEqual(filter, {
    property: "LinkedIn URL",
    url: {
      equals: "https://www.linkedin.com/company/example"
    }
  });
});
