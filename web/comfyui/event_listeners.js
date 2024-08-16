import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const { chainCallback } = await import("/extensions/ComfyUI_Dados_Nodes/common/js/utils.js");

app.registerExtension({
  name: "Dados.EventListeners",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
/*     chainCallback(app.graph, 'onNodeRemoved', async function (node) {
      console.log("(Dados.EventListeners) Node Removed :", node.type, node.id);
      
    });  */
    /* not being triggered app.graph, 'onExecuted' */
    chainCallback(app.graph, 'onExecuted', async function (node) {
      console.log("(Dados.EventListeners) Node Executed :", node.type, node.id);
    });

  }
});

/* api.addEventListener("executing", ({ detail }) => {
  console.log("Node start executing:", detail);
});

api.addEventListener("executed", ({ detail }) => {
  console.log("Node executed:", detail);
}); */

