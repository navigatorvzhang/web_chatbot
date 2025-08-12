const { spawn } = require('child_process');
const path = require('path');

console.log('Starting Flask server...');
const flaskServer = spawn('python', ['chatbot.py'], {
    cwd: path.join(__dirname),
    stdio: 'inherit'
});

flaskServer.on('error', (err) => {
    console.error('Failed to start Flask server:', err);
});

console.log('Starting Node.js server...');
const nodeServer = spawn('node', ['server.js'], {
    cwd: path.join(__dirname),
    stdio: 'inherit'
});

nodeServer.on('error', (err) => {
    console.error('Failed to start Node.js server:', err);
});

process.on('SIGINT', () => {
    console.log('Stopping servers...');
    flaskServer.kill();
    nodeServer.kill();
    process.exit();
});

console.log('Both servers started. Visit http://localhost:3000 to use the chat interface.');
console.log('Press Ctrl+C to stop both servers.');
