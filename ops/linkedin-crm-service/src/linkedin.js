import { ServiceError } from "./errors.js";

const LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization";
const LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken";
const LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo";

export function buildAuthorizationUrl({ clientId, redirectUri, scopes, state }) {
  const url = new URL(LINKEDIN_AUTH_URL);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("state", state);
  url.searchParams.set("scope", scopes.join(" "));
  return url.toString();
}

export async function exchangeAuthorizationCode({
  clientId,
  clientSecret,
  redirectUri,
  code
}) {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    client_id: clientId,
    client_secret: clientSecret,
    redirect_uri: redirectUri
  });

  const response = await fetch(LINKEDIN_TOKEN_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body
  });

  const payload = await readJson(response);
  if (!response.ok) {
    throw new ServiceError(
      response.status,
      "LinkedIn token exchange failed.",
      sanitizeProviderError(payload)
    );
  }

  return payload;
}

export async function fetchUserInfo(accessToken) {
  const response = await fetch(LINKEDIN_USERINFO_URL, {
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });

  const payload = await readJson(response);
  if (!response.ok) {
    throw new ServiceError(
      response.status,
      "LinkedIn userinfo request failed.",
      sanitizeProviderError(payload)
    );
  }

  return payload;
}

async function readJson(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    return {
      raw: text
    };
  }
}

function sanitizeProviderError(payload) {
  if (!payload || typeof payload !== "object") {
    return payload;
  }

  const safe = { ...payload };
  delete safe.access_token;
  delete safe.refresh_token;
  return safe;
}
