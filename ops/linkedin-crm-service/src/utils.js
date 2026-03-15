import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const DOT_ENV_LINE = /^\s*([\w.-]+)\s*=\s*(.*)?\s*$/;

export function loadDotEnv(baseDir) {
  const envPath = path.join(baseDir, ".env");
  if (!fs.existsSync(envPath)) {
    return;
  }

  const lines = fs.readFileSync(envPath, "utf8").split(/\r?\n/u);
  for (const line of lines) {
    if (!line || line.trim().startsWith("#")) {
      continue;
    }
    const match = line.match(DOT_ENV_LINE);
    if (!match) {
      continue;
    }

    const [, key, rawValue = ""] = match;
    if (process.env[key] !== undefined) {
      continue;
    }

    let value = rawValue.trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    process.env[key] = value;
  }
}

export function randomToken(bytes = 24) {
  return crypto.randomBytes(bytes).toString("hex");
}

export function signValue(value, secret) {
  const signature = crypto.createHmac("sha256", secret).update(value).digest("base64url");
  return `${value}.${signature}`;
}

export function unsignValue(signedValue, secret) {
  const boundary = signedValue.lastIndexOf(".");
  if (boundary <= 0) {
    return undefined;
  }

  const value = signedValue.slice(0, boundary);
  const provided = signedValue.slice(boundary + 1);
  const expected = crypto.createHmac("sha256", secret).update(value).digest("base64url");

  const providedBuffer = Buffer.from(provided);
  const expectedBuffer = Buffer.from(expected);
  if (
    providedBuffer.length !== expectedBuffer.length ||
    !crypto.timingSafeEqual(providedBuffer, expectedBuffer)
  ) {
    return undefined;
  }

  return value;
}

export function nowIso() {
  return new Date().toISOString();
}

export function safeTrim(value) {
  if (value === undefined || value === null) {
    return undefined;
  }
  const trimmed = String(value).trim();
  return trimmed ? trimmed : undefined;
}

export function normalizeEmail(value) {
  const trimmed = safeTrim(value);
  return trimmed ? trimmed.toLowerCase() : undefined;
}

export function normalizeLinkedinUrl(value, entityType = undefined) {
  const trimmed = safeTrim(value);
  if (!trimmed) {
    return undefined;
  }

  let url;
  try {
    url = new URL(trimmed);
  } catch {
    throw new Error(`Invalid LinkedIn URL: ${trimmed}`);
  }

  const host = url.hostname.toLowerCase();
  if (!host.endsWith("linkedin.com")) {
    throw new Error(`LinkedIn URLs must use a linkedin.com hostname: ${trimmed}`);
  }

  url.protocol = "https:";
  url.hostname = "www.linkedin.com";
  url.search = "";
  url.hash = "";

  const segments = url.pathname.split("/").filter(Boolean);
  if (!segments.length) {
    throw new Error(`LinkedIn URL must include a member or company path: ${trimmed}`);
  }

  if (entityType === "contact" && segments[0] !== "in") {
    throw new Error(`Contact intake expects a LinkedIn profile URL under /in/: ${trimmed}`);
  }

  if (entityType === "company" && !["company", "school", "showcase"].includes(segments[0])) {
    throw new Error(`Company intake expects a LinkedIn company-style URL: ${trimmed}`);
  }

  url.pathname = `/${segments.join("/")}`;
  return url.toString().replace(/\/$/u, "");
}

export function normalizeWebsiteUrl(value) {
  const trimmed = safeTrim(value);
  if (!trimmed) {
    return undefined;
  }

  const withProtocol = /^[a-z]+:\/\//iu.test(trimmed) ? trimmed : `https://${trimmed}`;
  let url;
  try {
    url = new URL(withProtocol);
  } catch {
    throw new Error(`Invalid website URL: ${trimmed}`);
  }

  url.protocol = "https:";
  url.hash = "";
  url.search = "";
  url.pathname = url.pathname === "/" ? "" : url.pathname.replace(/\/+$/u, "");
  return url.toString().replace(/\/$/u, "");
}

export function normalizeDomain(value) {
  const normalizedUrl = normalizeWebsiteUrl(value);
  if (!normalizedUrl) {
    return undefined;
  }

  const hostname = new URL(normalizedUrl).hostname.toLowerCase();
  return hostname.startsWith("www.") ? hostname.slice(4) : hostname;
}

export function deriveLinkedinSlugTitle(linkedinUrl, entityType) {
  const normalized = normalizeLinkedinUrl(linkedinUrl, entityType);
  const pathname = new URL(normalized).pathname;
  const slug = pathname.split("/").filter(Boolean).at(-1) ?? "linkedin-record";
  return slug
    .split(/[-_]+/u)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function mergeText(existingText, incomingText) {
  const existing = safeTrim(existingText);
  const incoming = safeTrim(incomingText);
  if (!existing) {
    return incoming;
  }
  if (!incoming || existing.includes(incoming)) {
    return existing;
  }
  return `${existing}\n\n${incoming}`;
}

export function uniqueIds(values) {
  return [...new Set((values ?? []).filter(Boolean))];
}

export function splitRichText(text, chunkSize = 1900) {
  const value = safeTrim(text);
  if (!value) {
    return [];
  }

  const chunks = [];
  for (let index = 0; index < value.length; index += chunkSize) {
    chunks.push(value.slice(index, index + chunkSize));
  }
  return chunks;
}

export function parseCookies(headerValue) {
  const cookies = {};
  if (!headerValue) {
    return cookies;
  }

  for (const pair of headerValue.split(";")) {
    const [name, ...rest] = pair.split("=");
    if (!name) {
      continue;
    }
    cookies[name.trim()] = decodeURIComponent(rest.join("="));
  }
  return cookies;
}

export function serializeCookie(name, value, options = {}) {
  const parts = [`${name}=${encodeURIComponent(value)}`];
  if (options.httpOnly !== false) {
    parts.push("HttpOnly");
  }
  if (options.maxAge) {
    parts.push(`Max-Age=${Math.floor(options.maxAge)}`);
  }
  parts.push(`Path=${options.path ?? "/"}`);
  parts.push(`SameSite=${options.sameSite ?? "Lax"}`);
  if (options.secure) {
    parts.push("Secure");
  }
  return parts.join("; ");
}

export function cleanupExpiredMap(map, now = Date.now()) {
  for (const [key, value] of map.entries()) {
    if (value?.expiresAt && value.expiresAt <= now) {
      map.delete(key);
    }
  }
}

export async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(Buffer.from(chunk));
  }

  if (chunks.length === 0) {
    return {};
  }

  const raw = Buffer.concat(chunks).toString("utf8");
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error("Request body must be valid JSON.");
  }
}

export function jsonResponse(response, statusCode, payload, headers = {}) {
  const body = JSON.stringify(payload, null, 2);
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    ...headers
  });
  response.end(body);
}

export function redirectResponse(response, location, headers = {}) {
  response.writeHead(302, {
    Location: location,
    ...headers
  });
  response.end();
}

export function noContentResponse(response, headers = {}) {
  response.writeHead(204, headers);
  response.end();
}

export function wantsJson(requestUrl) {
  return requestUrl.searchParams.get("format") === "json";
}
