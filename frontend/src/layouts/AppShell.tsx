import { useEffect, useState } from "react";

import { DesktopShell } from "./DesktopShell";
import { MobileShell } from "./MobileShell";

const MOBILE_QUERY = "(max-width: 768px)";

export function AppShell() {
  const [isMobile, setIsMobile] = useState(
    () => window.matchMedia(MOBILE_QUERY).matches,
  );

  useEffect(() => {
    const media = window.matchMedia(MOBILE_QUERY);
    const onChange = () => setIsMobile(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return isMobile ? <MobileShell /> : <DesktopShell />;
}
