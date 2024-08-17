import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyDialog } from "../../scripts/ui.js";
import { getStorageValue, setStorageValue } from "../../scripts/utils.js";

const { chainCallback, getWidget, getWidgets, fetchApiSend } = await import("/extensions/ComfyUI_Dados_Nodes/common/js/utils.js");
const { pinterest_modal } = await import('/extensions/ComfyUI_Dados_Nodes/common/js/pinterest_modal.js');

const boardDataUpdatedEvent = new Event('boardDataUpdated');
const fetchApiPinRoute = '/dadoNodes/pinterestNode/';
const baseUrl = window.location.origin + window.location.pathname.replace(/\/+$/, '');
const scriptUrl = `${baseUrl}/extensions/ComfyUI_Dados_Nodes/web/comfyui/pinterest_image.js`;

async function updateBackend(node) {
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
                node_id: node.id,
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
            if (error instanceof Response) {
                error.text().then(text => {
                    console.error("Error response text:", text);
                });
            } else {
                console.error("Error details:", error.toString());
            }
        }
    }
}

async function setupBoardNameWidget(node) {
    const usernameWidget = await getWidget(node, "username");
    if (usernameWidget.value === undefined) {
        return;
    }
    
    let username = usernameWidget.value;
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
            updateBackend(node);
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

    updateBackend(node);
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

function setupEventListener(node) {
    const nodeApiRoute = fetchApiPinRoute + node.id
    const originalOnDrawForeground = node.onDrawForeground || node.__proto__.onDrawForeground;

    api.addEventListener(nodeApiRoute, ({ detail }) => {
        if (detail["operation"] === "get_selected_board") {
            // console.log("python backend requesting selected board name from node ", detail["node_id"]);
            updateBackend(node)
        }
        if (detail["operation"] === "result") {
            // console.log("board name", detail["result"]["board_name"]);
            // console.log("image url", detail["result"]["image_url"]
            node.images = [detail["result"]["image_url"]];
            node.loadedImage = null;
            node.setDirtyCanvas(true);
        
        }
        if (detail["operation"] === "user_not_found") {
            console.error("error", detail["message"]);
            
            const errorDialog = new ComfyDialog();
            errorDialog.show(detail["message"]);
        
            node.hasError = true;
            node.errorMessage = detail["message"];
        
            node.onDrawForeground = function(ctx) {
                if (originalOnDrawForeground) {
                    originalOnDrawForeground.call(this, ctx);
                }
            
                if (this.hasError) {
                    ctx.strokeStyle = "#FF0000";
                    ctx.lineWidth = 2;
                    ctx.strokeRect(0, 0, this.size[0], this.size[1]);
                }
            };

            node.setDirtyCanvas(true);
        }
        if (detail["operation"] === "user_found") {
            if (node.hasError) {
                node.hasError = false;
                node.errorMessage = null;
            }
            node.isBlinking = true;        
            
            node.onDrawForeground = function(ctx) {
                if (originalOnDrawForeground) {
                    originalOnDrawForeground.call(this, ctx);
                }
                
                if (this.isBlinking) {
                    ctx.strokeStyle = "#228B22";
                    ctx.lineWidth = 1;
                    ctx.strokeRect(0, 0, this.size[0], this.size[1]);
                }
            };
        
            setTimeout(() => {
                node.isBlinking = false;
                node.onDrawForeground = originalOnDrawForeground;
                node.setDirtyCanvas(true);
            }, 250);
            
            node.setDirtyCanvas(true);
        }
        
    });
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
                    console.log("(Dados.EventListeners) Node Configured :", this.type, this.id, this.size);
                    console.log("(Dados.EventListeners) Node :", this);
                }
            });

            chainCallback(nodeType.prototype, 'onNodeCreated', async function () {
                
                await setupBoardNameWidget(this);
                const usernameWidget = await getWidget(this, "username");
                usernameWidget.callback = async (whatsthis) => {
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

                this.addCustomWidget({
                    name: "Select Image",
                    type: "button",
                    callback: pinterest_modal(this)
                });

                this.images = [];
                setupEventListener(this);

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

api.addEventListener("executing", async ({ detail }) => {
    const nodeId = parseInt(detail);
    if (!isNaN(nodeId)) {
        const node = app.graph.getNodeById(nodeId);
        if (node.type === "PinterestImageNode") {
            node.hasError = false;
            node.errorMessage = null;

            const originalOnDrawForeground = node.onDrawForeground || node.__proto__.onDrawForeground;
            node.onDrawForeground = function(ctx) {
                if (originalOnDrawForeground) {
                    originalOnDrawForeground.call(this, ctx);
                }
            };

            node.setDirtyCanvas(true);
        }
    }
});

