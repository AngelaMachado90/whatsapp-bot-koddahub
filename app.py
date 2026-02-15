import os
import logging
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

# Verificar se as variáveis de ambiente estão configuradas
if not all([WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN]):
    logger.error("Variaveis de ambiente nao configuradas:")
    if not WHATSAPP_ACCESS_TOKEN:
        logger.error("- WHATSAPP_ACCESS_TOKEN nao configurado")
    if not WHATSAPP_PHONE_NUMBER_ID:
        logger.error("- WHATSAPP_PHONE_NUMBER_ID nao configurado")
    if not WHATSAPP_VERIFY_TOKEN:
        logger.error("- WHATSAPP_VERIFY_TOKEN nao configurado")

# Inicializar cliente WhatsApp - SEM callback_url para evitar erro
try:
    wa = WhatsApp(
        phone_id=WHATSAPP_PHONE_NUMBER_ID,
        token=WHATSAPP_ACCESS_TOKEN,
        server=app,
        verify_token=WHATSAPP_VERIFY_TOKEN
    )
    logger.info("Cliente WhatsApp inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar WhatsApp: {str(e)}")
    wa = None

# ============================================
# HANDLER PRINCIPAL - RECEBE MENSAGENS
# ============================================

@wa.on_message()
def handle_message(client: WhatsApp, msg: Message):
    """
    Toda mensagem que chegar no seu número de teste
    vai passar por aqui
    """
    try:
        # Pegar informações de quem enviou
        from_number = msg.from_user.wa_id
        user_name = msg.from_user.name or "Cliente"
        message_text = msg.text.body if msg.text else ""
        
        logger.info(f"Mensagem recebida de {user_name} ({from_number}): {message_text}")
        
        # Marcar como lido e mostrar "digitando..."
        msg.mark_read()
        msg.send_action()
        
        # ===== INTEGRAÇÃO COM SEU CHATBOT =====
        bot_response = chatbot_integration.process_message(
            user_id=from_number,
            message=message_text,
            user_name=user_name
        )
        
        # Enviar resposta
        if bot_response:
            msg.reply_text(text=bot_response)
            logger.info(f"Resposta enviada: {bot_response[:50]}...")
        else:
            msg.reply_text(text="Desculpe, nao consegui processar sua mensagem.")
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")
        try:
            msg.reply_text(text="Ocorreu um erro interno. Nossa equipe foi notificada.")
        except:
            pass

# ============================================
# API PARA SEU SITE
# ============================================

@app.route('/api/enviar-mensagem', methods=['POST'])
def api_enviar_mensagem():
    """
    Endpoint para seu site enviar mensagens
    """
    try:
        data = request.json
        telefone = data.get('telefone', '')
        mensagem = data.get('mensagem', '')
        nome = data.get('nome', 'Cliente')
        
        if not telefone:
            return jsonify({"erro": "Telefone é obrigatório"}), 400
        if not mensagem:
            return jsonify({"erro": "Mensagem é obrigatória"}), 400
        
        telefone = ''.join(filter(str.isdigit, telefone))
        
        if not telefone.startswith('55'):
            telefone = '55' + telefone
        
        if wa:
            wa.send_message(to=telefone, text=mensagem)
            logger.info(f"Mensagem enviada para {telefone}")
            return jsonify({"sucesso": True, "mensagem": "Mensagem enviada com sucesso"}), 200
        else:
            return jsonify({"erro": "WhatsApp nao inicializado"}), 500
        
    except Exception as e:
        logger.error(f"Erro na API: {str(e)}")
        return jsonify({"erro": str(e)}), 500


@app.route('/api/notificar-admin', methods=['POST'])
def api_notificar_admin():
    """
    Endpoint para notificar o administrador
    """
    try:
        data = request.json
        nome = data.get('nome', 'Visitante')
        email = data.get('email', '')
        telefone = data.get('telefone', '')
        mensagem = data.get('mensagem', '')
        origem = data.get('origem', 'formulario do site')
        
        SEU_NUMERO = "5541992272854"
        
        texto = f"Nova mensagem do site\n\n"
        texto += f"Nome: {nome}\n"
        texto += f"Email: {email}\n"
        texto += f"Telefone: {telefone}\n"
        texto += f"Origem: {origem}\n"
        texto += f"Mensagem: {mensagem}"
        
        if wa:
            wa.send_message(to=SEU_NUMERO, text=texto)
            logger.info(f"Administrador notificado sobre mensagem de {nome}")
            return jsonify({"sucesso": True}), 200
        else:
            logger.warning("WhatsApp nao inicializado, notificacao nao enviada")
            return jsonify({"sucesso": False, "aviso": "Modo teste"}), 200
        
    except Exception as e:
        logger.error(f"Erro ao notificar administrador: {str(e)}")
        return jsonify({"erro": str(e)}), 500

# ============================================
# HEALTH CHECK
# ============================================

@app.route('/health', methods=['GET'])
def health():
    """Verificar se o servidor está rodando"""
    return jsonify({
        "status": "ok",
        "servico": "WhatsApp Bot",
        "whatsapp_configured": wa is not None
    })

# ============================================
# WEBHOOK
# ============================================

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Endpoint de verificacao do webhook
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verificado com sucesso")
        return challenge, 200
    
    logger.warning("Falha na verificacao do webhook")
    return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint que recebe as mensagens do WhatsApp
    """
    return "OK", 200

# ============================================
# INICIAR SERVIDOR
# ============================================

if __name__ == '__main__':
    logger.info(f"Iniciando servidor na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)
