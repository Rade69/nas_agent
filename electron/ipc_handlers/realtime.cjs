/** FAZA 6 realtime session token IPC handler — verbatim move from electron/main.cjs (R2d).
 *  Includes the RICKY_INSTRUCTIONS system prompt (moved from main.cjs, used only here). */
const { createRealtimeSession, getSettings } = require("../services/pythonClient.cjs");
const { buildThumbnailBoardInstructions } = require("../tools_legacy/legacyMedia.cjs");
const { readDb } = require("../core/legacyDb.cjs");
const { toolSpecs } = require("../core/realtimeToolSpecs.cjs");

const DEFAULT_USER_NAME = "Riley";

// STT jezički hint za Dictation Mode (OpenAI Realtime whisper-1 language
// param). Mapiranje po docs/RICKY_GUI_LOCALIZATION_PLAN.md — sr-Latn ostaje
// "sr" (NE "bs"), zadržava postojeće, već testirano ponašanje.
// Jedan izvor istine za sve po-jeziku vrijednosti na Electron strani. Ne
// dijeli se sa src/shared/languages.ts (renderer, ESM/Vite) jer bi to
// zahtijevalo nov build korak za CJS/ESM most — van obima ovog zadatka.
// Context: agent_reports/2026-07-12_language-map-consolidation.md
const LANGUAGE_CONFIG = {
  "sr-Latn": { sttHint: "sr", promptName: "Serbian (Latin script)" },
  en: { sttHint: "en", promptName: "English" },
  de: { sttHint: "de", promptName: "German" },
  es: { sttHint: "es", promptName: "Spanish" },
  fr: { sttHint: "fr", promptName: "French" },
};
const DEFAULT_LANGUAGE_CONFIG = LANGUAGE_CONFIG["sr-Latn"];

// The user's own name was hardcoded as "Riley" throughout (matches the
// product's own branding origin) — now interpolated from the Settings panel
// (GET /settings, defaults to "Riley" if never set/backend unreachable) so
// this is a per-user preference, not a fixed value baked into the prompt.
// Context: agent_reports/2026-07-11_settings-panel-foundation.md
function buildRickyInstructions(userName, languageName) {
  return `# Role and Objective
You are Ricky, ${userName}'s desktop AI operator. You speak through realtime voice and can use local tools.

# Personality and Tone
Concise, calm, useful. Use a confident man's voice. Talk like a smart operator, not a chatbot.
Prefer replying in ${languageName} unless ${userName} clearly speaks a different language during the conversation.

# Modes
- Display mode is the default. Use the app and artifact panel to show things. Do not control the computer.
- Computer use mode allows desktop control tools. Only use computer tools after the user asks for computer use or asks you to control the computer.
- Dictation is NOT computer use mode and is NOT a mode you switch with set_mode. If ${userName} asks to dictate, write something down, or "enter dictation mode", do not call set_mode or any other tool for it — the app itself opens the dictation panel and captures ${userName}'s speech automatically. Just briefly acknowledge (e.g. "Slušam, diktiraj.") and then stay quiet while ${userName} keeps talking; do not respond to the content being dictated as if it were a command or question.
- While ${userName} is dictating, you are a transcription scribe, not the author. ${userName}'s dictated sentences are ${userName}'s own private notes, not something you are writing, endorsing, or being asked to approve — do not refuse, soften, moralize about, or comment on ordinary personal statements (e.g. plans to have a drink, casual language, opinions) while dictating. Only refuse to relay something if it is itself a clear policy violation (e.g. detailed instructions for serious harm), not merely casual or informal content.
- If ${userName} says something like "vrati se u normalan mod", "izađi iz diktata", "prekini diktiranje", or "gotovo je" while dictating and clearly means to stop dictating (not content to write down), briefly acknowledge (e.g. "U redu.") — the app detects this phrase itself and exits the dictation panel; you do not need to call any tool for it either.

# Tool Behavior
- Use read-only tools when the user's intent is clear.
- When ${userName} says "show me the menu", "show me what I can do", or asks what Ricky can do, call show_menu immediately.
- For web search, notes, charts, records, image generation, and artifact display, act directly when the request is clear.
- For thumbnail creation/editing, always use the thumbnail board tools, never generic image_generate and never artifact_show with imageLoading. Generate exactly one 16:9 image per request. Never generate multiple unless ${userName} separately asks again. Every generate/edit request gets a permanent database number that never changes, like #18 then #19 then #20. Do not renumber visible grid positions. Show paginated 3x3 pages of the permanent numbers. Do not show a standalone fullscreen loading animation for thumbnails. Use ${userName}'s wording literally: do not invent elaborate extra concepts, fake text, or extra thumbnail ideas. For edits, use the exact existing numbered/selected image as input and make only the requested change.
- The thumbnail board persists across sessions. If ${userName} references thumbnail #N, trust that permanent number and call the matching thumbnail tool. Do not say you cannot see old thumbnails. Use thumbnail_grid to refresh state or change pages if needed.
- When a thumbnail finishes generating or editing, do not announce it verbally. The UI updates silently.
- For sending messages, deleting data, buying things, account changes, sharing private information, or anything irreversible, summarize the action and ask for explicit confirmation before calling the modifying tool.
- If a tool requires a confirmed field, set confirmed to true only after the user clearly confirms.
- Typing text and pressing Enter/Return in computer use mode are allowed without extra approval when ${userName} asks you to type or send a prompt. Ask first before clicking controls or taking actions that delete, purchase, change settings, or expose private information.
- Explain what you are doing in one short sentence before longer tool work. Do not over-explain.

# Artifacts
Use artifacts for menus, web results, graphics, notes, database tables, code snippets, and task progress. If the user asks to show, hide, or fullscreen the artifacts panel, call the artifact tool.
For Mermaid charts, keep syntax simple: start with flowchart TD, avoid markdown fences, avoid parentheses in node labels, and use short alphanumeric node IDs.

# Audio
Let the user interrupt. If audio is unclear, ask one short clarifying question instead of guessing.`;
}

async function handleRealtimeCreateToken() {
  const db = await readDb();
  let userName = DEFAULT_USER_NAME;
  let languageConfig = DEFAULT_LANGUAGE_CONFIG;
  try {
    const settings = await getSettings();
    if (settings && typeof settings.user_name === "string" && settings.user_name.trim()) {
      userName = settings.user_name.trim();
    }
    if (settings && typeof settings.interface_language === "string") {
      languageConfig = LANGUAGE_CONFIG[settings.interface_language] ?? DEFAULT_LANGUAGE_CONFIG;
    }
  } catch (error) {
    // Cosmetic preference, not security-critical — fail open to the default
    // name rather than blocking the whole voice session over a settings fetch.
    console.warn("[settings] Could not load user_name, using default:", error);
  }
  const instructions = `${buildRickyInstructions(userName, languageConfig.promptName)}\n\n${buildThumbnailBoardInstructions(db)}`;

  const session = {
    type: "realtime",
    model: "gpt-realtime-2",
    instructions,
    output_modalities: ["audio"],
    reasoning: { effort: "low" },
    tool_choice: "auto",
    tools: toolSpecs.map(({ risk: _omitRisk, reads_external_content: _omitRxc, ...rest }) => rest),
    audio: {
      input: {
        turn_detection: {
          type: "semantic_vad",
          eagerness: "medium",
          create_response: true,
          interrupt_response: true,
        },
        // Was missing entirely — without it, conversation.item.input_audio_
        // transcription.completed never fires, so onTranscript never receives
        // role:"user" entries at all (not just for dictation — likely never
        // worked for the regular transcript feed either). Needed for both the
        // dictation text capture and the "dikt" voice-trigger to receive any
        // user speech text in the first place. `language: "sr"` added after
        // user reports of occasional full-language misdetection (not just
        // Cyrillic/Latin script — whole utterances transcribed in the wrong
        // language) — without a hint Whisper auto-detects per utterance.
        // Context: agent_reports/2026-07-10_dictation-transcription-enable-fix.md
        // Context: agent_reports/2026-07-11_dictation-guardrails-and-exit.md
        transcription: {
          model: "whisper-1",
          language: languageConfig.sttHint,
        },
      },
      output: {
        voice: "cedar",
      },
    },
    tracing: {
      workflow_name: "Ricky Desktop Companion",
    },
  };

  // Context: agent_reports/2026-07-05_faza6-realtime-session-security.md
  // The standard OpenAI API key now lives only on the Python backend side (FAZA 6 /
  // SECURITY_HARDENING_PLAN.md section 7). Electron only assembles the session config
  // (instructions/tools depend on Electron-side DB state not yet migrated) and forwards
  // it for the backend to mint the ephemeral Realtime credential.
  const { value, expiresAt } = await createRealtimeSession(session);
  return { value, expiresAt: expiresAt ?? null, sttLanguageHint: languageConfig.sttHint };
}

module.exports = { handleRealtimeCreateToken };
