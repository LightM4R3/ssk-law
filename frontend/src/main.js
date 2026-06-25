import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import router from "./router";
import "./assets/styles/index.css";

function notifyFrontendError(error) {
  window.dispatchEvent(new CustomEvent("ssk-law:frontend-error", {
    detail: { message: error?.message || String(error || "") },
  }));
}

window.addEventListener("error", (event) => {
  notifyFrontendError(event.error || event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  notifyFrontendError(event.reason);
});

const app = createApp(App);

app.config.errorHandler = (error) => {
  notifyFrontendError(error);
};

app
  .use(createPinia())
  .use(router)
  .mount("#app");
