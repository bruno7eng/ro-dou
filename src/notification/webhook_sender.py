import requests
import logging
import json
from datetime import datetime
from typing import Any, Dict, List
# --- ADICIONE ESTE IMPORT ---
from .isender import ISender

# --- HERDE DE ISender ---
class WebhookSender(ISender): 
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

    def _serialize(self, obj):
        """
        Função auxiliar para transformar objetos complexos (Pydantic/Classes) 
        em dicionários simples que o JSON aceita.
        """
        if hasattr(obj, 'dict'): # Se for Pydantic (schema novo)
            return obj.dict()
        if hasattr(obj, 'model_dump'): # Se for Pydantic v2
            return obj.model_dump()
        if hasattr(obj, '__dict__'): # Se for classe normal
            return obj.__dict__
        if isinstance(obj, datetime): # Se for data
            return obj.isoformat()
        return str(obj) # Último recurso: transforma em texto

    def send(self, search_report: Dict[str, Any], report_date: str):
        """
        Envia os dados já "mastigados" para o n8n.
        """
        if not search_report:
            self.logger.info("WebhookSender: Nada para enviar.")
            return

        # Lista plana de todos os resultados encontrados
        all_matches = []

        # O search_report geralmente é: {'Termo Buscado': [Lista de Matches]}
        # Vamos iterar para criar uma lista única e rica
        for term, matches in search_report.items():
            for match in matches:
                # Serializa o objeto match para dicionário
                match_data = self._serialize(match)
                
                # Adiciona o termo que gerou esse resultado (útil pro n8n)
                match_data['triggered_by_term'] = term
                
                all_matches.append(match_data)

        # Monta o payload final
        payload = {
            "metadata": {
                "report_date": report_date,
                "total_matches": len(all_matches),
                "source": "ro-dou"
            },
            # Aqui está o ouro: uma lista pura de itens detalhados
            "data": all_matches 
        }

        try:
            # Usamos json.dumps com o default=self._serialize para garantir que nada quebre na conversão
            json_payload = json.dumps(payload, default=self._serialize)

            self.logger.info(f"Enviando {len(all_matches)} itens para n8n...")
            
            response = requests.post(
                self.webhook_url,
                data=json_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                self.logger.info("Webhook enviado com sucesso!")
            else:
                self.logger.error(f"Erro n8n (HTTP {response.status_code}): {response.text}")

        except Exception as e:
            self.logger.error(f"Falha ao enviar Webhook: {e}")