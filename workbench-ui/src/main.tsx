import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import { PreviewPage } from "./preview/PreviewPage";

function App() {
  return window.location.pathname === "/preview" ? <PreviewPage /> : <PreviewPage />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
