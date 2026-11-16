// Defer initial network work until React's effect cleanup probe has completed.
// A screen unmounted before the task starts never sends an abandoned request.
export function scheduleLoad(load: () => Promise<void>): () => void {
  let cancelled = false;
  queueMicrotask(() => {
    if (!cancelled)
      void load().catch((error) =>
        console.error("Unable to refresh data", error),
      );
  });
  return () => {
    cancelled = true;
  };
}
