import { ServiceError } from "./errors.js";
import { splitRichText, uniqueIds } from "./utils.js";

export class NotionClient {
  constructor({ apiKey, version }) {
    this.apiKey = apiKey;
    this.version = version;
  }

  async retrieveCollection(collectionType, id) {
    return this.request("GET", collectionPath(collectionType, id));
  }

  async queryCollection(collectionType, id, filter = undefined) {
    const results = [];
    let nextCursor = undefined;

    do {
      const payload = await this.request("POST", `${collectionPath(collectionType, id)}/query`, {
        page_size: 50,
        filter,
        start_cursor: nextCursor
      });

      results.push(...(payload.results ?? []));
      nextCursor = payload.has_more ? payload.next_cursor : undefined;
    } while (nextCursor);

    return results;
  }

  async retrievePage(pageId) {
    return this.request("GET", `/v1/pages/${pageId}`);
  }

  async createPage(parentType, parentId, properties) {
    const parentKey = parentType === "data_source" ? "data_source_id" : "database_id";
    return this.request("POST", "/v1/pages", {
      parent: {
        [parentKey]: parentId
      },
      properties
    });
  }

  async updatePage(pageId, properties) {
    return this.request("PATCH", `/v1/pages/${pageId}`, {
      properties
    });
  }

  async request(method, route, body = undefined) {
    if (!this.apiKey) {
      throw new ServiceError(503, "Notion API key is not configured.");
    }

    const response = await fetch(`https://api.notion.com${route}`, {
      method,
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Notion-Version": this.version,
        "Content-Type": "application/json"
      },
      body: body ? JSON.stringify(body) : undefined
    });

    const payload = await readJson(response);
    if (!response.ok) {
      throw new ServiceError(
        response.status,
        payload?.message ?? "Notion API request failed.",
        payload
      );
    }

    return payload;
  }
}

export function buildPropertyPatch(schema, value) {
  if (value === undefined) {
    return undefined;
  }

  switch (schema.type) {
    case "title":
      return {
        title: toRichTextArray(value)
      };
    case "rich_text":
      return {
        rich_text: toRichTextArray(value)
      };
    case "url":
      return { url: value || null };
    case "email":
      return { email: value || null };
    case "phone_number":
      return { phone_number: value || null };
    case "number":
      return { number: value === null ? null : Number(value) };
    case "checkbox":
      return { checkbox: Boolean(value) };
    case "date":
      return {
        date: value
          ? {
              start: value
            }
          : null
      };
    case "select":
      return {
        select: value ? { name: String(value) } : null
      };
    case "status":
      return {
        status: value ? { name: String(value) } : null
      };
    case "multi_select":
      return {
        multi_select: (Array.isArray(value) ? value : [value])
          .filter(Boolean)
          .map((item) => ({ name: String(item) }))
      };
    case "people":
      return {
        people: uniqueIds(Array.isArray(value) ? value : [value]).map((id) => ({
          object: "user",
          id
        }))
      };
    case "relation":
      return {
        relation: uniqueIds(Array.isArray(value) ? value : [value]).map((id) => ({ id }))
      };
    default:
      throw new ServiceError(
        500,
        `Unsupported Notion property type "${schema.type}" for property "${schema.name ?? schema.id}".`
      );
  }
}

export function buildEqualsFilter(propertyName, schema, value) {
  if (value === undefined) {
    return undefined;
  }

  switch (schema.type) {
    case "title":
      return {
        property: propertyName,
        title: {
          equals: String(value)
        }
      };
    case "rich_text":
      return {
        property: propertyName,
        rich_text: {
          equals: String(value)
        }
      };
    case "url":
      return {
        property: propertyName,
        url: {
          equals: String(value)
        }
      };
    case "email":
      return {
        property: propertyName,
        email: {
          equals: String(value)
        }
      };
    case "phone_number":
      return {
        property: propertyName,
        phone_number: {
          equals: String(value)
        }
      };
    case "select":
      return {
        property: propertyName,
        select: {
          equals: String(value)
        }
      };
    case "status":
      return {
        property: propertyName,
        status: {
          equals: String(value)
        }
      };
    default:
      throw new ServiceError(
        500,
        `Unsupported lookup type "${schema.type}" for property "${propertyName}".`
      );
  }
}

export function readPropertyValue(page, propertyName) {
  const property = page.properties?.[propertyName];
  if (!property) {
    return undefined;
  }

  switch (property.type) {
    case "title":
      return property.title.map((item) => item.plain_text).join("");
    case "rich_text":
      return property.rich_text.map((item) => item.plain_text).join("");
    case "url":
      return property.url ?? undefined;
    case "email":
      return property.email ?? undefined;
    case "phone_number":
      return property.phone_number ?? undefined;
    case "select":
      return property.select?.name;
    case "status":
      return property.status?.name;
    case "date":
      return property.date?.start;
    case "number":
      return property.number ?? undefined;
    case "checkbox":
      return property.checkbox;
    case "people":
      return property.people.map((person) => person.id);
    case "relation":
      return property.relation.map((relation) => relation.id);
    case "multi_select":
      return property.multi_select.map((option) => option.name);
    default:
      return undefined;
  }
}

export function mergeRelationPatch(existingPage, propertyName, ids) {
  const currentIds = Array.isArray(readPropertyValue(existingPage, propertyName))
    ? readPropertyValue(existingPage, propertyName)
    : [];
  return uniqueIds([...currentIds, ...ids]);
}

export function propertyOptionNames(schema) {
  if (schema.type === "select") {
    return schema.select.options.map((option) => option.name);
  }
  if (schema.type === "status") {
    return schema.status.options.map((option) => option.name);
  }
  return [];
}

function toRichTextArray(value) {
  return splitRichText(String(value)).map((content) => ({
    type: "text",
    text: {
      content
    }
  }));
}

function collectionPath(collectionType, id) {
  const normalizedType = collectionType === "database" ? "databases" : "data_sources";
  return `/v1/${normalizedType}/${id}`;
}

async function readJson(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }

  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}
