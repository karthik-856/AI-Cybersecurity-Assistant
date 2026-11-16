export const SESSION_EXPIRED_EVENT = "zuka:session-expired";

/** Reject an expired session without clearing a newer sign-in's credentials. */
export async function sessionFetch(
  url: string,
  options: RequestInit = {},
): Promise<Response> {
  const authorization = new Headers(options.headers).get("Authorization");
  const response = await fetch(url, options);
  const currentToken = localStorage.getItem("zuka_access_token");
  if (
    response.status === 401 &&
    currentToken &&
    authorization === `Bearer ${currentToken}`
  ) {
    localStorage.removeItem("zuka_access_token");
    localStorage.removeItem("zuka_user");
    sessionStorage.removeItem("zuka_chat_history");
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
  return response;
}
