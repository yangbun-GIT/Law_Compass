export type ChatSuggestionAction = "send_message" | "navigate" | "apply_case_draft" | "open_upload" | "open_external" | "open_result_help";

export type ChatSuggestion = {
  label: string;
  action: ChatSuggestionAction;
  target?: string;
  message?: string;
  payload?: Record<string, any>;
};

export type ChatDraftCase = {
  title: string;
  description_text: string;
  structured_facts?: Record<string, any>;
  selected_keywords?: string[];
  analysis_mode?: string;
  ai_profile?: string;
  followup_questions?: string[];
  knia_match?: ChatKniaMatch | null;
};

export type ChatKniaMatch = {
  chart_no: string;
  chart_type?: string;
  title: string;
  accident_party_type?: string;
  accident_party_label?: string;
  match_reason?: string;
  source_url?: string;
  video_url?: string;
  thumbnail_url?: string;
  base_fault_a?: number | null;
  base_fault_b?: number | null;
  display_tags?: string[];
  recommended_user_actions?: string[];
  display_mode?: string;
  button_label?: string;
  attribution?: string;
};

export type ChatSafety = {
  allowed: boolean;
  flags: string[];
  severity?: "low" | "medium" | "high";
  safe_reply?: string;
};

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string;
  suggestions?: ChatSuggestion[];
  draft_case?: ChatDraftCase | null;
  knia_matches?: ChatKniaMatch[];
  knia_primary_match?: ChatKniaMatch | null;
  safety?: ChatSafety;
  created_at?: string;
};

export type ChatContext = {
  page?: string;
  case_id?: string;
  chart_no?: string;
  current_route?: string;
  report_summary?: string;
  [key: string]: any;
};

export type ChatResponse = {
  session_id: string;
  reply: string;
  intent: string;
  message?: { role: "assistant"; content: string; intent?: string };
  suggestions: ChatSuggestion[];
  draft_case?: ChatDraftCase | null;
  knia_matches?: ChatKniaMatch[];
  knia_primary_match?: ChatKniaMatch | null;
  safety: ChatSafety;
  route_hint?: Record<string, any> | null;
};
