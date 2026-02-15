import os
import logging
import time
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pywa import WhatsApp
from pywa.types import Message
import chatbot_integration

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)

# Configurações
PORT = int(os.getenv('PORT', 5000))
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')

# Verificar variáveis
logger.info("=== VERIFICANDO CONFIGURAÇÃO ===")
logger.info(f"PORT: {PORT}")
logger.info(f"WHATSAPP_PHONE_NUMBER_ID: {WHATSAPP_PHONE_NUMBER_ID}")
logger.info(f"WHATSAPP_VERIFY_TOKEN: {'Configurado' if WHATSAPP_VERIFY_TOKEN else 'FALTANDO'}")
logger.info(f"WHATSAPP_ACCESS_TOKEN: {'Configurado' if WHATSAPP_ACCESS_TOKEN else 'FALTANDO'}")

# Inicializar cliente WhatsApp
try:
    wa = WhatsApp(
        phone_id=WHATSAPP_PHONE_NUMBER_ID,
        token=WHATSAPP_ACCESS_TOKEN,
        server=app,
        verify_token=WHATSAPP_VERIFY_TOKEN
    )
    logger.info("✅ Cliente WhatsApp inicializado com sucesso")
except Exception as e:
    logger.error(f"❌ Erro ao inicializar WhatsApp: {str(e)}")
    wa = None

# ============================================
# KEEP-ALIVE (evita que o Railway derrube o serviço)
# ============================================

def keep_alive():
    """Função para manter o serviço ativo"""
    while True:
        try:
            logger.info("Keep-alive: serviço ativo")
            time.sleep(60)  # Log a cada minuto
        except Exception as e:
            logger.error(f"Erro no keep-alive: {e}")
            time.sleep(60)

# Iniciar thread de keep-alive
threading.Thread(target=keep_alive, daemon=True).start()

# ============================================
# HANDLER PRINCIPAL
# ============================================

@wa.on_message()
def handle_message(client: WhatsApp, msg: Message):
    try:
        from_number = msg.from_user.wa_id
        user_name = msg.from_user.name or "Cliente"
        message_text = msg.text.body if msg.text else ""
        
        logger.info(f"📨 Mensagem de {user_name} ({from_number}): {message_text}")
        
        msg.mark_read()
        msg.send_action()
        
        bot_response = chatbot_integration.process_message(
            user_id=from_number,
            message=message_text,
            user_name=user_name
        )
        
        if bot_response:
            msg.reply_text(text=bot_response)
            logger.info(f"✅ Resposta enviada: {bot_response[:50]}...")
        else:
            msg.reply_text(text="Desculpe, não consegui processar sua mensagem.")
            
    except Exception as e:
        logger.error(f"❌ Erro no handler: {str(e)}")

# ============================================
# ROTAS
# ============================================

@app.route('/health', methods=['GET'])
def health():
    """Health check com mais informações"""
    logger.info("Health check chamado")
    return jsonify({
        "status": "ok",
        "timestamp": time.time(),
        "servico": "WhatsApp Bot",
        "whatsapp_configured": wa is not None,
        "uptime": "funcionando"
    })

@app.route('/debug', methods=['GET'])
def debug():
    """Rota de debug para verificar configurações"""
    return jsonify({
        "phone_id_configured": bool(WHATSAPP_PHONE_NUMBER_ID),
        "token_configured": bool(WHATSAPP_ACCESS_TOKEN),
        "verify_token_configured": bool(WHATSAPP_VERIFY_TOKEN),
        "wa_initialized": wa is not None
    })

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    logger.info(f"Webhook verification - mode: {mode}, token: {token}")
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("✅ Webhook verificado com sucesso")
        return challenge, 200
    
    logger.warning("❌ Falha na verificação do webhook")
    return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("Webhook POST recebido")
    return "OK", 200

@app.route('/api/notificar-admin', methods=['POST'])
def api_notificar_admin():
    try:
        data = request.json
        logger.info(f"Notificação recebida: {data.get('nome')}")
        
        SEU_NUMERO = "5541992272854"
        
        if wa:
            texto = f"Nova mensagem de {data.get('nome')}"
            wa.send_message(to=SEU_NUMERO, text=texto)
            return jsonify({"sucesso": True}), 200
        
        return jsonify({"sucesso": False, "aviso": "WhatsApp não inicializado"}), 200
        
    except Exception as e:
        logger.error(f"Erro: {e}")
        return jsonify({"erro": str(e)}), 500

# ============================================
# INICIAR SERVIDOR
# ============================================

if __name__ == '__main__':
    logger.info(f"🚀 Iniciando servidor na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)  # debug=False para produção
