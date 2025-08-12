from google import genai
import dotenv
from google.genai import types
import json

from v2_configurations import road_health, people_counting, audio_sentiment

class GeminiConnection:
    
    def __init__(self):
        api_key = dotenv.get_key('.env', 'GEMINI_API_KEY')
        self.client = genai.Client(api_key=api_key)
        
    def file_to_bytestring(self, image):
        with open(image, 'rb') as image:
            bytestring = image.read()
            return bytestring  
    
    def analyze_content(self, content:str, configuration:dict, model="gemini-2.5-flash-lite") -> dict:
        results = ""
        content_bytes = self.file_to_bytestring(content)
        
        response = self.client.models.generate_content(
            model=model,
            contents = [
                configuration["prompt"],
                types.Part.from_bytes(
                    data=content_bytes,
                    mime_type=configuration["mime_type"])],
            config = {
                "response_mime_type": "application/json",
                "response_schema": configuration["schema"],
            },
        ).text
        results = json.loads(response or "{}")
        return results      


def main():
    client = GeminiConnection()
    image = "v2_images/convo.png"

    for i in range(3):
        
        analysis = client.analyze_content(content=image, configuration=people_counting)
        print(f'round {i+1}: {analysis['count']}')
if __name__ == "__main__":
    main()
