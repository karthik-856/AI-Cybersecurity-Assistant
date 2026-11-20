import { useCallback, useEffect, useRef, useState } from "react";
import { processDemoEvent } from "../services/api";

// The signed-in layout owns the run, so route changes cannot stop it.
// Runs remain explicit and bounded; refresh/sign-out ends them, sleep pauses timers.
export function useDemoReplay(canProcessDemo: boolean) {
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoRunCount, setDemoRunCount] = useState(0);
  const [processingDemo, setProcessingDemo] = useState(false);
  const [demoMessage, setDemoMessage] = useState("");
  const [demoError, setDemoError] = useState("");
  const [demoAlert, setDemoAlert] = useState<string | null>(null);
  const [demoEvent, setDemoEvent] = useState<number | null>(null);
  const inFlight = useRef(false);

  const runDemo = useCallback(async (): Promise<boolean> => {
    if (!canProcessDemo || inFlight.current) return false;
    inFlight.current = true;
    setProcessingDemo(true);
    setDemoError("");
    try {
      const saved = Number(localStorage.getItem("zuka_demo_row") || "0");
      const result = await processDemoEvent(
        Number.isInteger(saved) && saved >= 0 && saved <= 1000000 ? saved : 0,
      );
      localStorage.setItem("zuka_demo_row", String(result.next_row_index));
      const row = result.result;
      setDemoEvent(row?.network_event_id ?? null);
      setDemoAlert(row?.alert_id ?? null);
      setDemoMessage(
        row
          ? `Demo event #${row.network_event_id}: ${row.predicted_class}. ${row.alert_id ? "Alert and explanation saved." : "Benign flow; no alert created."}`
          : result.message,
      );
      return result.processed;
    } catch (error) {
      setDemoError(
        error instanceof Error
          ? error.message
          : "Unable to process demonstration event.",
      );
      return false;
    } finally {
      inFlight.current = false;
      setProcessingDemo(false);
    }
  }, [canProcessDemo]);

  useEffect(() => {
    if (!demoRunning || !canProcessDemo) return;
    let active = true;
    let processed = 0;
    let timer: ReturnType<typeof setTimeout>;
    async function tick() {
      const succeeded = await runDemo();
      if (!active) return;
      if (!succeeded) {
        setDemoRunning(false);
        return;
      }
      processed += 1;
      setDemoRunCount(processed);
      if (processed >= 65) setDemoRunning(false);
      else timer = setTimeout(() => void tick(), 5000);
    }
    timer = setTimeout(() => void tick(), 0);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [demoRunning, canProcessDemo, runDemo]);

  function startDemo() {
    if (!canProcessDemo || inFlight.current || demoRunning) return;
    setDemoRunCount(0);
    setDemoRunning(true);
  }

  return {
    canProcessDemo,
    demoRunning,
    demoRunCount,
    processingDemo,
    demoMessage,
    demoError,
    demoAlert,
    demoEvent,
    runDemo,
    startDemo,
    pauseDemo: () => setDemoRunning(false),
  };
}

export type DemoReplayState = ReturnType<typeof useDemoReplay>;
