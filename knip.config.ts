import type { KnipConfig } from "knip";

const config: KnipConfig = {
  entry: [
    "electron/main.ts",
    "electron/preload.ts",
    "src/main.tsx",
  ],
  project: [
    "electron/**/*.ts",
    "src/**/*.{ts,tsx}",
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
    // Vite and plugins — used by Electron Forge and vite config files
    "vite",
    "@electron-forge/plugin-vite",
    "@vitejs/plugin-react",
    "@tailwindcss/vite",
    "tailwindcss",
  ],
  ignoreBinaries: [
    // ESLint is referenced in package.json scripts but not yet configured
    "eslint",
  ],
};

export default config;
