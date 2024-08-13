import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { getStorageValue, setStorageValue } from "../../scripts/utils.js";

import { chainCallback, getWidget, getWidgets } from "./utils.js";

const boardDataUpdatedEvent = new Event('boardDataUpdated');

async function nodeApiRouter(operation, data) {
    return api.fetchApi('/dadoNodes/pinterestNode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ op: operation, ...data })
    }).then(response => response.json());
}

async function updateBackendBoardName(node) {
    const { 
        username: usernameWidget, 
        board_name: boardNameWidget
    } = await getWidgets(node, ["username", "board_name"]);

    const username = usernameWidget.value;
    const boardName = boardNameWidget.value;

    if (username && boardName) {
        try {
            const result = await nodeApiRouter("update_selected_board_name", {
                username: username,
                board_name: boardName,
                node_id: node.id
            });
            console.log("Board updated successfully:", result);
        } catch (error) {
            console.error("Error updating board:", error);
        }
    }
}

async function updateBoardNames(node) {
const { 
        username: usernameWidget, 
        board_name: boardNameWidget
    } = await getWidgets(node, ["username", "board_name"]);

    const username = usernameWidget.value;
    if (username) {
        try {
            const boardNames = await nodeApiRouter("get_pinterest_board_names", { username });
            let currentValue = boardNameWidget.value;
            boardNameWidget.options.values = boardNames.board_names;

            if (boardNames.board_names.includes(currentValue)) {
                boardNameWidget.value = currentValue;
            } else {
                boardNameWidget.value = boardNames.board_names[0];
            }

            boardNameWidget.callback(boardNameWidget.value);

            const storedData = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
            if (!storedData[username]) {
                storedData[username] = { boards: [], selected: {} };
            }
            storedData[username].boards = boardNames.board_names;
            storedData[username].selected[node.id] = boardNameWidget.value;
            setStorageValue("Pinterest_username_boards", JSON.stringify(storedData));

            setStorageValue("Pinterest_username_boards", JSON.stringify(storedData));
            document.dispatchEvent(boardDataUpdatedEvent);
        } catch (error) {
            console.error("Error fetching board names:", error);
        }
    }
}

async function setupBoardNameWidget(node) {
    const usernameWidget = await getWidget(node, "username");
    const username = usernameWidget?.value;
    let storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
    
    function getBoardData() {
        return storedBoards[username] || { boards: ["all"], selected: {} };
    }

    function updateStoredBoards(newValue) {
        let userBoardData = getBoardData();
        userBoardData.selected[node.id] = newValue;
        storedBoards[username] = userBoardData;
        setStorageValue("Pinterest_username_boards", JSON.stringify(storedBoards));
    }

    const boardWidget = node.addWidget("combo", "board_name", getBoardData().selected[node.id] || "all", function(v) {
        console.log("Updating board selection for node:", node.id);
        updateStoredBoards(v);
        updateBackendBoardName(node);
        return v;
    }, { values: getBoardData().boards });

    document.addEventListener('boardDataUpdated', () => {
        storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
        let userBoardData = getBoardData();
        boardWidget.options.values = userBoardData.boards;
        boardWidget.value = userBoardData.selected[node.id] || boardWidget.value;
    });

    updateBackendBoardName(node);
}


app.registerExtension({
    name: "Dados.PinterestImageButton",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PinterestImageNode") {
            chainCallback(nodeType.prototype, 'onNodeCreated', async function () {
                const workflowId = app.graph.workflow_id;
                console.log("Workflow ID:", workflowId);
                await setupBoardNameWidget(this);
            
                this.addCustomWidget({
                    name: "Update Boards",
                    type: "button",
                    callback: () => updateBoardNames(this),
                });

                this.setSize([375, this.computeSize()[1]]);
                app.graph.setDirtyCanvas(true);
            });
        }
    }
});

/* api.addEventListener("executing", async ({ detail }) => {
    const nodeId = parseInt(detail);
    if (!isNaN(nodeId)) {
        const node = app.graph.getNodeById(nodeId);
        if (node.type === "PinterestImageNode") {
            // updateBackendBoardName(node);
            console.log(node);
            console.log("Output data for slot 1:", node.getOutputInfo(0));
        }
    }
  }); */