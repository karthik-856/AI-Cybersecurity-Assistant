let sharedAudioContext: AudioContext | null = null;
let unlockListenersInstalled = false;

function getAudioContext(): AudioContext | null {
  if (sharedAudioContext) return sharedAudioContext;

  const AudioContextClass =
    window.AudioContext ||
    (window as typeof window & { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext;

  if (!AudioContextClass) return null;
  sharedAudioContext = new AudioContextClass();
  return sharedAudioContext;
}

export function prepareAlertAudio() {
  if (unlockListenersInstalled || typeof window === "undefined") return;
  unlockListenersInstalled = true;

  const unlock = () => {
    const context = getAudioContext();
    if (!context) return;

    void context.resume().then(() => {
      if (context.state !== "running") return;
      window.removeEventListener("pointerdown", unlock, true);
      window.removeEventListener("keydown", unlock, true);
      unlockListenersInstalled = false;
    }).catch(() => undefined);
  };

  window.addEventListener("pointerdown", unlock, true);
  window.addEventListener("keydown", unlock, true);
}

export async function playAlertSound(): Promise<boolean> {
  try {
    const context = getAudioContext();
    if (!context) return false;
    if (context.state !== "running") await context.resume();
    if (context.state !== "running") return false;

    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const startedAt = context.currentTime;
    oscillator.frequency.value = 880;
    oscillator.type = "sine";
    gain.gain.setValueAtTime(0.0001, startedAt);
    gain.gain.exponentialRampToValueAtTime(0.12, startedAt + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, startedAt + 0.2);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.addEventListener("ended", () => {
      oscillator.disconnect();
      gain.disconnect();
    }, { once: true });
    oscillator.start();
    oscillator.stop(startedAt + 0.205);
    return true;
  } catch {
    return false;
  }
}
