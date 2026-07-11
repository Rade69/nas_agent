// Deterministic Serbian Cyrillic -> Latin transliteration (1:1, lossless).
// Context: agent_reports/2026-07-11_dictation-cyrillic-fix.md
//
// Debug logging (2026-07-11) proved the Realtime API's Whisper transcription
// sometimes returns Serbian speech in Cyrillic script within the same voice
// session that otherwise produces Latin script — this project standardizes
// on sr-Latn throughout. Rather than hope a `language` hint alone prevents
// the API from ever choosing Cyrillic (unverifiable without live testing),
// this deterministically normalizes any Cyrillic characters that do come
// back, so the visible result is always Latin regardless of what the STT
// engine decided for a given utterance.
const CYRILLIC_TO_LATIN: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", ђ: "đ", е: "e", ж: "ž", з: "z",
  и: "i", ј: "j", к: "k", л: "l", љ: "lj", м: "m", н: "n", њ: "nj", о: "o",
  п: "p", р: "r", с: "s", т: "t", ћ: "ć", у: "u", ф: "f", х: "h", ц: "c",
  ч: "č", џ: "dž", ш: "š",
  А: "A", Б: "B", В: "V", Г: "G", Д: "D", Ђ: "Đ", Е: "E", Ж: "Ž", З: "Z",
  И: "I", Ј: "J", К: "K", Л: "L", Љ: "Lj", М: "M", Н: "N", Њ: "Nj", О: "O",
  П: "P", Р: "R", С: "S", Т: "T", Ћ: "Ć", У: "U", Ф: "F", Х: "H", Ц: "C",
  Ч: "Č", Џ: "Dž", Ш: "Š",
};

export function cyrillicToLatin(text: string): string {
  let result = "";
  for (const char of text) {
    result += CYRILLIC_TO_LATIN[char] ?? char;
  }
  return result;
}
