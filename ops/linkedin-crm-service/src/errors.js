export class ServiceError extends Error {
  constructor(status, message, details = undefined) {
    super(message);
    this.name = "ServiceError";
    this.status = status;
    this.details = details;
  }
}

export class ConfigError extends ServiceError {
  constructor(message, details = undefined) {
    super(503, message, details);
    this.name = "ConfigError";
  }
}

export class ConflictError extends ServiceError {
  constructor(message, details = undefined) {
    super(409, message, details);
    this.name = "ConflictError";
  }
}
