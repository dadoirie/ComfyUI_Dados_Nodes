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

async function manageUrlWidget(node, action) {
    const usernameWidgetName = "username";
    const usernameWidget = node.widgets.find(w => w.name === usernameWidgetName);
    const widgetName = "image_url";
    const existingWidget = node.widgets.find(w => w.name === widgetName);
    const currentWidth = node.size[0];
    const currentHeight = node.size[1];
    
    switch (action) {
        case "add":
            if (!existingWidget) {
                widgetFactory.createWidget(node, {
                    name: widgetName,
                    type: "string",
                    value: "",
                    tooltip: "Enter the image URL"
                });
                console.log("URL widget added");
            }
            break;
        case "remove":
            if (existingWidget) {
                const index = node.widgets.indexOf(existingWidget);
                if (index > -1) {
                    node.widgets.splice(index, 1);
                    console.log("URL widget removed");
                }
            }
            break;
            case "toggle":
                if (usernameWidget) {
                    usernameWidget.value = "dado";
                    usernameWidget.callback(usernameWidget.value);
                } else {
                    console.log("Username widget not found");
                }
                break;
    }
    node.size = [currentWidth, currentHeight];
    node.setDirtyCanvas(true);
}


const widgetDataList = [
    /* {
        name: "username",
        type: "string",
        value: "",
        tooltip: "Pinterest username"
    }, */
    { 
        name: "url",
        type: "string",
        value: "",
        tooltip: "[WIP]\nUser Profile, Board, Section, Pin URLs\nupdates entire node inputs\nafter successful update URL input resets\n\n*Raw Image URLs are not supported and will throw an error*"
    },
    {
        name: "board",
        type: "dropdown",
        value: "all",
        options: ["all"],
        tooltip: "only if username is set\n`all` all users pins are in the pool (boards & sections)\n`board name` only pins of that board are in the pool"
    },
    {
        name: "section",
        type: "dropdown",
        value: "excluded",
        options: ["included", "excluded"],
        tooltip: "does nothing if selected board is `all`\n`included` boards sections are included in pool\n`excluded` boards sections are excluded from pool\n`section name` only pins of that section are in the pool"
    },
    {
        name: "api_requests",
        type: "dropdown",
        value: "live",
        options: ["cached", "live"],
        tooltip: "Select an option"
    },
    {
        name: "image_output",
        type: "dropdown",
        value: "chaotic draw",
        options: ["fixed", "chaotic draw", "circular shuffle"],
        tooltip: "Select an option"
    },
    {
        name: "image_resolution",
        type: "dropdown",
        value: "564x",
        options: ["474x", "chaotic draw", "circular shuffle"],
        tooltip: "Select an option"
    },
    {
        name: "Select Image",
        type: "button", action: function() { pinterest_modal(this)(); },
        tooltip: "Browse Pinterest for images"
    },
/*     { name: "Add Url Widget", type: "button", action: function() { manageUrlWidget(this, "add"); }, tooltip: "Add URL widget" },
    { name: "Remove Url Widget", type: "button", action: function() { manageUrlWidget(this, "remove"); }, tooltip: "Remove URL widget" },
    { name: "change username", type: "button", action: function() { manageUrlWidget(this, "toggle"); }, tooltip: "Toggle URL widget" }, */
];

const widgetFactory = {
    createWidget: (node, { name, type, value, options, tooltip, action }) => {
        const widgetTypes = {
            string: ["text", value => { widgetCallback(node, { name, value, type }); return value; }],
            dropdown: ["combo", value => { widgetCallback(node, { name, value, type }); return value; }, { values: options }],
            button: ["button", function() { action.call(node); widgetCallback(node, { name, type });}],
        };

        const [widgetType, callback, widgetOptions] = widgetTypes[type];
        const widget = node.addWidget(widgetType, name, value, callback, widgetOptions);
        widget.tooltip = tooltip;

        return widget;
    }
};

function widgetCallback(node, changedWidget) {
    // maybe even removing its callback completely ... lets see
    if (changedWidget.type === "button") {
        return;
    }
    console.log("CALLED");

    console.log(`\
        Widget [ ${changedWidget.name} ] changed
        New value: [${changedWidget.value}]
        Widget type: [${changedWidget.type}]
        Node ID: [${node.id}]`
    );

    if (changedWidget.name === "username") {
        handleUsernameChange(node);
    }

    console.log("FINISHED");
}

async function handleUsernameChange(node) {
    clearSelectedBoard(node);

    const updatedBoardNames = await getUserBoards(node);
    if (!updatedBoardNames) return;

    const widgets = await getWidgets(node, ["board"]);
    const boardWidget = widgets.board;
    if (!boardWidget) return;

    updateBoardNameWidget(boardWidget, updatedBoardNames);
    // node.setDirtyCanvas(true);
    
    boardWidget.callback(boardWidget.value);
}

function updateBoardNameWidget(widget, boardNames) {
    const currentValue = widget.value;
    widget.options = { values: boardNames };
    widget.value = boardNames.includes(currentValue) ? currentValue : boardNames[0];
}

async function updateBackendLegacy(node) {
    const { 
        username: usernameWidget, 
        board: boardWidget
    } = await getWidgets(node, ["username", "board"]);

    const username = usernameWidget.value;
    const boardName = boardWidget.value;

    if (username && boardName) {
        try {
            const result = await fetchApiSend(fetchApiPinRoute, "update_selected_board_name", {
                username: username,
                board: boardName,
                node_id: node.id
            });
            console.log("Board updated successfully:", result);
        } catch (error) {
            console.error("Error updating board:", error);
        }
    }
}

async function updateBackend(node) {
    const { 
        username: usernameWidget, 
    } = await getWidgets(node, ["username"]);

    const username = usernameWidget.value;

    if (username) {
        try {
            const result = await fetchApiSend(fetchApiPinRoute, "update_backend_inputs", {
                username: username,
                node_id: node.id
            });
            console.log("Backend inputs updated successfully:", result);
        } catch (error) {
            console.error("Error updating backend inputs:", error);
        }
    }
}

async function updateBoardNamesLegacy(node) {
    const { 
        username: usernameWidget, 
        board: boardWidget
    } = await getWidgets(node, ["username", "board"]);

    const username = usernameWidget.value;
    if (username) {
        try {
            const boardNames = await fetchApiSend(fetchApiPinRoute, "get_user_boards", {
                username: username,
                node_id: node.id,
            });

            const storedData = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
            if (!storedData[username]) {
                storedData[username] = { boards: [], selected: {} };
            }
            storedData[username].boards = boardNames.board_names;
            storedData[username].selected[node.id] = boardNames.board_names.includes(boardWidget.value) 
                ? boardWidget.value 
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

async function getUserBoards(node) {
    const widgets = await getWidgets(node, ["username"]);

    const username = widgets.username.value;
    if (username) {
        try {
            const boardNames = await fetchApiSend(fetchApiPinRoute, "get_user_boards", {
                username: username,
                node_id: node.id,
            });

            document.dispatchEvent(boardDataUpdatedEvent);
            return boardNames.board_names;
        } catch (error) {
            console.log("TRIGGERED")
            console.error("Error fetching board names:", error.message);
        }
    }
}


async function setupBoardNameWidgetLegacy(node) {
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

    const boardWidget = await getWidget(node, "board");
    boardWidget.options.values = getBoardData().boards;
    boardWidget.value = getBoardData().selected[node.id] || "all";

/*     const boardWidget = node.addWidget("combo", "board", getBoardData().selected[node.id] || "all", function(v) {
        handleBoardSelection(v, node);
        return v;
    }, { values: getBoardData().boards });
    
    async function handleBoardSelection(v, node) {
        try {
            const usernameWidget = await getWidget(node, "username");
            updateUsername(usernameWidget.value, node.id);
            updateStoredBoards(v);
            updateBackendLegacy(node);
        } catch (error) {
            console.error("Error handling board selection:", error);
        }
    } */

    document.addEventListener('boardDataUpdated', () => {
        storedBoards = JSON.parse(getStorageValue("Pinterest_username_boards")) || {};
        let userBoardData = getBoardData();
        boardWidget.options.values = userBoardData.boards;
        boardWidget.value = userBoardData.selected[node.id] || boardWidget.value;
    });

    updateBackendLegacy(node);
}

async function clearSelectedBoard(node) {
    const currentBoardNameWidget = await getWidget(node, "board");
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

    // doesn't make much sense with current error handling
    // for now it'll just listen silently in order avoid "unhandled message" alert
    // will see later if it can be used more effectively
    api.addEventListener("execution_interrupted", (event) => {
        // console.debug("execution_interrupted", event.detail)
    })
    api.addEventListener(nodeApiRoute, async ({ detail }) => {
        if (detail["operation"] === "get_selected_board") {
            // console.log("python backend requesting selected board name from node ", detail["node_id"]);
            updateBackendLegacy(node)
        }
        if (detail["operation"] === "get_inputs") {
            // console.log("python backend requesting selected board name from node ", detail["node_id"]);
                // Send the response back to the Python backend
            console.log("python backend requesting selected board name from node ", detail["node_id"]);

            const widgets = await getWidgets(node, ["username"]);
            fetchApiSend('/dadoNodes/pinterestNode/', 'critical_response', {
                message: widgets.username.value 
                    ? widgets.username.value
                    : "No username input provided"
            });

            updateBackend(node)
        }
        if (detail["operation"] === "result") {
            // console.log("board name", detail["result"]["board"]);
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

    async nodeCreated(node) {
        console.log("(Dados.EventListeners) Node Created :", node);
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
                const usernameWidget = this.widgets.find(w => w.name === "username");
                usernameWidget.callback = (value) => widgetCallback(this, { name: "username", value, type: "string" });
                
                // NEW LOGIC START
                const widgetCreator = (widgetData) => {
                    return widgetFactory.createWidget(this, widgetData);
                };
                
                // Create widgets
                widgetDataList.map(widgetData => widgetCreator(widgetData));
                const usernameWidgetNew = await getWidget(this, "username");
                console.log("(Dados.EventListeners) Username Widget :", usernameWidgetNew);
                // NEW LOGIC END
                await setupBoardNameWidgetLegacy(this);
                
                // const usernameWidget = await getWidget(this, "username");

                /* usernameWidget.callback = async (whatsthis) => {
                    const node = app.graph.getNodeById(this.id);
                    clearSelectedBoard(node);

                    const updatedBoardNames = await updateBoardNamesLegacy(this);
                    if (updatedBoardNames) {
                        const boardNameWidget = await getWidget(this, "board");
                        let currentValue = boardNameWidget.value;

                        boardNameWidget.options.values = updatedBoardNames;

                        if (updatedBoardNames.includes(currentValue)) {
                            boardNameWidget.value = currentValue;
                        } else {
                            boardNameWidget.value = updatedBoardNames[0];
                        }

                        this.setDirtyCanvas(true);
                    }
                }; */

/*                 this.addCustomWidget({
                    name: "Select Image",
                    type: "button",
                    callback: pinterest_modal(this)
                }); */

                this.images = [];
                setupEventListener(this);

                const computedSize = this.computeSize();
                const [width, height] = this.previousSize && this.previousSize.every(val => val !== undefined)
                    ? this.previousSize
                    : [350, computedSize[1]];
                this.setSize([width, height]);
                // await updateBoardNamesLegacy(this)

                this.setDirtyCanvas(true);
            });

            
            chainCallback(nodeType.prototype, 'onDrawBackground', function(ctx) {
                if (this.flags.collapsed || !this.images || !this.images.length) return;
            
                const MARGIN = 10;
                const availableWidth = this.size[0] - MARGIN * 2;
                const initialHeight = this.computeSize()[1];
            
                const loadAndDrawImage = () => {
                    if (!this.loadedImage) {
                        this.loadedImage = new Image();
                        this.loadedImage.src = this.images[0];
                        this.loadedImage.onload = () => {
                            this.cachedImgAspectRatio = this.loadedImage.height / this.loadedImage.width;
                            if (!this.hasAdjustedHeight) {
                                this.size[1] = initialHeight + Math.min(availableWidth, this.loadedImage.width) * this.cachedImgAspectRatio;
                                this.hasAdjustedHeight = true;
                            }
                            this.setDirtyCanvas(true);
                            loadAndDrawImage();
                        };
                    } else if (this.loadedImage.complete) {
                        const availableHeight = this.size[1] - initialHeight - MARGIN;
                        const imageWidth = Math.min(availableWidth, this.loadedImage.width, availableHeight / this.cachedImgAspectRatio);
                        const imageHeight = imageWidth * this.cachedImgAspectRatio;
            
                        ctx.drawImage(this.loadedImage, 
                            MARGIN + (availableWidth - imageWidth) / 2, 
                            initialHeight, 
                            imageWidth, imageHeight);
                    }
                };
            
                loadAndDrawImage();
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


