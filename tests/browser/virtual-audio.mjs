// Process-owned Linux test sink. No system daemon, hardware, or persistent config.
import { spawn } from "node:child_process";
import { access, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

export async function virtualAudio() {
  if (process.platform !== "linux") return { env: {}, stop: async () => {} };
  const directory = await mkdtemp(join(tmpdir(), "vistoda-test-audio-"));
  const socket = join(directory, "native");
  const child = spawn("pulseaudio", ["--daemonize=no", "--exit-idle-time=-1", "--use-pid-file=no", "-n",
    "--load=module-null-sink sink_name=vistoda_test",
    `--load=module-native-protocol-unix socket=${socket} auth-anonymous=1 auth-cookie-enabled=0`],
  { env: { ...process.env, PULSE_RUNTIME_PATH: directory, PULSE_STATE_PATH: directory }, stdio: "ignore" });
  let exited = false; let failed = false;
  const closed = new Promise((resolve) => {
    child.once("close", () => { exited = true; resolve(); });
    child.once("error", () => { failed = true; resolve(); });
  });
  const stop = async () => {
    if (!exited) child.kill("SIGTERM");
    await Promise.race([closed, new Promise((resolve) => setTimeout(resolve, 2000))]);
    if (!exited && !failed) { child.kill("SIGKILL"); await closed; }
    await rm(directory, { recursive: true, force: true });
  };
  try {
    const deadline = Date.now() + 5000;
    while (Date.now() < deadline && !exited && !failed) {
      try { await access(socket); return { env: { PULSE_SERVER: `unix:${socket}` }, stop }; }
      catch { await new Promise((resolve) => setTimeout(resolve, 50)); }
    }
    throw new Error("Virtual audio unavailable: install pulseaudio for browser capture tests");
  } catch (error) { await stop(); throw error; }
}
