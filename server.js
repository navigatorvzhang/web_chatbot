const express = require('express');
const { PythonShell } = require('python-shell');
const bodyParser = require('body-parser');
const path = require('path');

const app = express();
app.use(bodyParser.json());
app.use(express.static('public'));

function callPythonScript(message, callback) {
    const options = {
        mode: 'json',
        pythonOptions: ['-u'], // Unbuffered output
        env: { ...process.env, PYTHON_SHELL: '1' }, // Suppress Flask logs
    };

    const pyshell = new PythonShell('chatbot.py', options);

    pyshell.send(JSON.stringify({ message }));

    pyshell.on('message', (data) => {
        if (data && typeof data === 'object') {
            callback(null, data);
        } else {
            callback(new Error('Invalid JSON response from Python script'));
        }
    });

    pyshell.on('error', (err) => {
        callback(err);
    });

    pyshell.end((err) => {
        if (err) {
            console.error('PythonShell Error:', err);
        }
    });
}

app.get('/init', (req, res) => {
    console.log('Initializing chat session...');
    let options = {
        mode: 'text', // Change to text mode to handle the output manually
        pythonPath: 'python3',
        scriptPath: path.join(__dirname),
        args: ['--init'],
        pythonOptions: ['-u']  // Unbuffered output
    };

    PythonShell.run('chatbot.py', options)
        .then(results => {
            console.log('Init raw response:', results);
            try {
                // Try to parse the last line as JSON (most likely the actual result)
                const lastLine = results[results.length - 1];
                const response = JSON.parse(lastLine);
                console.log('Init parsed response:', response);
                res.json(response);
            } catch (err) {
                console.error('JSON parse error:', err);
                res.status(500).json({ 
                    status: 'error',
                    message: 'Failed to parse Python response' 
                });
            }
        })
        .catch(err => {
            console.error('Init Error:', err);
            res.status(500).json({ 
                status: 'error',
                message: 'Failed to initialize chat session'
            });
        });
});

app.post('/chat', (req, res) => {
    const { message, context } = req.body;
    console.log('Processing chat request:', message.substring(0, 30) + '...');
    
    let options = {
        mode: 'json',
        scriptPath: path.join(__dirname),
        pythonPath: 'python3',
        args: ['--chat', JSON.stringify({ message, context })],
        pythonOptions: ['-u']  // Unbuffered output
    };

    PythonShell.run('chatbot.py', options)
        .then(results => {
            if (results && results.length > 0) {
                const response = results[0];
                if (response.error) {
                    console.error('Python Error:', response.error);
                    res.status(500).json({ error: response.error });
                } else {
                    res.json(response);
                }
            } else {
                throw new Error('No response from Python script');
            }
        })
        .catch(err => {
            console.error('Server Error:', err);
            res.status(500).json({ 
                error: {
                    message: 'Internal server error processing chat request',
                    details: err.message
                }
            });
        });
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});
