from google import genai
import dotenv
from google.genai import types
import json
import sqlite3
import os
from datetime import datetime

from v2_configurations import road_health, people_counting, audio_sentiment

class GeminiConnection:
    
    def __init__(self):
        api_key = dotenv.get_key('.env', 'GEMINI_API_KEY')
        self.client = genai.Client(api_key=api_key)
        
        self.conn = sqlite3.connect('v2_points.db')
        self.cursor = self.conn.cursor()
        
    def export_db_to_json(self, db_path="v2_points.db", output_folder="v2_output_json"):
        self.cursor.execute("SELECT * FROM points")
        columns = [desc[0] for desc in self.cursor.description]
        rows = self.cursor.fetchall()
        
        data = [dict(zip(columns, row)) for row in rows]
        
        os.makedirs(output_folder, exist_ok=True)
        
        output_filename = f"points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_path = os.path.join(output_folder, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Exported {len(data)} records to {output_path}")
        
    def clear_points_table(self, db_path="v2_points.db"):
        self.cursor.execute("DELETE FROM points")
        self.conn.commit()

    def close_db(self):
        self.conn.close()
        
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
    
    def update_point(self, content_filename:str, analysis:dict):
        select_command = """SELECT id FROM points WHERE frame_filename = ?"""
        update_command = """UPDATE points SET analysis = ? WHERE id = ?"""
        #What does SELECT command return? List? pandas dataframe? 
        rows = self.cursor.execute(select_command, (content_filename,)).fetchall()
        print(rows)
        analysis_json_string = json.dumps(analysis)
        self.cursor.execute(update_command, (analysis_json_string, rows[0][0])) # Replace rows[0] with the true reference to id

        self.conn.commit()

def main():
    client = GeminiConnection()
    '''image = "v2_images/convo.png"

    for i in range(3):
        
        analysis = client.analyze_content(content=image, configuration=people_counting)
        print(f'round {i+1}: {analysis['count']}')'''
    dict = {"hello": "world"}
    client.update_point("frame_0000.png", dict)
if __name__ == "__main__":
    main()
