import { createModal } from "./modal.js";
import { fetchApiSend } from "./utils.js";

export function pinterest_modal(node) {
  return () => {
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
              const usernameWidget = await getWidget(node, "username");
              usernameWidget.value = usernameInput.value;
              usernameWidget.callback(usernameInput.value);
              node.setDirtyCanvas(true);
          };
      
          modal.view.contentWrapper.appendChild(usernameInput);
          modal.view.contentWrapper.appendChild(changeUsernameButton);
      };
      
      const modalConfig = {
          modal: "pinterest",
          contentType: 'html',
          title: "Initial Title",
          content: contentDiv,
          nodeId: node.id,
          customLogic: customLogic,
          onClose: () => console.log('Modal closed'),
      };
      
      createModal(modalConfig);
  };
}