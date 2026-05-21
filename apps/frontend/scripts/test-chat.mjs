import { readFileSync, existsSync } from "node:fs";

const required = [
  "src/components/chat/AiChatFloatingButton.vue",
  "src/components/chat/AiChatPanel.vue",
  "src/components/chat/ChatKniaMatchCard.vue",
  "src/components/chat/ChatDraftCaseCard.vue",
  "src/stores/chatStore.ts",
  "src/api/chat.ts",
  "src/types/chat.ts"
];

for (const file of required) {
  if (!existsSync(file)) throw new Error(`missing ${file}`);
}

const forbidden = ["match_score", "chunk_id", "model_info", "raw HTML", "embedding"];
const userFiles = [
  "src/components/chat/AiChatPanel.vue",
  "src/components/chat/ChatKniaMatchCard.vue",
  "src/components/chat/ChatMessageBubble.vue"
];
for (const file of userFiles) {
  const text = readFileSync(file, "utf8");
  for (const token of forbidden) {
    if (text.includes(token)) throw new Error(`${file} exposes forbidden token ${token}`);
  }
}
console.log(JSON.stringify({ test_chat: "passed", required_files: required.length }, null, 2));
