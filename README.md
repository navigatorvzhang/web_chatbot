# Web Chatbot

## Setup and Running

### 1. Install dependencies
```bash
pip install flask flask-cors openai
npm install
```

### 2. Start both servers
Use the provided script to start both Flask and Node.js servers:
```bash
node start-servers.js
```

Or start them individually:
- Flask server: `python chatbot.py`
- Node.js server: `node server.js`

### 3. Access the web interface
Open your browser and navigate to http://localhost:3000

## Troubleshooting

### "Unable to connect to server" error
This usually happens when:

1. **Flask server isn't running**
   - Make sure Python server is running with `python chatbot.py`
   - Check terminal for any Python errors

2. **CORS issues**
   - Ensure Flask CORS is properly configured
   - Check browser console for CORS errors

3. **Port conflicts**
   - Make sure ports 3000 and 5000 are available
   - No other applications are using these ports

4. **Network issues**
   - Check if localhost is accessible
   - Try restarting both servers

### For other issues
Check the console logs in both:
- Browser developer tools (F12)
- Terminal where servers are running
