import type { CSSProperties } from "react";

export type TokenMap = Record<string, string>;

export type DesignTokenBundle = {
  version: string;
  grammarVersion: string;
  light: TokenMap;
  dark: TokenMap;
  componentGrammar: TokenMap;
};

export function applyTokenMap(
  target: HTMLElement,
  tokens: TokenMap,
): void {
  for (const [key, value] of Object.entries(tokens)) {
    target.style.setProperty(key, value);
  }
}

export function tokensToStyle(tokens: TokenMap): CSSProperties {
  const style: Record<string, string> = {};
  for (const [key, value] of Object.entries(tokens)) {
    style[key] = value;
  }
  return style as CSSProperties;
}
