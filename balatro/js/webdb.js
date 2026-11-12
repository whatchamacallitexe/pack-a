(function(global) {
  if (typeof global.__getWebDB !== 'function') {
    global.__getWebDB = function(name) {
      try {
        if (global.localStorage) {
          return global.localStorage.getItem(name);
        }
      } catch (err) {
        if (global.console && global.console.warn) {
          global.console.warn('Unable to access localStorage for __getWebDB:', err);
        }
      }
      return null;
    };
  }

  if (typeof global.__setWebDB !== 'function') {
    global.__setWebDB = function(name, value) {
      try {
        if (global.localStorage) {
          global.localStorage.setItem(name, value);
          return true;
        }
      } catch (err) {
        if (global.console && global.console.warn) {
          global.console.warn('Unable to access localStorage for __setWebDB:', err);
        }
      }
      return false;
    };
  }
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : window));
