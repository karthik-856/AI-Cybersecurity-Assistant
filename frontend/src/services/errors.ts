export function getErrorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const payload = data as Record<string, unknown>;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((item: unknown) => {
        if (typeof item === "string") return item;
        if (
          item &&
          typeof item === "object" &&
          "msg" in item &&
          typeof item.msg === "string"
        )
          return item.msg;
        return "Invalid request.";
      })
      .join(", ");
  }
  return typeof payload.message === "string" ? payload.message : fallback;
}
