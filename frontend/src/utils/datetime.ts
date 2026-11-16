/**
 * ZUKA Date/Time Utilities
 * Formats timestamps in user's laptop local time environment.
 */

export function parseUtcDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;

  const raw = String(value).trim();
  if (!raw) return null;

  const normalized =
    /[zZ]$/.test(raw) || /[+-]\d{2}:\d{2}$/.test(raw)
      ? raw
      : `${raw.replace(" ", "T")}Z`;

  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const date = parseUtcDate(value);
  if (!date) return "—";

  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatShortDateTime(value: string | Date | null | undefined): string {
  const date = parseUtcDate(value);
  if (!date) return "—";

  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatTime(value: string | Date | null | undefined): string {
  const date = parseUtcDate(value);
  if (!date) return "—";

  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = parseUtcDate(value);
  if (!date) return "—";

  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function isToday(value: string | Date | null | undefined): boolean {
  const date = parseUtcDate(value);
  if (!date) return false;
  const now = new Date();
  return (
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  );
}
