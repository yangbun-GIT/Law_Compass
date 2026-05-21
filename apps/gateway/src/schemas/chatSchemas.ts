export const createChatSessionSchema = {
  body: {
    type: "object",
    properties: {
      case_id: { type: "string" },
      title: { type: "string", maxLength: 140 },
      context: { type: "object", additionalProperties: true }
    },
    additionalProperties: true
  }
} as const;

export const sendChatMessageSchema = {
  body: {
    type: "object",
    required: ["message"],
    properties: {
      message: { type: "string", minLength: 1, maxLength: 4000 },
      context: { type: "object", additionalProperties: true }
    },
    additionalProperties: true
  }
} as const;

export const quickChatSchema = {
  body: {
    type: "object",
    required: ["message"],
    properties: {
      message: { type: "string", minLength: 1, maxLength: 4000 },
      case_id: { type: "string" },
      context: { type: "object", additionalProperties: true }
    },
    additionalProperties: true
  }
} as const;
