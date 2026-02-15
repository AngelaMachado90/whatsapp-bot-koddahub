import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from pywa import WhatsApp
from pywa.types import Message
import chatbot_integration

# Carregar variáveis de ambiente
load_dotenv()

# CONFIGURAÇÃO IMPORTANTE PARA O RAILWAY
PORT = int(os.getenv('PORT', 5000))  # Railway define a porta automaticamente

# ============================================
# API PARA SEU SITE (formulários, etc.)
# ============================================

@app.route('/api/enviar-mensagem', methods=['POST'])
def api_enviar_mensagem():
    """
    Endpoint para seu site enviar mensagens
    Ex: Quando alguém preenche um formulário, você pode enviar uma notificação
    """
    try:
        data = request.json
        telefone = data.get('telefone', '')  # Número do cliente
        mensagem = data.get('mensagem', '')
        nome = data.get('nome', 'Cliente')
        
        # Validar
        if not telefone or not mensagem:
            return jsonify({"erro": "Telefone e mensagem são obrigatórios"}), 400
        
        # Enviar mensagem via WhatsApp
        resultado = send_whatsapp_message(telefone, mensagem)
        
        return jsonify({
            "sucesso": True,
            "mensagem": "Mensagem enviada com sucesso",
            "detalhes": resultado
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na API: {str(e)}")
        return jsonify({"erro": str(e)}), 500


@app.route('/api/notificar-admin', methods=['POST'])
def api_notificar_admin():
    """
    Endpoint para notificar você (admin) quando alguém usar o site
    """
    try:
        data = request.json
        nome = data.get('nome', 'Visitante')
        email = data.get('email', '')
        mensagem = data.get('mensagem', '')
        origem = data.get('origem', 'formulário do site')
        
        # Seu número (o que você usou nos testes)
        SEU_NUMERO = "5541992272854"  # Ajuste conforme seu número
        
        texto = f"🔔 *Nova mensagem do site*\n\n"
        texto += f"*Nome:* {nome}\n"
        texto += f"*Email:* {email}\n"
        texto += f"*Origem:* {origem}\n"
        texto += f"*Mensagem:* {mensagem}"
        
        # Enviar para seu WhatsApp
        wa.send_message(to=SEU_NUMERO, text=texto)
        
        return jsonify({"sucesso": True}), 200
        
    except Exception as e:
        logger.error(f"Erro ao notificar: {str(e)}")
        return jsonify({"erro": str(e)}), 500


def send_whatsapp_message(telefone, mensagem):
    """Função auxiliar para enviar mensagens"""
    try:
        # Formatar número (remover caracteres especiais)
        telefone = ''.join(filter(str.isdigit, telefone))
        
        # Adicionar código do país se não tiver
        if not telefone.startswith('55'):
            telefone = '55' + telefone
        
        wa.send_message(to=telefone, text=mensagem)
        return {"status": "enviado", "para": telefone}
    except Exception as e:
        logger.error(f"Erro ao enviar: {str(e)}")
        raise
