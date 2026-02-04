import requests
import logging
import json
from datetime import datetime
from typing import Any, Dict, List
from .isender import ISender

class WebhookSender(ISender):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

    # --- TRIBUTO AO PAI (ISender) ---
    # Precisamos definir isso para o Python não travar, 
    # mas não vamos usar nenhuma dessas duas coisas na lógica real.
    @property
    def highlight_tags(self):
        return ("", "")

    def send(self, *args, **kwargs):
        pass
    # --------------------------------

    def _serialize(self, obj):
        """Serializa objetos complexos para JSON"""
        if hasattr(obj, 'dict'): 
            return obj.dict()
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    # --- A LÓGICA REAL ---
    # Sobrescrevemos o send_report do pai. Assim, o Notifier chama ESTE método
    # diretamente, ignorando toda a lógica de formatação de texto do ISender.
    def send_report(self, search_report: Dict[str, Any], report_date: str):
        if not search_report:
            self.logger.info("WebhookSender: Nada para enviar.")
            return

        all_matches = []

        for term, matches in search_report.items():
            for match in matches:
                match_data = self._serialize(match)
                match_data['triggered_by_term'] = term
                all_matches.append(match_data)

        payload = {
            "metadata": {
                "report_date": report_date,
                "total_matches": len(all_matches),
                "source": "ro-dou"
            },
            "data": all_matches 
        }

        try:
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