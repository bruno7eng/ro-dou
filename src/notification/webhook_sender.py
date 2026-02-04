import requests
import logging
import json
from datetime import datetime
from typing import Any, Dict, List, Union
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
        if isinstance(obj, (dict, list)):
            return obj
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
    def _iter_matches(self, search_report: Union[List[Dict[str, Any]], Dict[str, Any]]):
        if isinstance(search_report, dict):
            search_items = [search_report]
        else:
            search_items = search_report

        for search in search_items:
            if not search:
                continue

            header = search.get("header")
            filters = {
                "department": search.get("department"),
                "department_ignore": search.get("department_ignore"),
                "pubtype": search.get("pubtype"),
            }

            for group, search_results in search.get("result", {}).items():
                for term, term_results in search_results.items():
                    for department, results in term_results.items():
                        for match in results:
                            match_data = self._serialize(match)
                            if not isinstance(match_data, dict):
                                match_data = {"value": match_data}
                            else:
                                match_data = dict(match_data)
                            match_data.update(
                                {
                                    "group": group,
                                    "term": term,
                                    "department": department,
                                    "search_header": header,
                                    "filters": filters,
                                }
                            )
                            yield match_data

    def send_report(
        self, search_report: Union[List[Dict[str, Any]], Dict[str, Any]], report_date: str
    ):
        if not search_report:
            self.logger.info("WebhookSender: Nada para enviar.")
            return

        all_matches = list(self._iter_matches(search_report))
        if not all_matches:
            self.logger.info("WebhookSender: Nenhum item encontrado para enviar.")
            return

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