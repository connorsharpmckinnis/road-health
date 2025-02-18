#utils.py

instructions = """
    You are a road condition analysis expert.
    Your task is to analyze visual data of road surfaces to identify and evaluate key types of distress. Focus on significant or severe issues only, avoiding over-detection of minor or superficial defects. Pay attention to the following types of distress:
        1.	Potholes: Depressions in the pavement surface caused by traffic loading and water intrusion. Not to be confused with manholes or pavement patches. 
        •	Avoid identifying shallow surface irregularities (e.g., oil stains, manhole covers, or mild texture changes) as potholes.
        •	Only classify as a pothole if the depth and shape suggest significant wear or damage likely to affect safety or functionality.
        •	Be very conservative about flagging an image as containing a pothole. Whenever in doubt, strongly consider the possibility that what you are looking at is actually a manhole cover or a patch of pavement with a different color. 
        •	When identifying a pothole, include in the summary field a general location of the pothole (e.g., 'Pothole is in the lower-left corner of the image').
        2.	Alligator Cracking: Interconnected cracks forming small, irregular shapes resembling an alligator’s skin, typically caused by fatigue or structural failure.
        •	Focus on extensive areas of visible cracking; disregard isolated or faint surface-level cracks.
        •	Cracking that is superficial or cosmetic in appearance should not be flagged.
        •	Be very conservative about calling something alligator cracking. Only mark 'yes' if the cracks are significant and extensive
        3.	Line Cracking: Significant or extensive longitudinal or transverse cracks along the road, caused by shrinkage, temperature changes, or structural failure.
        •	Refine criteria: Consider line cracking only if cracks are wide, deep, or continuous across a significant area. Ignore scattered, narrow, or isolated hairline cracks.
        •	Be very conservative about calling something line cracking. Only mark 'yes' if the cracks are significant and extensive
        4.	Debris: Foreign materials such as leaves, stones, or trash present on the road surface that could impact safety or visibility.
        •	Focus on debris that represents a clear hazard. Ignore small, inconsequential debris unlikely to affect road performance.
        •	Be very conservative about calling something debris. Only mark 'yes' if the debris is significant and obvious and on the roadway or shoulder.

    Detection Guidelines:
        •	Presence: Determine whether the issue is present (yes or no). Err on the side of “no” for borderline cases or if the issue is ambiguous.
        •	Confidence: Provide a confidence score between 0 and 1, reflecting certainty in your analysis.
        •	Confidence values above 0.7 should only be assigned for issues that are visually clear and consistent with definitions above.
        •	For low-confidence cases (e.g., <0.3), recommend re-evaluation or additional data collection.

    Updated Evaluation Output:

    For an image showing significant potholes and alligator cracking:
        •	Pothole: Yes (confidence: 0.94)
        •	Alligator Cracking: Yes (confidence: 0.91)
        •	Line Cracking: No (confidence: 0.70)
        •	Debris: No (confidence: 0.77)
        •	Summary: “The road exhibits severe alligator cracking and a large pothole in the top-left corner of the image. Overall condition is Poor.”
        •	Road Health Index: 45 (Poor)

    Additional Notes:
        •	Be conservative in classifying issues. Minor defects or ambiguous features should not be flagged unless they meet clear criteria of severity or safety impact.
        •	Confidence values are key to analysis reliability. Assign lower confidence scores to borderline or unclear cases.
        •	Ensure results are consistent with the Pavement Condition Index (PCI) system, emphasizing real-world road safety and functionality over purely cosmetic or minor issues.
    """

model = 'gpt-4o-mini'

response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "road_condition",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "pothole": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of potholes on the road"
                            },
                            "pothole_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the pothole determination, ranging from 0 to 1. 1 means that you are very confident that you are correct in your assessment, either that there is or is not a pothole."
                            },
                            "alligator_cracking": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the clear presence of 'alligator cracking' on the road"
                            },
                            "alligator_cracking_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the alligator cracking detection, ranging from 0 to 1. 1 means that you are very confident that you are correct in your assessment, either that there is or is not alligator cracking."
                            },
                            "line_cracking": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the substantial presence of line cracking on the road"
                            },
                            "line_cracking_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the line cracking detection, ranging from 0 to 1. 1 means that you are very confident that you are correct in your assessment, either that there is or is not line cracking."
                            },
                            "debris": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of debris on the road"
                            },
                            "debris_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the debris detection, ranging from 0 to 1"
                            },
                            "summary": {
                                "type": "string",
                                "description": "A brief summary of the road condition, a few sentences tops"
                            },
                            "road_health_index": {
                                "type": "integer",
                                "description": "The overall health of the road represented as a percentage from 1 to 100"
                            }
                        },
                        "required": [
                            "pothole",
                            "pothole_confidence",
                            "alligator_cracking",
                            "alligator_cracking_confidence",
                            "line_cracking",
                            "line_cracking_confidence",
                            "debris",
                            "debris_confidence",
                            "summary",
                            "road_health_index"
                        ],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }

batch_user_message = "Please analyze these images and share your expert road health analyses, adhering to the JSON schema provided."
batch_response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "road_condition_batch",
        "schema": {
            "type": "object",
            "properties": {
                "analyses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "The openai file id or unique identifier of the analyzed image"
                            },
                            "pothole": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of potholes on the road"
                            },
                            "pothole_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the pothole detection, ranging from 0 to 1"
                            },
                            "alligator_cracking": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of alligator cracking on the road"
                            },
                            "alligator_cracking_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the alligator cracking detection, ranging from 0 to 1"
                            },
                            "line_cracking": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of line cracking on the road"
                            },
                            "line_cracking_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the line cracking detection, ranging from 0 to 1"
                            },
                            "debris": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of debris on the road"
                            },
                            "debris_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the debris detection, ranging from 0 to 1"
                            },
                            "summary": {
                                "type": "string",
                                "description": "A brief summary of the road condition, a few sentences tops"
                            },
                            "road_health_index": {
                                "type": "integer",
                                "description": "The overall health of the road represented as a percentage from 1 to 100"
                            }
                        },
                        "required": [
                            "file_id",
                            "pothole",
                            "pothole_confidence",
                            "alligator_cracking",
                            "alligator_cracking_confidence",
                            "line_cracking",
                            "line_cracking_confidence",
                            "debris",
                            "debris_confidence",
                            "summary",
                            "road_health_index"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["analyses"],
            "additionalProperties": False
        },
        "strict": True
    }
}

assistant = 'asst_eU5BTCInSqddd4fsRiXwE8Dm'
batch_assistant = 'asst_os1KrypxpdTlWtqm7eswVUg6'

unprocessed_videos_path = 'unprocessed_videos'


"""
BOX FOLDER STRUCTURE
Root Folder (0)
- Videos (303832684570)
    - Archived Videos (308058834229)
- Images (308059149587)
    - Archived Images (308059844499)
    - Work Order Images (308058285408)
"""
box_videos_folder_id = '303832684570'
box_archived_videos_folder_id = '308058834229'
box_images_folder_id = '308059149587'
box_archived_images_folder_id = '308059844499'
box_work_order_images_folder_id = '308058285408'

def log_event(message):
    print(f"[LOG] {message}")

def get_assistant():
    return assistant

def get_batch_assistant():
    return batch_assistant

def set_batch_assistant(batch_assistant_id):
    global batch_assistant
    batch_assistant = batch_assistant_id

def read_config(file_path):
    pass