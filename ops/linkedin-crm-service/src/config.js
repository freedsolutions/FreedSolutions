import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomToken, loadDotEnv, safeTrim } from "./utils.js";

const SERVICE_ROOT = fileURLToPath(new URL("..", import.meta.url));

export const REQUIRED_COLLECTION_FIELDS = {
  intake: [
    "entityType",
    "linkedinUrl",
    "source",
    "importStatus",
    "notes",
    "importedBy",
    "importedAt"
  ],
  companies: ["linkedinUrl", "source", "importStatus", "lastImportedAt"],
  contacts: ["linkedinUrl", "source", "importStatus", "lastImportedAt", "companyRelation"]
};

export function loadConfig() {
  loadDotEnv(SERVICE_ROOT);

  const configPath = resolveConfigPath(process.env.CRM_CONFIG_PATH);
  const crmConfig = loadCrmConfig(configPath);
  const baseUrl = safeTrim(process.env.APP_BASE_URL);
  const redirectUri =
    safeTrim(process.env.LINKEDIN_REDIRECT_URI) ??
    (baseUrl ? `${baseUrl.replace(/\/$/u, "")}/auth/linkedin/callback` : undefined);

  const config = {
    serviceRoot: SERVICE_ROOT,
    configPath,
    port: Number(process.env.PORT ?? 8787),
    baseUrl,
    allowedOrigin: safeTrim(process.env.ALLOWED_ORIGIN),
    sessionSecret: safeTrim(process.env.SESSION_SECRET) ?? randomToken(32),
    ephemeralSessionSecret: !safeTrim(process.env.SESSION_SECRET),
    linkedin: {
      clientId: safeTrim(process.env.LINKEDIN_CLIENT_ID),
      clientSecret: safeTrim(process.env.LINKEDIN_CLIENT_SECRET),
      redirectUri,
      scopes: (safeTrim(process.env.LINKEDIN_SCOPES) ?? "openid profile email")
        .split(/\s+/u)
        .filter(Boolean)
    },
    notion: {
      apiKey: safeTrim(process.env.NOTION_API_KEY),
      version: safeTrim(process.env.NOTION_VERSION) ?? "2025-09-03"
    },
    crm: crmConfig
  };

  const setupQuestions = buildSetupQuestions(config);
  config.setup = {
    ready: !setupQuestions.some((question) => question.status === "missing"),
    questions: setupQuestions,
    assumptions: {
      auditMode: crmConfig.auditMode ?? "store",
      storeOperatorIdentity: crmConfig.storeOperatorIdentity ?? true,
      applyMetadataUpdatesOnApprove: crmConfig.applyMetadataUpdatesOnApprove ?? false,
      deployment: "Deploy this folder as a private service, not on GitHub Pages."
    }
  };

  return config;
}

function resolveConfigPath(configPath) {
  const candidate = safeTrim(configPath) ?? "./config/crm.config.json";
  return path.isAbsolute(candidate) ? candidate : path.resolve(SERVICE_ROOT, candidate);
}

function loadCrmConfig(configPath) {
  if (!fs.existsSync(configPath)) {
    return {};
  }

  try {
    return JSON.parse(fs.readFileSync(configPath, "utf8"));
  } catch (error) {
    return {
      _parseError: error instanceof Error ? error.message : String(error)
    };
  }
}

export function buildSetupQuestions(config) {
  const questions = [];
  const crmConfig = config.crm ?? {};

  if (crmConfig._parseError) {
    questions.push({
      id: "crm-config-json",
      status: "missing",
      prompt: `Fix JSON parse error in ${config.configPath}: ${crmConfig._parseError}`
    });
  }

  if (!config.linkedin.clientId) {
    questions.push({
      id: "linkedin-client-id",
      status: "missing",
      prompt: "What is the LinkedIn Client ID for this private app?"
    });
  }

  if (!config.linkedin.clientSecret) {
    questions.push({
      id: "linkedin-client-secret",
      status: "missing",
      prompt: "What is the LinkedIn Client Secret for this private app?"
    });
  }

  if (!config.linkedin.redirectUri) {
    questions.push({
      id: "linkedin-redirect-uri",
      status: "missing",
      prompt: "What private host and exact redirect URI should LinkedIn call back to?"
    });
  }

  if (!config.notion.apiKey) {
    questions.push({
      id: "notion-api-key",
      status: "missing",
      prompt: "What Notion integration API key should this service use?"
    });
  }

  for (const collectionName of ["intake", "companies", "contacts"]) {
    const collectionConfig = crmConfig.notion?.[collectionName];
    if (!collectionConfig?.id) {
      questions.push({
        id: `${collectionName}-id`,
        status: "missing",
        prompt: `What is the exact Notion data source or database ID for ${collectionName}?`
      });
    }

    if (!collectionConfig?.titleProperty) {
      questions.push({
        id: `${collectionName}-title-property`,
        status: "missing",
        prompt: `What is the exact title property name for ${collectionName}?`
      });
    }

    for (const logicalField of REQUIRED_COLLECTION_FIELDS[collectionName]) {
      if (!collectionConfig?.properties?.[logicalField]) {
        questions.push({
          id: `${collectionName}-${logicalField}`,
          status: "missing",
          prompt: `What is the exact Notion property name for ${collectionName}.${logicalField}?`
        });
      }
    }
  }

  if (crmConfig.applyMetadataUpdatesOnApprove === undefined) {
    questions.push({
      id: "approve-metadata-policy",
      status: "assumption",
      prompt:
        "Should approval update existing CRM notes and status fields? Default is false so only structural LinkedIn fields are updated."
    });
  }

  if (crmConfig.storeOperatorIdentity === undefined) {
    questions.push({
      id: "operator-identity-policy",
      status: "assumption",
      prompt:
        "Should operator identity be written into Notion for audit? Default is true when a compatible property exists."
    });
  }

  return questions;
}
