import fs from "node:fs";
import path from "node:path";

export type AppSettings = {
  allowPythonExecution: boolean;
};

const DEFAULT_SETTINGS: AppSettings = {
  allowPythonExecution: true,
};

function getSettingsPath(): string {
  const dir = path.join(process.cwd(), "data");
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return path.join(dir, "settings.json");
}

export function getAppSettings(): AppSettings {
  try {
    const file = getSettingsPath();
    if (fs.existsSync(file)) {
      const data = JSON.parse(fs.readFileSync(file, "utf-8"));
      return {
        ...DEFAULT_SETTINGS,
        ...data,
      };
    }
  } catch (err) {
    console.error("Error reading settings.json:", err);
  }
  return DEFAULT_SETTINGS;
}

export function updateAppSettings(partial: Partial<AppSettings>): AppSettings {
  const current = getAppSettings();
  const updated = { ...current, ...partial };
  try {
    const file = getSettingsPath();
    fs.writeFileSync(file, JSON.stringify(updated, null, 2), "utf-8");
  } catch (err) {
    console.error("Error writing settings.json:", err);
  }
  return updated;
}
