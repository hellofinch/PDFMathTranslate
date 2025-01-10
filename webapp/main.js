// Modules to control application life and create native browser window
const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const { exec } = require('child_process');
const http = require('http');
const kill = require('tree-kill');

let processInstance;

// Function to load port from config file
const getPortFromConfig = () => {
  const configPath = path.join(process.env.HOME || process.env.USERPROFILE, '.config', 'PDFMathTranslate', 'config.json');
  try {
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
      return config.gradio_port || 12366; // Fallback to default port 12366
    }
  } catch (error) {
    console.error(`Failed to load config: ${error.message}`);
  }
  return 12366; // Default port
};

const port = getPortFromConfig();
const targetURL = `http://localhost:${port}/`;

const createWindow = () => {
  const mainWindow = new BrowserWindow({
    width: 1280,
    height: 880,
    show: false, // Use 'ready-to-show' event to show window
  });

  Menu.setApplicationMenu(null);

  mainWindow.on('ready-to-show', () => {
    mainWindow.show();
  });

  // 加载指定的网页
  mainWindow.loadURL(targetURL);

  ipcMain.on('window-close', () => {
    if (processInstance && processInstance.pid) {
      kill(processInstance.pid, 'SIGTERM', (err) => {
        if (err) {
          console.error(`Failed to kill process: ${err.message}`);
        } else {
          console.log(`Successfully killed process with PID: ${processInstance.pid}`);
        }
      });
    } else {
      console.warn('No process is running.');
    }
  });

  mainWindow.on('closed', () => {
    ipcMain.removeAllListeners('window-close');
  });
};

app.whenReady().then(() => {
  processInstance = exec('pdf2zh -i --electron', (error, stdout, stderr) => {
    if (error) {
      console.error(`Error: ${error.message}`);
      app.quit();
      return;
    }
    console.log(`stdout: ${stdout}`);
  });

  createWindow();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('window-all-closed', () => {
  if (processInstance && processInstance.pid) {
    kill(processInstance.pid, 'SIGTERM', (err) => {
      if (err) {
        console.error(`Failed to kill process: ${err.message}`);
      } else {
        console.log(`Successfully killed process with PID: ${processInstance.pid}`);
      }
    });
  } else {
    console.warn('No process is running.');
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
