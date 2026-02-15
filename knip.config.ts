import type { KnipConfig } from "knip";

const config: KnipConfig = {
  entry: [
    "electron/main.ts",
    "electron/preload.ts",
    // Uncomment when React scaffolding is added:
    // "src/main.tsx",
  ],
  project: [
    "electron/**/*.ts",
    // Uncomment when React scaffolding is added:
    // "src/**/*.{ts,tsx}",
  ],
  ignore: [
    "dist/**",
    ".vite/**",
  ],
  ignoreDependencies: [
    // Electron Forge makers — loaded dynamically by Forge, not imported directly
    "@electron-forge/maker-squirrel",
    "@electron-forge/maker-zip",
    "@electron-forge/maker-deb",
    "@electron-forge/maker-rpm",
    // Vite is used by @electron-forge/plugin-vite internally
    "vite",
    "@electron-forge/plugin-vite",
  ],
  ignoreBinaries: [
    // ESLint is referenced in package.json scripts but not yet configured
    "eslint",
  ],
};

export default config;
