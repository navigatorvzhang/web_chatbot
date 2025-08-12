// Check if we're in a browser environment
if (typeof window !== 'undefined' && typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', async () => {
        const messagesDiv = document.getElementById('chat-messages');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        let conversationContext = null;

        // Initialize chat session
        async function initChat() {
            try {
                const response = await fetchWithTimeout(`${API_CONFIG.baseUrl}/init`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!response.ok) throw new Error('Failed to initialize chat');
                
                const data = await response.json();
                if (data.status === 'success') {
                    conversationContext = {
                        messages: [{
                            role: "system",
                            content: `Using profile: ${JSON.stringify(data.profile, null, 2)}`
                        }],
                        chat_file: data.chat_file
                    };
                    console.log('Chat initialized with profile:', data.profile);
                }
            } catch (error) {
                console.error('Chat initialization failed:', error);
                addMessage('Failed to initialize chat session. Please refresh the page.');
            }
        }

        function addMessage(content, isUser = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
            
            // Convert newlines to <br> tags and preserve formatting
            const formattedContent = content
                .replace(/\n/g, '<br>')
                .replace(/ {2}/g, '&nbsp;&nbsp;');
                
            messageDiv.innerHTML = `
                <div class="message-content">${formattedContent}</div>
            `;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // API configuration
        const API_CONFIG = {
            baseUrl: 'http://localhost:3000',  // Update to Node.js server port
            timeout: 30000, // 30 seconds
            retries: 2
        };

        async function fetchWithTimeout(resource, options) {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), API_CONFIG.timeout);
            
            try {
                const response = await fetch(resource, {
                    ...options,
                    signal: controller.signal
                });
                clearTimeout(timeout);
                return response;
            } catch (error) {
                clearTimeout(timeout);
                throw error;
            }
        }

        async function sendMessageWithRetry(message, retryCount = 0) {
            try {
                console.log('Sending message to server:', message);
                const response = await fetchWithTimeout(`${API_CONFIG.baseUrl}/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        message,
                        context: conversationContext 
                    })
                });

                console.log('Server response status:', response.status);
                if (!response.ok) {
                    throw new Error(`Server error: ${response.status}`);
                }
                
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Invalid response format from server');
                }
                
                return await response.json();
            } catch (error) {
                console.error('Network error:', error);
                if (retryCount < API_CONFIG.retries && 
                    (error.name === 'AbortError' || error.message === 'Failed to fetch')) {
                    console.log(`Retrying (${retryCount + 1}/${API_CONFIG.retries})...`);
                    return await sendMessageWithRetry(message, retryCount + 1);
                }
                throw new Error(error.name === 'AbortError' 
                    ? 'Request timed out. Please try again.' 
                    : 'Unable to connect to server. Please check your connection.');
            }
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            // Disable input while processing
            userInput.disabled = true;
            sendButton.disabled = true;

            addMessage(message, true);
            userInput.value = '';

            try {
                const data = await sendMessageWithRetry(message);
                if (data.error) {
                    throw new Error(data.error.message);
                }
                addMessage(data.response);
                // Update conversation context
                conversationContext = data.context;
                
            } catch (error) {
                const errorMessage = error.message || 'Unknown error occurred';
                addMessage(`Sorry, there was an error processing your message. Details: ${errorMessage}`);
                console.error('Chat Error:', error);
            } finally {
                userInput.disabled = false;
                sendButton.disabled = false;
                userInput.focus();
            }
        }

        // Call initChat immediately and wait for it
        await initChat();
        console.log('Chat initialization complete');
        
        // Enable UI elements after initialization
        userInput.disabled = false;
        sendButton.disabled = false;

        // Handle multi-line input
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        sendButton.addEventListener('click', sendMessage);

        // Auto-resize textarea
        userInput.addEventListener('input', () => {
            userInput.style.height = 'auto';
            userInput.style.height = (userInput.scrollHeight) + 'px';
        });
    });
} else {
    console.log('This script is intended to run in a browser environment.');
}
