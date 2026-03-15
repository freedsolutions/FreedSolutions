import test from "node:test";
import assert from "node:assert/strict";
import {
  mergeText,
  normalizeDomain,
  normalizeLinkedinUrl,
  normalizeWebsiteUrl
} from "../src/utils.js";

test("normalizeLinkedinUrl strips query strings and trailing slash", () => {
  const normalized = normalizeLinkedinUrl(
    "https://linkedin.com/in/example-person/?trk=public-profile",
    "contact"
  );

  assert.equal(normalized, "https://www.linkedin.com/in/example-person");
});

test("normalizeWebsiteUrl normalizes protocol and root path", () => {
  assert.equal(normalizeWebsiteUrl("example.com/"), "https://example.com");
  assert.equal(normalizeDomain("https://www.example.com/path"), "example.com");
});

test("mergeText appends only new content", () => {
  assert.equal(mergeText("Existing note", "Existing note"), "Existing note");
  assert.equal(mergeText("Existing note", "New note"), "Existing note\n\nNew note");
});
