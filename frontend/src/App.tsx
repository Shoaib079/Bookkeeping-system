import { BrowserRouter } from "react-router-dom";

import { AppRouter } from "./routes/AppRouter";
import { ThemeProvider } from "./theme/ThemeProvider";
import "./styles/app.css";

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </ThemeProvider>
  );
}
