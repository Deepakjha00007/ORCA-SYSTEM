import os
import requests
import base64
from dotenv import load_dotenv 
load_dotenv()

class BhashiniNLPService:
    def __init__(self):
        self.user_id = os.getenv("BHASHINI_USER_ID", ""),
        self.udyat_api_key = os.getenv("UDYAT_API_KEY", "")
        self.inference_api_key = os.getenv("UDYAT_INFERENCE_ENDPOINT", "")
        self.config_url = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
        self.dhruva_url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"

    def _get_pipeline_service_ids(self, source_lang: str, target_lang: str, task_type: str):
        """Step 1 of Bhashini API: Capability negotiation to get model serviceId."""
        headers = {
            "userID": self.user_id,
            "udyatapikey":self.udyat_api_key,
            "inferencekey":self.inference_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "pipelineTasks": [
                {
                    "taskType": task_type,
                    "config": {
                        "language": {
                            "sourceLanguage": source_lang,
                            "targetLanguage": target_lang
                        }
                    }
                }
            ],
            "pipelineRequestConfig": {"pipelineId": "64392f08d7019a282c035b13"}
        }
        try:
            res = requests.post(self.config_url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
        return None

    def translate_indic_to_english(self, text: str, source_lang: str) -> str:
        """Translates local fishermen text query (e.g. Marathi/Tamil) to English using NMT."""
        if source_lang == "en" or not text:
            return text

        headers = {"Authorization": self.inference_api_key, "Content-Type": "application/json"}
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "nmt",
                    "config": {
                        "language": {"sourceLanguage": source_lang, "targetLanguage": "en"}
                    }
                }
            ],
            "inputData": {"input": [{"source": text}]}
        }
        try:
            res = requests.post(self.dhruva_url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                translated = res.json()["pipelineResponse"][0]["output"][0]["target"]
                return translated
        except Exception:
            pass
        return text  # Fallback to original text

    def translate_english_to_indic(self, text: str, target_lang: str) -> str:
        """Translates final agent advisory back into the local fisherman's language."""
        if target_lang == "en" or not text:
            return text

        headers = {"Authorization": self.inference_api_key, "Content-Type": "application/json"}
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "nmt",
                    "config": {
                        "language": {"sourceLanguage": "en", "targetLanguage": target_lang}
                    }
                }
            ],
            "inputData": {"input": [{"source": text}]}
        }
        try:
            res = requests.post(self.dhruva_url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json()["pipelineResponse"][0]["output"][0]["target"]
        except Exception:
            pass
        return text

    def text_to_speech(self, text: str, target_lang: str) -> str:
        """Converts localized advisory text to Base64 WAV audio for voice playback."""
        headers = {"Authorization": self.inference_api_key, "Content-Type": "application/json"}
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": target_lang},
                        "gender": "male"
                    }
                }
            ],
            "inputData": {"input": [{"source": text}]}
        }
        try:
            res = requests.post(self.dhruva_url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                audio_b64 = res.json()["pipelineResponse"][0]["audio"][0]["audioContent"]
                return audio_b64
        except Exception:
            pass
        return base64.b64encode(b"mock_audio_data").decode("utf-8")