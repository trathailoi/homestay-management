import vi from "./vi.json";
import en from "./en.json";

export type Locale = "vi" | "en";

export type Dictionary = Record<string, string | string[]>;

export const dictionaries: Record<Locale, Dictionary> = { vi, en };
