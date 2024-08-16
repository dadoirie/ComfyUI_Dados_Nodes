import { api } from "../../../../scripts/api.js";

export function chainCallback(object, property, callback) {
  if (object == undefined) {
      console.error('Tried to add callback to non-existent object');
      return;
  }
  if (property in object) {
      const callback_orig = object[property];
      object[property] = function () {
          const r = callback_orig.apply(this, arguments);
          callback.apply(this, arguments);
          return r;
      };
  } else {
      object[property] = callback;
  }
}

export async function fetchApiSend(route, operation, data) {
  return api.fetchApi(route, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ op: operation, ...data })
  }).then(response => response.json());
}

export async function getWidget(node, name, maxRetries = 3) {
  const checkWidget = (retries = 0) => {
      return new Promise((resolve) => {
          const widget = node.widgets.find(w => w.name === name);
          if (widget) {
              resolve(widget);
          } else if (retries < maxRetries) {
              requestAnimationFrame(() => resolve(checkWidget(retries + 1)));
          } else {
              console.warn(`Widget "${name}" not found after ${maxRetries} attempts`);
              resolve(null);
          }
      });
  };

  return await checkWidget();
};

export async function getWidgets(node, target, maxRetries = 3) {
    const checkWidgets = (retries = 0) => {
      return new Promise((resolve) => {
        const result = {};
        const allFound = target.every(name => {
          const widget = node.widgets.find(w => w.name === name);
          if (widget) {
            result[name] = widget;
            return true;
          }
          return false;
        });
  
        if (allFound) {
          resolve(result);
        } else if (retries < maxRetries) {
          requestAnimationFrame(() => resolve(checkWidgets(retries + 1)));
        } else {
          console.warn(`Some widgets not found after ${maxRetries} attempts`);
          resolve(result);
        }
      });
    };
  
    return await checkWidgets();
}


