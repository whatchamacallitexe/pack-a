var Module = typeof Module !== 'undefined' ? Module : {};

(function() {
  Module.expectedDataFileDownloads = Module.expectedDataFileDownloads || 0;
  Module.finishedDataFileDownloads = Module.finishedDataFileDownloads || 0;

  function loadManifest(url) {
    if (typeof fetch === 'function') {
      return fetch(url).then(function(response) {
        if (!response.ok) {
          throw new Error('Failed to fetch ' + url + ' (' + response.status + ')');
        }
        return response.json();
      });
    }

    return new Promise(function(resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', url, true);
      xhr.responseType = 'json';
      xhr.onload = function() {
        if (xhr.status === 200 || xhr.status === 0) {
          if (xhr.response) {
            resolve(xhr.response);
          } else {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch (err) {
              reject(err);
            }
          }
        } else {
          reject(new Error('Failed to fetch ' + url + ' (' + xhr.status + ')'));
        }
      };
      xhr.onerror = function() {
        reject(new Error('Network error while fetching ' + url));
      };
      xhr.send(null);
    });
  }

  Module.preRun = Module.preRun || [];
  Module.preRun.push(function() {
    var dependencyId = 'data-preload';
    Module.addRunDependency(dependencyId);

    if (Module.setStatus) {
      Module.setStatus('Loading asset manifest...');
    }

    loadManifest('data/manifest.json').then(function(files) {
      Module['FS_createPath']('/', 'data', true, true);
      var createdDirs = {
        '/data': true
      };

      function ensureDirectory(relativePath) {
        var currentDir = '/data';
        if (!relativePath) return currentDir;
        var parts = relativePath.split('/');
        for (var i = 0; i < parts.length; i++) {
          var part = parts[i];
          if (!part) continue;
          var nextDir = currentDir + '/' + part;
          if (!createdDirs[nextDir]) {
            Module['FS_createPath'](currentDir, part, true, true);
            createdDirs[nextDir] = true;
          }
          currentDir = nextDir;
        }
        return currentDir;
      }

      if (!files || files.length === 0) {
        if (Module.setStatus) {
          Module.setStatus('No assets listed in manifest.');
        }
        Module.removeRunDependency(dependencyId);
        return;
      }

      var total = files.length;
      var remaining = total;

      function updateProgress() {
        if (!Module.setStatus) return;
        if (remaining > 0) {
          Module.setStatus('Preloading assets... (' + (total - remaining) + '/' + total + ')');
        } else {
          Module.setStatus('All assets loaded.');
        }
      }

      function onAssetComplete() {
        remaining--;
        updateProgress();
        if (remaining === 0) {
          Module.removeRunDependency(dependencyId);
        }
      }

      function onAssetError(path, error) {
        console.error('Failed to preload asset ' + path + ':', error);
        onAssetComplete();
      }

      updateProgress();

      files.forEach(function(relativePath) {
        var segments = relativePath.split('/');
        var fileName = segments.pop();
        var parentRelativePath = segments.join('/');
        var parentDir = ensureDirectory(parentRelativePath);
        Module['FS_createPreloadedFile'](parentDir, fileName, 'data/' + relativePath, true, true, function() {
          onAssetComplete();
        }, function(error) {
          onAssetError(relativePath, error);
        });
      });
    }).catch(function(error) {
      console.error('Unable to load asset manifest:', error);
      Module.removeRunDependency(dependencyId);
    });
  });
})();
