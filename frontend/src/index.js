import React from "react";
import ReactDOM from "react-dom/client";
// Styles
import "./custom.scss";
// State
import { Provider } from "react-redux";
import { store } from "./app/store";
// Config
import { filteredProjects, projectCardImages } from "./config";
import App from "./App";
import * as serviceWorkerRegistration from "./serviceWorkerRegistration";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <Provider store={store}>
    <App
      filteredProjects={filteredProjects}
      projectCardImages={projectCardImages}
    />
  </Provider>
);


serviceWorkerRegistration.register();
