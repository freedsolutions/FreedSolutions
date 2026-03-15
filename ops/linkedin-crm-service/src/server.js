import http from "node:http";
import { loadConfig } from "./config.js";
import { CrmService } from "./crm.js";
import { ServiceError } from "./errors.js";
import {
  cleanupExpiredMap,
  jsonResponse,
  noContentResponse,
  parseCookies,
  randomToken,
  readJsonBody,
  redirectResponse,
  serializeCookie,
  signValue,
  unsignValue,
  wantsJson
} from "./utils.js";
import {
  buildAuthorizationUrl,
  exchangeAuthorizationCode,
  fetchUserInfo
} from "./linkedin.js";

const SESSION_COOKIE = "linkedin_crm_session";
const AUTH_STATE_TTL_MS = 10 * 60 * 1000;
const SESSION_TTL_MS = 24 * 60 * 60 * 1000;

const config = loadConfig();
const crmService = new CrmService(config);
const sessions = new Map();
const authStates = new Map();

if (config.ephemeralSessionSecret) {
  console.warn(
    "[linkedin-crm-service] SESSION_SECRET is not set. Using an ephemeral secret for this process only."
  );
}

const server = http.createServer(async (request, response) => {
  try {
    cleanupExpiredMap(sessions);
    cleanupExpiredMap(authStates);

    if (applyCors(request, response)) {
      return;
    }

    const requestUrl = new URL(request.url, config.baseUrl ?? `http://${request.headers.host}`);
    const pathname = normalizePath(requestUrl.pathname);
    const session = getSession(request);

    if (request.method === "GET" && pathname === "/") {
      return jsonResponse(response, 200, {
        service: "linkedin-crm-service",
        ready: config.setup.ready,
        setupQuestions: config.setup.questions,
        assumptions: config.setup.assumptions,
        endpoints: [
          "GET /setup/questions",
          "GET /setup/schema-audit",
          "GET /auth/linkedin/start",
          "GET /auth/linkedin/callback",
          "GET /integrations/linkedin/userinfo",
          "POST /crm/linkedin-intake",
          "POST /crm/linkedin-intake/:id/approve"
        ]
      });
    }

    if (request.method === "GET" && pathname === "/setup/questions") {
      return jsonResponse(response, 200, {
        ready: config.setup.ready,
        questions: crmService.setupQuestions(),
        assumptions: config.setup.assumptions
      });
    }

    if (request.method === "GET" && pathname === "/setup/schema-audit") {
      const audit = await crmService.schemaAudit();
      return jsonResponse(response, audit.ok ? 200 : 409, audit);
    }

    if (request.method === "GET" && pathname === "/auth/linkedin/start") {
      assertLinkedInConfigured();
      const state = randomToken(16);
      authStates.set(state, {
        redirectTo: requestUrl.searchParams.get("redirectTo") ?? undefined,
        expiresAt: Date.now() + AUTH_STATE_TTL_MS
      });

      const authUrl = buildAuthorizationUrl({
        clientId: config.linkedin.clientId,
        redirectUri: config.linkedin.redirectUri,
        scopes: config.linkedin.scopes,
        state
      });

      if (wantsJson(requestUrl)) {
        return jsonResponse(response, 200, { authUrl, state });
      }

      return redirectResponse(response, authUrl);
    }

    if (request.method === "GET" && pathname === "/auth/linkedin/callback") {
      assertLinkedInConfigured();
      const providerError = requestUrl.searchParams.get("error");
      if (providerError) {
        throw new ServiceError(400, "LinkedIn authorization failed.", {
          error: providerError,
          errorDescription: requestUrl.searchParams.get("error_description")
        });
      }

      const state = requestUrl.searchParams.get("state");
      const code = requestUrl.searchParams.get("code");
      const stateRecord = state ? authStates.get(state) : undefined;
      if (state) {
        authStates.delete(state);
      }

      if (!state || !stateRecord) {
        throw new ServiceError(400, "Invalid or expired LinkedIn OAuth state.");
      }

      if (!code) {
        throw new ServiceError(400, "LinkedIn callback is missing the authorization code.");
      }

      const tokenResponse = await exchangeAuthorizationCode({
        clientId: config.linkedin.clientId,
        clientSecret: config.linkedin.clientSecret,
        redirectUri: config.linkedin.redirectUri,
        code
      });

      const profile = await fetchUserInfo(tokenResponse.access_token);
      const sessionRecord = createOrRefreshSession(session?.id);
      sessionRecord.linkedin = {
        accessToken: tokenResponse.access_token,
        expiresAt: Date.now() + Number(tokenResponse.expires_in ?? 0) * 1000,
        scope: tokenResponse.scope,
        profile
      };

      const cookie = serializeCookie(
        SESSION_COOKIE,
        signValue(sessionRecord.id, config.sessionSecret),
        {
          maxAge: SESSION_TTL_MS / 1000,
          secure: isSecureRequest(request)
        }
      );

      if (stateRecord.redirectTo) {
        return redirectResponse(response, stateRecord.redirectTo, {
          "Set-Cookie": cookie
        });
      }

      return jsonResponse(
        response,
        200,
        {
          ok: true,
          authenticated: true,
          profile
        },
        {
          "Set-Cookie": cookie
        }
      );
    }

    if (request.method === "GET" && pathname === "/integrations/linkedin/userinfo") {
      if (!session?.linkedin?.accessToken) {
        throw new ServiceError(401, "No active LinkedIn session. Start with /auth/linkedin/start.");
      }

      const profile =
        session.linkedin.expiresAt > Date.now()
          ? session.linkedin.profile
          : await fetchUserInfo(session.linkedin.accessToken);

      session.linkedin.profile = profile;
      return jsonResponse(response, 200, {
        authenticated: true,
        profile
      });
    }

    if (request.method === "POST" && pathname === "/crm/linkedin-intake") {
      const body = await parseBody(request);
      const result = await crmService.createIntake(body, session);
      return jsonResponse(response, 200, result);
    }

    const approveMatch = pathname.match(/^\/crm\/linkedin-intake\/([^/]+)\/approve$/u);
    if (request.method === "POST" && approveMatch) {
      const body = await parseBody(request);
      const result = await crmService.approveIntake(approveMatch[1], body, session);
      return jsonResponse(response, 200, result);
    }

    throw new ServiceError(404, `No route matches ${request.method} ${pathname}`);
  } catch (error) {
    handleError(response, error);
  }
});

server.listen(config.port, () => {
  console.log(
    `[linkedin-crm-service] listening on ${config.baseUrl ?? `http://localhost:${config.port}`}`
  );
});

function normalizePath(pathname) {
  if (!pathname || pathname === "/") {
    return "/";
  }
  return pathname.replace(/\/+$/u, "");
}

function getSession(request) {
  const cookies = parseCookies(request.headers.cookie);
  const sessionId = cookies[SESSION_COOKIE]
    ? unsignValue(cookies[SESSION_COOKIE], config.sessionSecret)
    : undefined;
  if (!sessionId) {
    return undefined;
  }

  const session = sessions.get(sessionId);
  if (!session || session.expiresAt <= Date.now()) {
    sessions.delete(sessionId);
    return undefined;
  }

  session.expiresAt = Date.now() + SESSION_TTL_MS;
  return session;
}

function createOrRefreshSession(existingSessionId) {
  const id = existingSessionId && sessions.has(existingSessionId) ? existingSessionId : randomToken(18);
  const session = {
    id,
    expiresAt: Date.now() + SESSION_TTL_MS
  };
  sessions.set(id, session);
  return session;
}

async function parseBody(request) {
  try {
    return await readJsonBody(request);
  } catch (error) {
    throw new ServiceError(400, error instanceof Error ? error.message : String(error));
  }
}

function applyCors(request, response) {
  if (!config.allowedOrigin) {
    if (request.method === "OPTIONS") {
      noContentResponse(response);
      return true;
    }
    return false;
  }

  response.setHeader("Access-Control-Allow-Origin", config.allowedOrigin);
  response.setHeader("Access-Control-Allow-Credentials", "true");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
  response.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");

  if (request.method === "OPTIONS") {
    noContentResponse(response);
    return true;
  }

  return false;
}

function assertLinkedInConfigured() {
  if (!config.linkedin.clientId || !config.linkedin.clientSecret || !config.linkedin.redirectUri) {
    throw new ServiceError(503, "LinkedIn OAuth is not fully configured yet.", {
      questions: crmService.setupQuestions()
    });
  }
}

function isSecureRequest(request) {
  return request.headers["x-forwarded-proto"] === "https" || request.socket.encrypted;
}

function handleError(response, error) {
  const statusCode = error instanceof ServiceError ? error.status : 500;
  const payload = {
    ok: false,
    error: error instanceof Error ? error.message : "Unknown server error"
  };

  if (error instanceof ServiceError && error.details !== undefined) {
    payload.details = error.details;
  }

  if (!(error instanceof ServiceError)) {
    console.error(error);
  }

  jsonResponse(response, statusCode, payload);
}
