import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import tokenBundle from "../generated/design-tokens.json";
import { applyTokenMap, type DesignTokenBundle } from "./applyTokens";

type ThemeMode = "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  bundle: DesignTokenBundle;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

const bundle = tokenBundle as DesignTokenBundle;

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>("light");

  useEffect(() => {
    const root = document.documentElement;
    const palette = mode === "light" ? bundle.light : bundle.dark;
    applyTokenMap(root, palette);
    applyTokenMap(root, bundle.componentGrammar);
    root.dataset.theme = mode;
    root.dataset.grammarVersion = bundle.grammarVersion;
  }, [mode]);

  const value = useMemo(
    () => ({ mode, setMode, bundle }),
    [mode],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
