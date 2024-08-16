import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { getStorageValue, setStorageValue } from "../../scripts/utils.js";

const { chainCallback, getWidget, getWidgets, fetchApiSend } = await import("/extensions/ComfyUI_Dados_Nodes/common/js/utils.js");
const { createModal } = await import('/extensions/ComfyUI_Dados_Nodes/common/js/modal.js');
const { pinterest_modal } = await import('/extensions/ComfyUI_Dados_Nodes/common/js/pinterest_modal.js');

const boardDataUpdatedEvent = new Event('boardDataUpdated');
const fetchApiPinRoute = '/dadoNodes/pinterestNode/';
const baseUrl = window.location.origin + window.location.pathname.replace(/\/+$/, '');
const scriptUrl = `${baseUrl}/extensions/ComfyUI_Dados_Nodes/web/comfyui/pinterest_image.js`;

async function updateBackendBoardName(node) {
    const { 
        username: usernameWidget, 
        board_name: boardNameWidget
    } = await getWidgets(node, ["username", "board_name"]);

    const username = usernameWidget.value;
    const boardName = boardNameWidget.value;

    if (username && boardName) {
        try {
            const result = await fetchApiSend(fetchApiPinRoute, "update_selected_board_name", {
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
            const boardNames = await fetchApiSend(fetchApiPinRoute, "get_pinterest_board_names", {
                username: username,
            });

            const storedData = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
            if (!storedData[username]) {
                storedData[username] = { boards: [], selected: {} };
            }
            storedData[username].boards = boardNames.board_names;
            storedData[username].selected[node.id] = boardNames.board_names.includes(boardNameWidget.value) 
                ? boardNameWidget.value 
                : boardNames.board_names[0];
            setStorageValue("Pinterest_username_boards", JSON.stringify(storedData));

            document.dispatchEvent(boardDataUpdatedEvent);
            return boardNames.board_names;
        } catch (error) {
            console.error("Error fetching board names:", error);
        }
    }
}

async function setupBoardNameWidget(node) {
    const usernameWidget = await getWidget(node, "username");
    let username = usernameWidget?.value;
    let storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
    
    function getBoardData() {
        return storedBoards[username] || { boards: ["all"], selected: {} };
    }

    function updateUsername(newUsername) {
        if (newUsername === username) return;
        storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
        username = newUsername;
    }

    function updateStoredBoards(newValue) {
        let userBoardData = getBoardData();
        userBoardData.selected[node.id] = newValue;
        storedBoards[username] = userBoardData;
        setStorageValue("Pinterest_username_boards", JSON.stringify(storedBoards));
        document.dispatchEvent(boardDataUpdatedEvent);
    }

    const boardWidget = node.addWidget("combo", "board_name", getBoardData().selected[node.id] || "all", function(v) {
        handleBoardSelection(v, node);
        return v;
    }, { values: getBoardData().boards });
    
    async function handleBoardSelection(v, node) {
        try {
            const usernameWidget = await getWidget(node, "username");
            updateUsername(usernameWidget.value, node.id);
            updateStoredBoards(v);
            updateBackendBoardName(node);
        } catch (error) {
            console.error("Error handling board selection:", error);
        }
    }

    document.addEventListener('boardDataUpdated', () => {
        storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
        let userBoardData = getBoardData();
        boardWidget.options.values = userBoardData.boards;
        boardWidget.value = userBoardData.selected[node.id] || boardWidget.value;
    });

    updateBackendBoardName(node);
}

async function clearSelectedBoard(node) {
    const currentBoardNameWidget = await getWidget(node, "board_name");
    const storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards"));

    const matchingUsername = storedBoards ? Object.keys(storedBoards).find(username =>
        storedBoards[username]?.selected?.[node.id] === currentBoardNameWidget.value
    ) : null;
    
    if (matchingUsername) {
        delete storedBoards[matchingUsername].selected[node.id];
        if (Object.keys(storedBoards[matchingUsername].selected).length === 0) {
            delete storedBoards[matchingUsername];
        }
        setStorageValue("Pinterest_username_boards", JSON.stringify(storedBoards));
    }
}

app.registerExtension({
    name: "Dados.PinterestImageButton",
    async setup(app) {

        console.log("URL of pinterest_image.js:", scriptUrl);

        chainCallback(app.graph, 'onNodeRemoved', async function (removedNode) {
            if (removedNode.type === "PinterestImageNode") {
                /* console.log("(Dados.EventListeners) Node Removed :", removedNode.type, removedNode.id); */
                clearSelectedBoard(removedNode);
            }
        });
    },
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "PinterestImageNode") {
            chainCallback(LGraphNode.prototype, "configure", function(info) {
                if (info.type === "PinterestImageNode") {
                    this.previousSize = [...this.size];
                }
            });

            chainCallback(nodeType.prototype, 'onNodeCreated', async function () {
                
                await setupBoardNameWidget(this);
                const usernameWidget = await getWidget(this, "username");
                usernameWidget.callback = async (currentUsername) => {
                    const node = app.graph.getNodeById(this.id);
                    clearSelectedBoard(node);

                    const updatedBoardNames = await updateBoardNames(this);
                    if (updatedBoardNames) {
                        const boardNameWidget = await getWidget(this, "board_name");
                        let currentValue = boardNameWidget.value;

                        boardNameWidget.options.values = updatedBoardNames;

                        if (updatedBoardNames.includes(currentValue)) {
                            boardNameWidget.value = currentValue;
                        } else {
                            boardNameWidget.value = updatedBoardNames[0];
                        }

                        this.setDirtyCanvas(true);
                    }
                };
            
                /* this.addCustomWidget({
                    name: "Select Image",
                    type: "button",
                    callback: () => {
                        const contentDiv = document.createElement('div');
                        contentDiv.innerHTML = `<h2 id="modalTitle"></h2>`;
                        
                        const customLogic = async (modal, testString) => {

                            if (modal.config.nodeId) {
                                const result = await fetchApiSend("/dadoNodes/pinterestNode/", "common_test", {
                                  message: `Hello, API! from node ${modal.config.nodeId}. Test string: ${testString}`,
                                });
                                console.log("Reply:", result);
                            }
                            const titleElement = modal.view.contentWrapper.querySelector('#modalTitle');
                            titleElement.textContent = modal.config.title;
                        
                            const inputField = document.createElement('input');
                            inputField.type = 'text';
                            inputField.placeholder = 'Enter new title';
                        
                            const changeButton = document.createElement('button');
                            changeButton.textContent = 'Change Title';
                            changeButton.onclick = () => {
                                modal.config.title = inputField.value;
                                titleElement.textContent = modal.config.title;
                            };
                            const closeButton = document.createElement('button');
                            closeButton.textContent = 'Close Modal';
                            closeButton.onclick = () => {
                                modal.closeModal();
                            };
                        
                            modal.view.contentWrapper.appendChild(inputField);
                            modal.view.contentWrapper.appendChild(changeButton);
                            modal.view.contentWrapper.appendChild(closeButton);

                            const usernameInput = document.createElement('input');
                            usernameInput.type = 'text';
                            usernameInput.placeholder = 'Enter new username';
                        
                            const changeUsernameButton = document.createElement('button');
                            changeUsernameButton.textContent = 'Change Username';
                            changeUsernameButton.onclick = async () => {
                                const node = app.graph.getNodeById(modal.config.nodeId);
                                const usernameWidget = await getWidget(node, "username");
                                usernameWidget.value = usernameInput.value;
                                usernameWidget.callback(usernameInput.value);
                                node.setDirtyCanvas(true);
                            };
                        
                            modal.view.contentWrapper.appendChild(usernameInput);
                            modal.view.contentWrapper.appendChild(changeUsernameButton);
                        
                        };
                        
                        const modalConfig = {
                            content: contentDiv,
                            nodeId: this.id,
                            contentType: 'html',
                            onClose: () => console.log('Modal closed'),
                            customLogic: customLogic,
                            title: "Initial Title"
                        };
                        
                        createModal(modalConfig);
                    },
                }); */

                this.addCustomWidget({
                    name: "Select Image",
                    type: "button",
                    callback: pinterest_modal(this)
                });

                this.images = [];
                const nodeApiRoute = fetchApiPinRoute + this.id
                api.addEventListener(nodeApiRoute, ({ detail }) => {
                    if (detail["operation"] === "get_selected_board") {
                        // console.log("python backend requesting selected board name from node ", detail["node_id"]);
                        updateBackendBoardName(this)
                    }
                    if (detail["operation"] === "result") {
                        // console.log("board name", detail["result"]["board_name"]);
                        // console.log("image url", detail["result"]["image_url"]);

                        this.images = [detail["result"]["image_url"]];
                        this.loadedImage = null;
                        this.setDirtyCanvas(true);
                    
                    }
                });

                const computedSize = this.computeSize();
                const [width, height] = this.previousSize && this.previousSize.every(val => val !== undefined)
                    ? this.previousSize
                    : [350, computedSize[1]];
                this.setSize([width, height]);
                await updateBoardNames(this)
                this.setDirtyCanvas(true);
            });

            
            chainCallback(nodeType.prototype, 'onDrawBackground', function(ctx) {
                if (this.flags.collapsed || !this.images || !this.images.length) return;

                const MARGIN = 10;
                const DOUBLE_MARGIN = MARGIN * 2;
            
                const availableWidth = this.size[0] - DOUBLE_MARGIN;
                const initialHeight = this.computeSize()[1];
            
                if (!this.loadedImage) {
                    this.loadedImage = new Image();
                    this.loadedImage.src = this.images[0];
                    this.loadedImage.onload = () => {
                        if (!this.hasAdjustedHeight) {
                            const aspectRatio = this.loadedImage.height / this.loadedImage.width;
                            this.size[1] = initialHeight + Math.min(availableWidth, this.loadedImage.width) * aspectRatio + DOUBLE_MARGIN;
                            this.hasAdjustedHeight = true;
                        }
                        this.cachedImgAspectRatio = this.loadedImage.height / this.loadedImage.width;
                        this.setDirtyCanvas(true);
                    };
                    /* this.loadedImage.onerror = () => {
                        console.error('Failed to load image:', this.images[0]);
                        // maybe?!?
                    }; */
                }
            
                if (this.loadedImage.complete) {
                    const imgAspectRatio = this.cachedImgAspectRatio || this.loadedImage.height / this.loadedImage.width;
                    const availableHeight = this.size[1] - initialHeight - DOUBLE_MARGIN;
                    const imageWidth = Math.min(availableWidth, this.loadedImage.width, availableHeight / imgAspectRatio);
                    const imageHeight = imageWidth * imgAspectRatio;
            
                    ctx.drawImage(this.loadedImage, 
                        MARGIN + (availableWidth - imageWidth) / 2, 
                        initialHeight + MARGIN, 
                        imageWidth, imageHeight);
                }
            });
            
            
            
            chainCallback(nodeType.prototype, 'onResize', function(size) {
                // console.log("(Dados.PinterestImageButton) resizing :", this.size);
                this.setDirtyCanvas(true);
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

