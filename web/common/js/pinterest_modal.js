import { createModal } from "./modal.js";
import { fetchApiSend, getWidgets } from "./utils.js";
import { getIcon } from "./svg_icons.js";

export function pinterest_modal(node) {
  return () => {
    const contentDiv = document.createElement('div');

    const loadCSS = () => {
      if (!document.querySelector('link[href$="/pinterest_modal.css"]')) {
        const cssLink = document.createElement('link');
        cssLink.rel = 'stylesheet';
        cssLink.href = '/extensions/ComfyUI_Dados_Nodes/common/css/dn_pinterest_modal.css';
        document.head.appendChild(cssLink);
      }
    };

    const customLogic = async (modal, testString) => {
      if (modal.config.nodeId) {
        const result = await fetchApiSend("/dadoNodes/pinterestNode/", "common_test", {
          message: `Hello, API! from node ${modal.config.nodeId}. Test string: ${testString}`,
        });
        console.log("Reply:", result);
      }

      const topBar = document.createElement('div');
      topBar.className = 'dn_pin_top_bar';

      const pinterestIcon = document.createElement('div');
      pinterestIcon.innerHTML = getIcon('pinterest');
      pinterestIcon.className = 'dn_pinterest_icon';

      const usernameInput = document.createElement('input');
      usernameInput.type = 'text';
      usernameInput.placeholder = 'Enter Pinterest username';
      usernameInput.className = 'dn_username_input';
      
      const searchIcon = document.createElement('div');
      searchIcon.className = 'dn_search_icon';
      searchIcon.innerHTML = getIcon('search');
      searchIcon.onclick = () => {
        console.log('Search icon clicked');
        // Perform search logic here
      };
      
      usernameInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          console.log('Enter key pressed');
          // Perform search logic here
        }
      });
      
      const usernameWrapper = document.createElement('div');
      usernameWrapper.className = 'dn_username_wrapper';
      usernameWrapper.appendChild(usernameInput);
      usernameWrapper.appendChild(searchIcon);

      const changeUsernameButton = document.createElement('button');
      changeUsernameButton.textContent = 'Change Username';
      changeUsernameButton.onclick = async () => {
        const widgets = await getWidgets(node, ["username"]);
        const usernameWidget = widgets.username;
        usernameWidget.value = usernameInput.value;
        usernameWidget.callback(usernameInput.value);
        node.setDirtyCanvas(true);
      };

      // topBar.appendChild(pinterestIcon);
      topBar.appendChild(usernameWrapper);
      topBar.appendChild(changeUsernameButton);

      modal.view.contentWrapper.appendChild(topBar);
    };

    const modalConfig = {
      modal: "pinterest",
      content: contentDiv,
      nodeId: node.id,
      customLogic: customLogic,
      onClose: () => console.log('Modal closed'),
    };

    loadCSS();
    createModal(modalConfig);
  };
}
