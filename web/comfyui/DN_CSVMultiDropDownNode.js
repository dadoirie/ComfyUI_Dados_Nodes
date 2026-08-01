import { app } from "../../scripts/app.js"
import { api } from "../../scripts/api.js"

let EXTENSION_NAME, MESSAGE_ROUTE, chainCallback, fetchSend;
(async () => {
  const constants = await fetch('/dadosConstants').then(response => response.json());
  EXTENSION_NAME = constants.EXTENSION_NAME;
  MESSAGE_ROUTE = constants.MESSAGE_ROUTE;
  
  ({chainCallback, fetchSend} = 
   await import(`/extensions/${EXTENSION_NAME}/common/js/utils.js`));
})().catch(error => console.error("Failed to load utilities:", error));

app.registerExtension({
    name: "DN_CSVMultiDropDownNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "DN_CSVMultiDropDownNode") return;

        chainCallback(nodeType.prototype, "onNodeCreated", function() {
            this.properties = this.properties || {};
            this.properties.csvText = this.properties.csvText || "";
            this.properties.removeDuplicates = this.properties.removeDuplicates || "false";
            this.dropdownWidgets = {};

            if (this.outputs) {
                for (let i = this.outputs.length - 1; i >= 0; i--) {
                    const output = this.outputs[i];
                    if (output.name !== "combined_selections") {
                        this.removeOutput(i);
                    }
                }
            }
            
            const computed = this.computeSize();
            this.size[0] = Math.max(this.size[0], computed[0]);
            this.size[1] = computed[1];
            this.setDirtyCanvas(true, true);

            const csvWidget = this.widgets.find(w => w.name === "csv_text");
            if (csvWidget && csvWidget.element) {
                /* csvWidget.element.addEventListener('focus', () => {
                    console.log("csv_text focused", this.id);
                }); */
                csvWidget.element.addEventListener('blur', () => {
                    this.resetDropdowns();
                    this.properties.csvText = csvWidget.value;
                    this.parseCSVToDropdowns(csvWidget.value);
                });

                this.addWidget("button", "load_csv", "Load CSV", () => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.csv';
                    input.onchange = async (e) => {
                        const file = e.target.files[0];
                        if (file) {
                            const content = await file.text();
                            this.properties.csvText = content;
                            csvWidget.value = content;
                            this.resetDropdowns();
                            this.parseCSVToDropdowns(content);
                        }
                    };
                    input.click();
                }, {});
            }

            this.updateBackend = async function() {
                if (!this.id || this.id === -1) return;
                const payload = {};
                for (const [id, widget] of Object.entries(this.dropdownWidgets)) {
                    let value = widget.value;
                    payload[id] = value;
                    if (value === "random") {
                        payload[id + "_entries"] = widget.options.values.filter(v => v !== "random");
                    }
                }
                await fetchSend(MESSAGE_ROUTE, this.id, "update_selections", payload);
            };

            this.resetDropdowns = function() {
                for (const id in this.dropdownWidgets) {
                    const widget = this.dropdownWidgets[id];
                    const index = this.widgets.indexOf(widget);
                    if (index !== -1) {
                        this.widgets.splice(index, 1);
                    }
                }
                this.dropdownWidgets = {};
                
                if (this.outputs) {
                    for (let i = this.outputs.length - 1; i >= 0; i--) {
                        const output = this.outputs[i];
                        if (output.name !== "combined_selections") {
                            this.removeOutput(i);
                        }
                    }
                }
                
                this.setDirtyCanvas(true, true);
            };

            this.parseCSVToDropdowns = function(csvText) {
                if (!csvText) return;
                const rows = csvText.split(/\r?\n/).filter(r => r.trim() !== "");
                
                const newDropdownWidgets = {};
                
                for (const row of rows) {
                    let parts = row.split(",");
                    let id, options;

                    if (parts.length === 2 && parts[1].includes('"')) {
                        id = parts[0].replace(/^"|"$/g, "").trim();
                        options = parts[1].replace(/^"|"$/g, "").split(",").map(o => o.trim().replace(/^"|"$/g, ''));
                    } else if (parts.length > 1) {
                        id = parts[0].trim();
                        options = parts.slice(1).map(o => o.trim().replace(/^"|"$/g, ''));
                    } else {
                        continue;
                    }

                    if (this.properties.removeDuplicates === "true") {
                        options = [...new Set(options)];
                    }
                    if (options.length > 1) options.push("random");

                    let widget = this.dropdownWidgets[id];
                    if (!widget) {
                        const initialValue = (this.properties[id] !== undefined && options.includes(this.properties[id]))
                            ? this.properties[id]
                            : options[0];
                        widget = this.addWidget("combo", id, initialValue, async (value) => {
                            this.properties[id] = value;
                            await this.updateBackend();
                            return value;
                        }, { values: options });
                        
                        const existingOutput = this.outputs?.find(output => output.name === id);
                        if (!existingOutput) {
                            this.addOutput(id, "STRING");
                        }
                    } else {
                        widget.options.values = options;
                        if (widget.value && options.includes(widget.value)) {
                            widget.value = widget.value;
                        } else {
                            widget.value = options[0];
                        }
                    }
                    newDropdownWidgets[id] = widget;
                }

                this.dropdownWidgets = newDropdownWidgets;
                this.setDirtyCanvas(true, true);
                this.updateBackend().catch(() => {/* silent error */});
            };

            if (this.properties.csvText) {
                setTimeout(() => this.parseCSVToDropdowns(this.properties.csvText), 50);
            }
        });

        chainCallback(nodeType.prototype, "onConfigure", function(o) {
            if (this.properties.csvText) {
                this.parseCSVToDropdowns(this.properties.csvText);
            }
        });

        return nodeType;
    },
    
    setup(app) {
        const originalOnNodeRemoved = app.graph.onNodeRemoved;
        app.graph.onNodeRemoved = function(node) {
            if (node.type === "DN_CSVMultiDropDownNode") {
                fetchSend(MESSAGE_ROUTE, node.id, "remove_selection");
            }
            originalOnNodeRemoved?.apply(this, arguments);
        };
        api.addEventListener('reconnected', () => {
            // Find all DN_CSVMultiDropDownNode instances and send their selections
            for (const node of app.graph._nodes) {
                if (node.type === "DN_CSVMultiDropDownNode" && node.updateBackend) {
                    console.log("API reconnected - sending selections to backend");
                    setTimeout(() => {
                        node.updateBackend().catch(() => {/* silent error */});
                    }, 100);
                }
            }
        });
    }
})

