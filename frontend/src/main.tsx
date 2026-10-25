import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import App from "./App";
import "./ui/index.css";
import "./styles.css";

/* Обычная сборка живёт на сервере: nginx отдаёт index.html на любой путь,
   поэтому адреса вида /login работают как надо.

   Снимок (npm run snapshot) открывают с диска по file://, где браузер
   считает путём папку на компьютере и ни один маршрут не совпадёт.
   Там переключаемся на адреса через #. */
const Router = import.meta.env.VITE_SNAPSHOT ? HashRouter : BrowserRouter;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Router>
      <App />
    </Router>
  </StrictMode>,
);
