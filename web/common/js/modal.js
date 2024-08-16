class ModalView {
  constructor() {
    this.loadCSS();
    this.overlay = document.createElement('div');
    this.overlay.className = 'dn_overlay';

    this.modal = document.createElement('div');
    this.modal.className = 'dn_modal';

    this.contentWrapper = document.createElement('div');
    this.contentWrapper.className = 'dn_content_wrapper';

    this.resizeHandle = document.createElement('div');
    this.resizeHandle.className = 'dn_resize_handle';

    this.closeButton = document.createElement('button');
    this.closeButton.className = 'dn_close_button';
    this.closeButton.textContent = '×';

    this.modal.appendChild(this.resizeHandle);
    this.modal.appendChild(this.closeButton);
    this.modal.appendChild(this.contentWrapper);

    this.modal.tabIndex = -1;
    // Set initial styles
    this.modal.style.opacity = '0';
    this.modal.style.transform = 'translate(-50%, -50%) scale(0)';
    this.overlay.style.opacity = '0';
  }

  loadCSS() {
    if (!document.querySelector('link[href$="/dn_modal.css"]')) {
      const cssLink = document.createElement('link');
      cssLink.rel = 'stylesheet';
      cssLink.href = '/extensions/ComfyUI_Dados_Nodes/common/css/dn_modal.css';
      document.head.appendChild(cssLink);
    }
  }

  render() {
    document.body.appendChild(this.overlay);
    document.body.appendChild(this.modal);
    
    // Force a reflow to ensure styles are applied before animation
    this.modal.offsetHeight;
}

  setContent(content) {
    this.contentWrapper.appendChild(content);
  }

  show() {
    requestAnimationFrame(() => {
        this.modal.style.opacity = '1';
        this.modal.style.transform = 'translate(-50%, -50%) scale(1)';
        this.overlay.style.opacity = '1';
        this.modal.focus();
    });
}

  close() {
    this.contentWrapper.style.opacity = '0';
    this.overlay.style.opacity = '0';
    this.modal.style.transition = 'transform 0.15s ease-in';
    this.modal.style.transform = 'translate(-50%, -50%) scale(0)';
  }

  remove() {
    this.modal.remove();
    this.overlay.remove();
  }
}

class ModalModel {
  constructor(config) {
    this.view = new ModalView();
    this.config = config;
    this.setupEventListeners();
    this.customLogic = config.customLogic || (() => {});
  }

  setupEventListeners() {
    this.view.closeButton.onclick = () => this.closeModal();
    this.view.overlay.onclick = () => this.closeModal();
    document.addEventListener('keydown', (event) => this.handleEscapeKey(event));
    this.view.modal.onclick = (event) => event.stopPropagation();
    this.setupResize();
  }

  setupResize() {
    let isResizing = false;
    let originalWidth, originalHeight, originalX, originalY;

    const initResize = (e) => {
        e.preventDefault();
        isResizing = true;
        originalWidth = this.view.modal.offsetWidth;
        originalHeight = this.view.modal.offsetHeight;
        originalX = originalWidth - (e.clientX - this.view.modal.offsetLeft);
        originalY = originalHeight - (e.clientY - this.view.modal.offsetTop);
        document.addEventListener('mousemove', resize, false);
        document.addEventListener('mouseup', stopResize, false);
    };

    const resize = (e) => {
        if (isResizing) {
            const rect = this.view.modal.getBoundingClientRect();
            const newWidth = e.clientX - rect.left;
            const newHeight = e.clientY - rect.top;
            const maxWidth = window.innerWidth * 0.9;
            const maxHeight = window.innerHeight * 0.9;
            const minWidth = window.innerWidth * 0.2;
            const minHeight = window.innerHeight * 0.2;

            if (newWidth >= minWidth && newWidth <= maxWidth) {
                this.view.modal.style.width = newWidth + 'px';
            }
            if (newHeight >= minHeight && newHeight <= maxHeight) {
                this.view.modal.style.height = newHeight + 'px';
            }
        }
    };

    const stopResize = () => {
      isResizing = false;
      document.removeEventListener('mousemove', resize, false);
      document.removeEventListener('mouseup', stopResize, false);
    };

    this.view.resizeHandle.addEventListener('mousedown', initResize, false);
  }

  handleEscapeKey(event) {
    if (event.key === 'Escape') {
      this.closeModal();
    }
  }

  closeModal() {
    this.view.close();
    setTimeout(() => {
      this.view.remove();
      if (this.config.onClose && typeof this.config.onClose === 'function') {
        this.config.onClose();
      }
    }, 150);
  }

  render() {
    this.processContent();
    this.view.render();
    setTimeout(() => this.view.show(), 10);
  }

  async processContent() {
    let testString = 'test from modal';
    if (this.config.content) {
      this.view.setContent(this.config.content);
    }
    if (typeof this.config.customLogic === 'function') {
      await this.config.customLogic(this, testString);
    }
    // ... rest of the method ...
  }
}

// Main export function
export function createModal(config) {
  const modalModel = new ModalModel(config);
  modalModel.render();
  return modalModel;
}
