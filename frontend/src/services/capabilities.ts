import { useEffect, useState } from "react";
import { API_BASE_URL } from "./config";

interface Capabilities {
  registration: boolean;
  password_recovery: boolean;
  two_factor: boolean;
}
const unavailable: Capabilities = {
  registration: false,
  password_recovery: false,
  two_factor: false,
};

export function useCapabilities() {
  const [capabilities, setCapabilities] = useState(unavailable);
  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${API_BASE_URL}/api/auth/features`, {
      signal: controller.signal,
    })
      .then((response) =>
        response.ok ? (response.json() as Promise<Capabilities>) : unavailable,
      )
      .then((result) => {
        if (!controller.signal.aborted) setCapabilities(result);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, []);
  return capabilities;
}
