import { createApp } from "vue";

import App from "./App.vue";
import { revealDirective } from "./directives/reveal";
import { rippleDirective } from "./directives/ripple";
import "./styles.css";
import "./themes.css";

const app = createApp(App);
app.directive("reveal", revealDirective);
app.directive("ripple", rippleDirective);
app.mount("#app");
