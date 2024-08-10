import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
// import { getStorageValue, setStorageValue } from "../../scripts/utils.js";

app.registerExtension({
    name: "Dados.PinterestImageButton",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PinterestImageNode") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                let node = this;
                
                const usernameWidget = this.widgets.find(w => w.name === "username");
    
                this.addWidget("combo", "board_name", "all", function(v) {
                    updateBackendBoardName(node);
                    return v;
                }, { values: ["all"] });

                const boardNameWidget = this.widgets.find(w => w.name === "board_name");
                const index = this.widgets.indexOf(boardNameWidget);
                
                if (index !== -1) {
                    this.addCustomWidget({
                        name: "Update Boards",
                        type: "button",
                        callback: () => updateBoardNames(this),
                    });
                }
                
                this.setSize([this.size[0], this.computeSize()[1]]);
                console.log("Node created: ", this);
                setTimeout(() => updateBoardNames(this), 0);
                setTimeout(() => updateBackendBoardName(this), 0);
                return this;
            };
        }
    }
});

function updateBoardNames(node) {
    if (!node.widgets || !node.widgets.length) {
        console.log("Widgets not initialized yet");
        return;
    }
    const usernameWidget = node.widgets.find(w => w.name === "username");
    const boardNameWidget = node.widgets.find(w => w.name === "board_name");
    console.log("Updating board names for username:", usernameWidget.value);

    const username = usernameWidget.value;
    if (username) {
        return api.fetchApi('/pinterestimageboard/get_board_names', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username })
        })
        .then(response => response.json())
        .then(boardNames => {
            let currentValue = boardNameWidget.value;
            boardNameWidget.options.values = boardNames.board_names;

            if (boardNames.board_names.includes(currentValue)) {
                boardNameWidget.value = currentValue;
            } else {
                boardNameWidget.value = boardNames.board_names[0];
            }

            boardNameWidget.callback(boardNameWidget.value);
            updateBackendBoardName(node);
            app.graph.setDirtyCanvas(true);

        })
        .catch(error => {
            console.error("Error fetching board names:", error);
        });
    }
}

async function updateBackendBoardName(node) {
    if (!node.widgets || !node.widgets.length) {
        console.log("Widgets not initialized yet");
        return;
    }
    const usernameWidget = node.widgets.find(w => w.name === "username");
    const boardNameWidget = node.widgets.find(w => w.name === "board_name");
    
    await api.fetchApi('/pinterestimageboard/update_board', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: usernameWidget.value,
            board_name: boardNameWidget.value,
            node_id: node.id 
        })
    });
}
