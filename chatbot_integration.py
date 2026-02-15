import logging

logger = logging.getLogger(__name__)

def process_message(user_id: str, message: str, user_name: str = "") -> str:
    """Processa mensagens do WhatsApp"""
    
    message_lower = message.lower()
    
    if "oi" in message_lower or "olá" in message_lower:
        return f"Olá {user_name}! Tudo bem? Como posso ajudar?"
    elif "preço" in message_lower or "valor" in message_lower:
        return "Nossos produtos têm preços a partir de R$ 50,00."
    elif "obrigado" in message_lower:
        return "Por nada! 😊"
    else:
        return f"Entendi: '{message}'. Em breve um atendente vai responder."

def process_callback(user_id: str, callback_data: str) -> str:
    return "Opção não reconhecida."
