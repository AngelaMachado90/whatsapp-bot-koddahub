const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');

const app = express();
const PORT = process.env.PORT || 3001;

// Middlewares
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Garantir que pastas existam
if (!fs.existsSync('./data')) fs.mkdirSync('./data');
if (!fs.existsSync('./sessions')) fs.mkdirSync('./sessions');

// Banco de dados simples (arquivo JSON)
const DB_FILE = './data/instances.json';

function loadInstances() {
    try {
        if (fs.existsSync(DB_FILE)) {
            return JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
        }
    } catch (error) {
        console.error('Erro ao carregar instâncias:', error);
    }
    return { instances: [] };
}

function saveInstances(data) {
    try {
        fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2));
    } catch (error) {
        console.error('Erro ao salvar instâncias:', error);
    }
}

// Armazenar clientes ativos em memória
const activeClients = new Map();

// ============================================
// API ENDPOINTS
// ============================================

// Listar todas instâncias
app.get('/api/instances', (req, res) => {
    const data = loadInstances();
    res.json(data.instances);
});

// Criar nova instância
app.post('/api/instances', async (req, res) => {
    const { name, number } = req.body;
    
    if (!name || !number) {
        return res.status(400).json({ error: 'Nome e número são obrigatórios' });
    }
    
    const instanceId = `inst_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    
    // Salvar no banco
    const data = loadInstances();
    const newInstance = {
        id: instanceId,
        name,
        number,
        status: 'initializing',
        createdAt: new Date().toISOString(),
        webhookUrl: `https://www.koddahub.com.br/webhook/whatsapp/${instanceId}`
    };
    
    data.instances.push(newInstance);
    saveInstances(data);
    
    // Iniciar cliente WhatsApp
    startWhatsAppClient(instanceId, number);
    
    res.json({ 
        success: true, 
        instance: newInstance 
    });
});

// Obter QR Code de uma instância
app.get('/api/instances/:instanceId/qr', (req, res) => {
    const { instanceId } = req.params;
    const client = activeClients.get(instanceId);
    
    if (!client) {
        return res.status(404).json({ error: 'Instância não encontrada' });
    }
    
    res.json({ 
        qr: client.qr || null,
        status: client.status || 'initializing'
    });
});

// Função para iniciar cliente WhatsApp
async function startWhatsAppClient(instanceId, number) {
    console.log(`🔄 Iniciando cliente para ${instanceId}`);
    
    const client = new Client({
        authStrategy: new LocalAuth({
            clientId: instanceId,
            dataPath: `./sessions/${instanceId}`
        }),
        puppeteer: {
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
    });
    
    // Armazenar no mapa
    activeClients.set(instanceId, { 
        client, 
        status: 'initializing',
        qr: null 
    });
    
    // Evento QR Code
    client.on('qr', async (qr) => {
        console.log(`📱 QR Code gerado para ${instanceId}`);
        
        // Gerar imagem base64 do QR Code
        const qrImage = await qrcode.toDataURL(qr);
        
        activeClients.set(instanceId, { 
            ...activeClients.get(instanceId),
            qr: qrImage,
            status: 'waiting_qr'
        });
    });
    
    // Evento de autenticado
    client.on('authenticated', () => {
        console.log(` Autenticado: ${instanceId}`);
        activeClients.set(instanceId, { 
            ...activeClients.get(instanceId),
            status: 'authenticated',
            qr: null 
        });
    });
    
    // Evento de pronto
    client.on('ready', () => {
        console.log(`Cliente pronto: ${instanceId}`);
        
        activeClients.set(instanceId, { 
            ...activeClients.get(instanceId),
            status: 'connected',
            qr: null 
        });
        
        // Atualizar status no banco
        const data = loadInstances();
        const index = data.instances.findIndex(i => i.id === instanceId);
        if (index !== -1) {
            data.instances[index].status = 'connected';
            data.instances[index].connectedAt = new Date().toISOString();
            saveInstances(data);
        }
    });
    
    // Evento de desconexão
    client.on('disconnected', (reason) => {
        console.log(`Desconectado ${instanceId}: ${reason}`);
        
        activeClients.set(instanceId, { 
            ...activeClients.get(instanceId),
            status: 'disconnected' 
        });
        
        // Atualizar status no banco
        const data = loadInstances();
        const index = data.instances.findIndex(i => i.id === instanceId);
        if (index !== -1) {
            data.instances[index].status = 'disconnected';
            saveInstances(data);
        }
    });
    
    // Evento de mensagem
    client.on('message', async (message) => {
        console.log(`📨 Mensagem para ${instanceId} de ${message.from}: ${message.body}`);
        
        // Aqui você vai chamar seu chatbot
        const resposta = await processarComChatbot(message.body);
        
        if (resposta) {
            await message.reply(resposta);
        }
    });
    
    // Inicializar
    client.initialize();
}

// Função do chatbot (copie a lógica do seu kodassauro-chat.js)
async function processarComChatbot(texto) {
    // Por enquanto uma resposta simples
    // Depois você pode importar a lógica completa
    
    const lowerText = texto.toLowerCase();
    
    if (lowerText.includes('preço') || lowerText.includes('valor')) {
        return "💰 Nossos planos começam em R$ 99,90/mês. Quer saber mais?";
    }
    
    if (lowerText.includes('site') || lowerText.includes('criar')) {
        return "🦕 Temos sites institucionais, e-commerce, industriais e mais! Qual te interessa?";
    }
    
    if (lowerText.includes('obrigado')) {
        return "🥰 Por nada! Estou aqui para ajudar.";
    }
    
    return "🦕 Olá! Sou o Kodassauro, assistente da KoddaHub. Como posso ajudar?";
}

// ============================================
// ADMIN INTERFACE
// ============================================

// Página admin simplificada
app.get('/admin', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsBot Admin</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }
                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.1);
                }
                h1 { color: #333; margin-bottom: 10px; }
                h1 i { color: #25D366; }
                .subtitle { color: #666; margin-bottom: 30px; }
                
                .add-card {
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }
                
                input {
                    padding: 10px;
                    margin: 5px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    width: 200px;
                }
                
                button {
                    background: #25D366;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                button:hover { background: #128C7E; }
                
                .instance {
                    background: #f8f9fa;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    border-left: 4px solid #25D366;
                }
                
                .status {
                    display: inline-block;
                    padding: 3px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: bold;
                }
                .status.connected { background: #d4edda; color: #155724; }
                .status.waiting { background: #fff3cd; color: #856404; }
                .status.disconnected { background: #f8d7da; color: #721c24; }
                
                .qr-code {
                    max-width: 200px;
                    margin: 10px 0;
                }
                
                .toast {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #333;
                    color: white;
                    padding: 15px 25px;
                    border-radius: 8px;
                    display: none;
                }
            </style>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        </head>
        <body>
            <div class="container">
                <h1><i class="fab fa-whatsapp"></i> WhatsBot - KoddaHub</h1>
                <p class="subtitle">Gerencie seus números de WhatsApp</p>
                
                <div class="add-card">
                    <h3><i class="fas fa-plus-circle"></i> Adicionar Novo Número</h3>
                    <input type="text" id="name" placeholder="Nome (ex: Meu Número)">
                    <input type="text" id="number" placeholder="Número (ex: 554192272854)">
                    <button onclick="addInstance()">Adicionar</button>
                </div>
                
                <h3>Instâncias Ativas</h3>
                <div id="instances"></div>
            </div>
            
            <!-- Modal QR Code -->
            <div id="qrModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.5); justify-content:center; align-items:center;">
                <div style="background:white; padding:30px; border-radius:15px; text-align:center;">
                    <h3>Conectar WhatsApp</h3>
                    <div id="qrCodeContainer"></div>
                    <button onclick="closeQR()" style="margin-top:15px;">Fechar</button>
                </div>
            </div>
            
            <div class="toast" id="toast"></div>
            
            <script>
                async function loadInstances() {
                    const response = await fetch('/api/instances');
                    const instances = await response.json();
                    
                    const html = instances.map(inst => \`
                        <div class="instance">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div>
                                    <strong>\${inst.name}</strong> - \${inst.number}
                                </div>
                                <div>
                                    <span class="status \${inst.status === 'connected' ? 'connected' : inst.status === 'waiting_qr' ? 'waiting' : 'disconnected'}">
                                        \${inst.status === 'connected' ? 'Conectado' : inst.status === 'waiting_qr' ? 'Aguardando QR' : 'Desconectado'}
                                    </span>
                                    <button onclick="showQR('\${inst.id}')" style="margin-left:10px;">
                                        <i class="fas fa-qrcode"></i>
                                    </button>
                                </div>
                            </div>
                            <div style="font-size:12px; color:#666; margin-top:5px;">
                                ID: \${inst.id} | Criado: \${new Date(inst.createdAt).toLocaleString()}
                            </div>
                        </div>
                    \`).join('');
                    
                    document.getElementById('instances').innerHTML = html || '<p>Nenhuma instância configurada</p>';
                }
                
                async function addInstance() {
                    const name = document.getElementById('name').value;
                    const number = document.getElementById('number').value;
                    
                    if (!name || !number) {
                        showToast('Preencha todos os campos', 'error');
                        return;
                    }
                    
                    const response = await fetch('/api/instances', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, number })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        showToast('Instância criada com sucesso!');
                        document.getElementById('name').value = '';
                        document.getElementById('number').value = '';
                        loadInstances();
                    } else {
                        showToast('Erro ao criar instância', 'error');
                    }
                }
                
                async function showQR(instanceId) {
                    document.getElementById('qrModal').style.display = 'flex';
                    document.getElementById('qrCodeContainer').innerHTML = '<p>Carregando QR Code...</p>';
                    
                    const response = await fetch(\`/api/instances/\${instanceId}/qr\`);
                    const data = await response.json();
                    
                    if (data.qr) {
                        document.getElementById('qrCodeContainer').innerHTML = \`
                            <img src="\${data.qr}" style="width:200px; height:200px;">
                            <p>Escaneie com seu WhatsApp</p>
                        \`;
                    } else {
                        document.getElementById('qrCodeContainer').innerHTML = '<p>QR Code ainda não gerado. Aguarde...</p>';
                    }
                    
                    // Atualizar a cada 5 segundos
                    setTimeout(() => showQR(instanceId), 5000);
                }
                
                function closeQR() {
                    document.getElementById('qrModal').style.display = 'none';
                }
                
                function showToast(message, type = 'success') {
                    const toast = document.getElementById('toast');
                    toast.textContent = message;
                    toast.style.background = type === 'success' ? '#28a745' : '#dc3545';
                    toast.style.display = 'block';
                    setTimeout(() => toast.style.display = 'none', 3000);
                }
                
                loadInstances();
                setInterval(loadInstances, 10000); // Atualizar a cada 10s
            </script>
        </body>
        </html>
    `);
});

// ============================================
// INICIAR SERVIDOR
// ============================================
app.listen(PORT, () => {
    console.log(`🚀 Servidor rodando na porta ${PORT}`);
    console.log(`📊 Admin: http://localhost:${PORT}/admin`);
});
