import { buildSetupQuestions, REQUIRED_COLLECTION_FIELDS } from "./config.js";
import { ConfigError, ConflictError, ServiceError } from "./errors.js";
import {
  NotionClient,
  buildEqualsFilter,
  buildPropertyPatch,
  mergeRelationPatch,
  propertyOptionNames,
  readPropertyValue
} from "./notion.js";
import {
  deriveLinkedinSlugTitle,
  mergeText,
  normalizeDomain,
  normalizeEmail,
  normalizeLinkedinUrl,
  normalizeWebsiteUrl,
  nowIso,
  safeTrim
} from "./utils.js";

export class CrmService {
  constructor(config) {
    this.config = config;
    this.notion = new NotionClient(config.notion);
    this.collectionCache = new Map();
  }

  setupQuestions() {
    return buildSetupQuestions(this.config);
  }

  async schemaAudit() {
    if (this.setupQuestions().some((question) => question.status === "missing")) {
      return {
        ok: false,
        ready: false,
        issues: [],
        questions: this.setupQuestions()
      };
    }

    const issues = [];
    for (const collectionName of ["intake", "companies", "contacts"]) {
      const collectionConfig = this.getCollectionConfig(collectionName);
      const collection = await this.getCollection(collectionName);

      if (collection.properties?.[collectionConfig.titleProperty]?.type !== "title") {
        issues.push({
          collection: collectionName,
          property: collectionConfig.titleProperty,
          type: "title-property",
          message: `Expected ${collectionName}.${collectionConfig.titleProperty} to be a title property.`
        });
      }

      for (const logicalField of REQUIRED_COLLECTION_FIELDS[collectionName]) {
        const propertyName = collectionConfig.properties?.[logicalField];
        if (!propertyName) {
          continue;
        }
        if (!collection.properties?.[propertyName]) {
          issues.push({
            collection: collectionName,
            property: propertyName,
            type: "missing-property",
            message: `Notion property "${propertyName}" is missing in ${collectionName}.`
          });
        }
      }

      for (const [key, value] of Object.entries(collectionConfig.selectDefaults ?? {})) {
        const propertyName = selectPropertyForKey(key, collectionConfig);
        if (!propertyName || !collection.properties?.[propertyName]) {
          continue;
        }

        const schema = collection.properties[propertyName];
        const options = propertyOptionNames(schema);
        if (options.length > 0 && !options.includes(value)) {
          issues.push({
            collection: collectionName,
            property: propertyName,
            type: "missing-option",
            message: `Option "${value}" is missing from ${collectionName}.${propertyName}.`
          });
        }
      }
    }

    return {
      ok: issues.length === 0,
      ready: issues.length === 0,
      issues,
      questions: this.setupQuestions()
    };
  }

  async createIntake(input, session) {
    this.assertAuthenticated(session);
    this.assertNoPartnerOnlyEnrichment(input);

    const payload = normalizeIntakeInput(input);
    const collectionConfig = this.getCollectionConfig("intake");
    const collection = await this.getCollection("intake");
    const existing = await this.findUniquePageByCandidates("intake", [
      { logicalField: "linkedinUrl", value: payload.linkedinUrl }
    ]);

    const actorValue = this.resolveActorValue(
      collection,
      collectionConfig.properties.importedBy,
      payload.notionImportedByUserId,
      session.linkedin.profile
    );
    const existingNotes = existing
      ? readPropertyValue(existing, collectionConfig.properties.notes)
      : undefined;

    const notesValue = buildAuditNotes({
      notes: mergeText(existingNotes, payload.notes),
      sessionProfile: session.linkedin.profile,
      includeAuditLine:
        (this.config.crm.storeOperatorIdentity ?? true) && actorValue === undefined
    });

    const title = buildIntakeTitle(payload);
    const properties = {
      [collectionConfig.titleProperty]: buildPropertyPatch(
        collection.properties[collectionConfig.titleProperty],
        title
      )
    };

    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "entityType",
      capitalize(payload.entityType)
    );
    applyMappedValue(properties, collection, collectionConfig.properties, "linkedinUrl", payload.linkedinUrl);
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "source",
      collectionConfig.selectDefaults?.source ?? "LinkedIn"
    );
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "importStatus",
      collectionConfig.selectDefaults?.pendingReview ?? "Pending Review"
    );
    applyMappedValue(properties, collection, collectionConfig.properties, "notes", notesValue);
    applyMappedValue(properties, collection, collectionConfig.properties, "importedBy", actorValue);
    applyMappedValue(properties, collection, collectionConfig.properties, "importedAt", nowIso());
    applyMappedValue(properties, collection, collectionConfig.properties, "lastImportedAt", nowIso());
    applyMappedValue(properties, collection, collectionConfig.properties, "contactName", payload.contactName);
    applyMappedValue(properties, collection, collectionConfig.properties, "companyName", payload.companyName);
    applyMappedValue(properties, collection, collectionConfig.properties, "email", payload.email);
    applyMappedValue(properties, collection, collectionConfig.properties, "website", payload.website);
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "companyLinkedinUrl",
      payload.companyLinkedinUrl
    );
    applyMappedValue(properties, collection, collectionConfig.properties, "owner", payload.ownerId);
    applyMappedValue(properties, collection, collectionConfig.properties, "status", payload.status);

    const page = existing
      ? await this.notion.updatePage(existing.id, properties)
      : await this.notion.createPage(collectionConfig.collectionType, collectionConfig.id, properties);

    return {
      ok: true,
      action: existing ? "updated" : "created",
      intakeId: page.id,
      intakeUrl: page.url,
      entityType: payload.entityType,
      linkedinUrl: payload.linkedinUrl
    };
  }

  async approveIntake(intakeId, input, session) {
    this.assertAuthenticated(session);
    const options = input ?? {};

    const intakeConfig = this.getCollectionConfig("intake");
    const intakeCollection = await this.getCollection("intake");
    const intakePage = await this.notion.retrievePage(intakeId);
    const intake = this.readMappedPage("intake", intakePage);

    if (!intake.linkedinUrl) {
      throw new ServiceError(422, "The intake record is missing a LinkedIn URL.");
    }
    if (!["company", "contact"].includes(intake.entityType)) {
      throw new ServiceError(422, "The intake record is missing a valid entity type.");
    }

    const allowMetadataUpdates =
      options.allowMetadataUpdates ?? this.config.crm.applyMetadataUpdatesOnApprove ?? false;

    let companyResult;
    let contactResult;

    if (intake.entityType === "company") {
      companyResult = await this.upsertCompany(
        {
          companyName: intake.companyName,
          linkedinUrl: intake.linkedinUrl,
          website: intake.website,
          notes: intake.notes,
          ownerId: options.ownerId ?? firstValue(intake.owner),
          status: options.status ?? firstValue(intake.status)
        },
        { allowMetadataUpdates }
      );
    }

    if (intake.entityType === "contact") {
      if (intake.companyLinkedinUrl || intake.companyName || intake.website) {
        companyResult = await this.upsertCompany(
          {
            companyName: intake.companyName,
            linkedinUrl: intake.companyLinkedinUrl,
            website: intake.website,
            notes: intake.notes,
            ownerId: options.ownerId ?? firstValue(intake.owner),
            status: options.status ?? firstValue(intake.status)
          },
          { allowMetadataUpdates }
        );
      }

      contactResult = await this.upsertContact(
        {
          contactName: intake.contactName,
          linkedinUrl: intake.linkedinUrl,
          email: intake.email,
          notes: intake.notes,
          ownerId: options.ownerId ?? firstValue(intake.owner),
          status: options.status ?? firstValue(intake.status),
          companyId: companyResult?.page?.id
        },
        { allowMetadataUpdates }
      );

      if (companyResult?.page?.id && contactResult?.page?.id) {
        await this.linkCompanyAndContact(companyResult.page, contactResult.page);
      }
    }

    const intakeUpdates = {};
    applyMappedValue(
      intakeUpdates,
      intakeCollection,
      intakeConfig.properties,
      "importStatus",
      intakeConfig.selectDefaults?.approved ?? "Approved"
    );
    applyMappedValue(intakeUpdates, intakeCollection, intakeConfig.properties, "lastImportedAt", nowIso());
    applyMappedValue(
      intakeUpdates,
      intakeCollection,
      intakeConfig.properties,
      "approvalNotes",
      safeTrim(options.approvalNotes)
    );

    if (companyResult?.page?.id && intakeConfig.properties.companyRelation) {
      const relationProperty = intakeConfig.properties.companyRelation;
      const mergedRelation = mergeRelationPatch(intakePage, relationProperty, [companyResult.page.id]);
      applyMappedValue(
        intakeUpdates,
        intakeCollection,
        intakeConfig.properties,
        "companyRelation",
        mergedRelation
      );
    }

    if (contactResult?.page?.id && intakeConfig.properties.contactRelation) {
      const relationProperty = intakeConfig.properties.contactRelation;
      const mergedRelation = mergeRelationPatch(intakePage, relationProperty, [contactResult.page.id]);
      applyMappedValue(
        intakeUpdates,
        intakeCollection,
        intakeConfig.properties,
        "contactRelation",
        mergedRelation
      );
    }

    await this.notion.updatePage(intakeId, intakeUpdates);

    return {
      ok: true,
      intakeId,
      company:
        companyResult && {
          id: companyResult.page.id,
          url: companyResult.page.url,
          action: companyResult.action
        },
      contact:
        contactResult && {
          id: contactResult.page.id,
          url: contactResult.page.url,
          action: contactResult.action
        },
      allowMetadataUpdates
    };
  }

  async upsertCompany(input, options = {}) {
    if (!input.linkedinUrl && !input.website) {
      throw new ServiceError(
        422,
        "Company approval requires at least a company LinkedIn URL or website."
      );
    }

    let linkedinUrl;
    let website;
    let domain;
    try {
      linkedinUrl = normalizeLinkedinUrl(input.linkedinUrl, "company");
      website = normalizeWebsiteUrl(input.website);
      domain = normalizeDomain(input.website);
    } catch (error) {
      throw new ServiceError(422, error instanceof Error ? error.message : String(error));
    }
    const companyName =
      safeTrim(input.companyName) ??
      (linkedinUrl ? deriveLinkedinSlugTitle(linkedinUrl, "company") : domain ?? "LinkedIn Company");

    const payload = {
      companyName,
      linkedinUrl,
      website,
      domain,
      notes: safeTrim(input.notes),
      ownerId: safeTrim(input.ownerId),
      status: safeTrim(input.status)
    };

    const collectionConfig = this.getCollectionConfig("companies");
    const collection = await this.getCollection("companies");
    const existing = await this.findUniquePageByCandidates("companies", [
      payload.linkedinUrl && { logicalField: "linkedinUrl", value: payload.linkedinUrl },
      payload.website && { logicalField: "website", value: payload.website },
      payload.domain && { logicalField: "website", value: payload.domain }
    ]);

    const properties = {};
    if (!existing) {
      properties[collectionConfig.titleProperty] = buildPropertyPatch(
        collection.properties[collectionConfig.titleProperty],
        payload.companyName
      );
    }

    applyMappedValue(properties, collection, collectionConfig.properties, "linkedinUrl", payload.linkedinUrl);
    applyMappedValue(properties, collection, collectionConfig.properties, "website", payload.website);
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "source",
      collectionConfig.selectDefaults?.source ?? "LinkedIn"
    );
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "importStatus",
      collectionConfig.selectDefaults?.approved ?? "Approved"
    );
    applyMappedValue(properties, collection, collectionConfig.properties, "lastImportedAt", nowIso());

    if (!existing || options.allowMetadataUpdates) {
      const existingNotes = existing
        ? readPropertyValue(existing, collectionConfig.properties.notes)
        : undefined;
      applyMappedValue(
        properties,
        collection,
        collectionConfig.properties,
        "notes",
        mergeText(existingNotes, payload.notes)
      );
      applyMappedValue(properties, collection, collectionConfig.properties, "owner", payload.ownerId);
      applyMappedValue(properties, collection, collectionConfig.properties, "status", payload.status);
    }

    const page = existing
      ? await this.notion.updatePage(existing.id, properties)
      : await this.notion.createPage(collectionConfig.collectionType, collectionConfig.id, properties);

    return {
      action: existing ? "updated" : "created",
      page
    };
  }

  async upsertContact(input, options = {}) {
    if (!input.linkedinUrl && !input.email) {
      throw new ServiceError(
        422,
        "Contact approval requires at least a contact LinkedIn URL or email."
      );
    }

    let linkedinUrl;
    let email;
    try {
      linkedinUrl = normalizeLinkedinUrl(input.linkedinUrl, "contact");
      email = normalizeEmail(input.email);
    } catch (error) {
      throw new ServiceError(422, error instanceof Error ? error.message : String(error));
    }
    const contactName =
      safeTrim(input.contactName) ??
      (linkedinUrl
        ? deriveLinkedinSlugTitle(linkedinUrl, "contact")
        : email?.split("@")[0]?.replace(/[._-]+/gu, " ") ?? "LinkedIn Contact");

    const payload = {
      contactName,
      linkedinUrl,
      email,
      notes: safeTrim(input.notes),
      ownerId: safeTrim(input.ownerId),
      status: safeTrim(input.status),
      companyId: safeTrim(input.companyId)
    };

    const collectionConfig = this.getCollectionConfig("contacts");
    const collection = await this.getCollection("contacts");
    const existing = await this.findUniquePageByCandidates("contacts", [
      payload.linkedinUrl && { logicalField: "linkedinUrl", value: payload.linkedinUrl },
      payload.email && { logicalField: "email", value: payload.email }
    ]);

    const properties = {};
    if (!existing) {
      properties[collectionConfig.titleProperty] = buildPropertyPatch(
        collection.properties[collectionConfig.titleProperty],
        payload.contactName
      );
    }

    applyMappedValue(properties, collection, collectionConfig.properties, "linkedinUrl", payload.linkedinUrl);
    applyMappedValue(properties, collection, collectionConfig.properties, "email", payload.email);
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "source",
      collectionConfig.selectDefaults?.source ?? "LinkedIn"
    );
    applyMappedValue(
      properties,
      collection,
      collectionConfig.properties,
      "importStatus",
      collectionConfig.selectDefaults?.approved ?? "Approved"
    );
    applyMappedValue(properties, collection, collectionConfig.properties, "lastImportedAt", nowIso());

    if (payload.companyId && collectionConfig.properties.companyRelation) {
      const relationValue = existing
        ? mergeRelationPatch(existing, collectionConfig.properties.companyRelation, [payload.companyId])
        : [payload.companyId];
      applyMappedValue(
        properties,
        collection,
        collectionConfig.properties,
        "companyRelation",
        relationValue
      );
    }

    if (!existing || options.allowMetadataUpdates) {
      const existingNotes = existing
        ? readPropertyValue(existing, collectionConfig.properties.notes)
        : undefined;
      applyMappedValue(
        properties,
        collection,
        collectionConfig.properties,
        "notes",
        mergeText(existingNotes, payload.notes)
      );
      applyMappedValue(properties, collection, collectionConfig.properties, "owner", payload.ownerId);
      applyMappedValue(properties, collection, collectionConfig.properties, "status", payload.status);
    }

    const page = existing
      ? await this.notion.updatePage(existing.id, properties)
      : await this.notion.createPage(collectionConfig.collectionType, collectionConfig.id, properties);

    return {
      action: existing ? "updated" : "created",
      page
    };
  }

  async linkCompanyAndContact(companyPage, contactPage) {
    const companyConfig = this.getCollectionConfig("companies");
    const contactsRelationProperty = companyConfig.properties.contactsRelation;
    if (!contactsRelationProperty) {
      return;
    }

    const companyCollection = await this.getCollection("companies");
    const mergedRelations = mergeRelationPatch(companyPage, contactsRelationProperty, [contactPage.id]);
    const properties = {};
    applyMappedValue(
      properties,
      companyCollection,
      companyConfig.properties,
      "contactsRelation",
      mergedRelations
    );
    await this.notion.updatePage(companyPage.id, properties);
  }

  readMappedPage(collectionName, page) {
    const collectionConfig = this.getCollectionConfig(collectionName);
    const values = {
      title: readPropertyValue(page, collectionConfig.titleProperty)
    };

    for (const [logicalField, propertyName] of Object.entries(collectionConfig.properties ?? {})) {
      values[logicalField] = readPropertyValue(page, propertyName);
    }

    if (!values.companyName && collectionName === "intake" && values.entityType === "company") {
      values.companyName = values.title;
    }
    if (!values.contactName && collectionName === "intake" && values.entityType === "contact") {
      values.contactName = values.title;
    }

    values.entityType = values.entityType ? values.entityType.toLowerCase() : values.entityType;
    return values;
  }

  resolveActorValue(collection, propertyName, notionUserId, sessionProfile) {
    if (!propertyName) {
      return undefined;
    }

    const schema = collection.properties?.[propertyName];
    if (!schema) {
      return undefined;
    }

    if (schema.type === "people" && notionUserId) {
      return [notionUserId];
    }

    const parts = [];
    if (sessionProfile?.name) {
      parts.push(sessionProfile.name);
    }
    if (sessionProfile?.email) {
      parts.push(`<${sessionProfile.email}>`);
    }
    const actorText = parts.join(" ").trim() || sessionProfile?.sub;

    if (schema.type === "email") {
      return sessionProfile?.email;
    }
    if (["rich_text", "title"].includes(schema.type)) {
      return actorText;
    }

    return undefined;
  }

  async findUniquePageByCandidates(collectionName, candidates) {
    const collectionConfig = this.getCollectionConfig(collectionName);
    const collection = await this.getCollection(collectionName);
    const matches = new Map();

    for (const candidate of candidates.filter(Boolean)) {
      const propertyName = collectionConfig.properties?.[candidate.logicalField];
      const schema = propertyName ? collection.properties?.[propertyName] : undefined;
      if (!propertyName || !schema) {
        continue;
      }

      let value = candidate.value;
      if (candidate.logicalField === "website" && schema.type !== "url") {
        value = normalizeDomain(candidate.value);
      }

      const filter = buildEqualsFilter(propertyName, schema, value);
      const results = await this.notion.queryCollection(
        collectionConfig.collectionType,
        collectionConfig.id,
        filter
      );

      for (const page of results) {
        matches.set(page.id, page);
      }
    }

    if (matches.size > 1) {
      throw new ConflictError(
        `Multiple ${collectionName} records matched the same dedupe keys. Resolve duplicates before approving.`,
        {
          collection: collectionName,
          pageIds: [...matches.keys()]
        }
      );
    }

    return matches.values().next().value;
  }

  getCollectionConfig(collectionName) {
    const collectionConfig = this.config.crm?.notion?.[collectionName];
    if (!collectionConfig) {
      throw new ConfigError(`CRM config is missing notion.${collectionName}.`, {
        questions: this.setupQuestions()
      });
    }
    return collectionConfig;
  }

  async getCollection(collectionName) {
    if (this.collectionCache.has(collectionName)) {
      return this.collectionCache.get(collectionName);
    }

    const collectionConfig = this.getCollectionConfig(collectionName);
    if (!collectionConfig.id) {
      throw new ConfigError(`CRM config is missing notion.${collectionName}.id.`, {
        questions: this.setupQuestions()
      });
    }

    const collection = await this.notion.retrieveCollection(
      collectionConfig.collectionType,
      collectionConfig.id
    );
    this.collectionCache.set(collectionName, collection);
    return collection;
  }

  assertAuthenticated(session) {
    if (!session?.linkedin?.accessToken) {
      throw new ServiceError(
        401,
        "LinkedIn authentication is required before intake or approval.",
        {
          next: "/auth/linkedin/start"
        }
      );
    }
  }

  assertNoPartnerOnlyEnrichment(input) {
    if (
      input?.autoEnrich ||
      input?.enrichmentRequested ||
      input?.fetchLinkedinProfile ||
      input?.fetchLinkedinCompany
    ) {
      throw new ServiceError(
        400,
        "Self-serve LinkedIn apps cannot auto-enrich arbitrary third-party leads or companies. This requires partner-level access."
      );
    }
  }
}

function applyMappedValue(properties, collection, propertyMap, logicalField, value) {
  if (value === undefined) {
    return;
  }

  const propertyName = propertyMap?.[logicalField];
  if (!propertyName) {
    return;
  }

  const schema = collection.properties?.[propertyName];
  if (!schema) {
    throw new ConfigError(`Notion property "${propertyName}" is missing from the configured collection.`);
  }

  const patch = buildPropertyPatch(
    {
      ...schema,
      name: propertyName
    },
    value
  );
  if (patch !== undefined) {
    properties[propertyName] = patch;
  }
}

function buildIntakeTitle(payload) {
  const label =
    payload.entityType === "company"
      ? payload.companyName ?? deriveLinkedinSlugTitle(payload.linkedinUrl, "company")
      : payload.contactName ?? deriveLinkedinSlugTitle(payload.linkedinUrl, "contact");
  return `${capitalize(payload.entityType)} Intake - ${label}`;
}

function buildAuditNotes({ notes, sessionProfile, includeAuditLine }) {
  if (!includeAuditLine) {
    return notes;
  }

  const parts = [];
  if (sessionProfile?.name) {
    parts.push(sessionProfile.name);
  }
  if (sessionProfile?.email) {
    parts.push(`<${sessionProfile.email}>`);
  }
  const actor = parts.join(" ").trim();
  if (!actor) {
    return notes;
  }
  return mergeText(notes, `Imported by LinkedIn session: ${actor}`);
}

function normalizeIntakeInput(input) {
  const entityType = safeTrim(input?.entityType)?.toLowerCase();
  if (!["company", "contact"].includes(entityType)) {
    throw new ServiceError(422, 'entityType must be either "company" or "contact".');
  }

  let linkedinUrl;
  let companyLinkedinUrl;
  let website;
  try {
    linkedinUrl = normalizeLinkedinUrl(input.linkedinUrl, entityType);
    companyLinkedinUrl =
      entityType === "company"
        ? linkedinUrl
        : normalizeLinkedinUrl(input.companyLinkedinUrl, "company");
    website = normalizeWebsiteUrl(input.website);
  } catch (error) {
    throw new ServiceError(422, error instanceof Error ? error.message : String(error));
  }

  if (!linkedinUrl) {
    throw new ServiceError(422, "linkedinUrl is required for intake.");
  }

  return {
    entityType,
    linkedinUrl,
    contactName: safeTrim(input.contactName),
    companyName: safeTrim(input.companyName),
    companyLinkedinUrl,
    email: normalizeEmail(input.email),
    website,
    notes: safeTrim(input.notes),
    ownerId: safeTrim(input.ownerId),
    notionImportedByUserId: safeTrim(input.notionImportedByUserId),
    status: safeTrim(input.status)
  };
}

function selectPropertyForKey(key, collectionConfig) {
  if (key === "source") {
    return collectionConfig.properties.source;
  }
  if (["pendingReview", "approved"].includes(key)) {
    return collectionConfig.properties.importStatus;
  }
  return collectionConfig.properties[key];
}

function firstValue(value) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

function capitalize(value) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}
