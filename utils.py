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

greenway_instructions = """
    You are a dedicated greenway pavement analyst. Your task is to review GoPro images or video frames of paved greenways and assess surface condition by detecting and quantifying key defects. Your primary goal is to emulate expert-level evaluations with high consistency and clarity.
 
1. Primary Objectives

For each image or frame:
•	Estimate a PASER rating (1–10) based on the entire visible segment. Think: “If this condition continued for the whole greenway, what would its PASER score be?”
•	Assign severity scores (0–10) for the following:
o	Line Cracking
o	Longitudinal Cracking
o	Raveling
o	Upheaval
 
2. PASER Rating Guidelines

Use these surface-level indicators when assigning PASER scores:
Score	Meaning	Notes
10–9	Excellent	No visible defects
8–7	Very Good–Good	Slight surface wear, light cracking
6–5	Good–Fair	Moderate cracking, minor raveling or patching
4–3	Fair–Poor	Severe cracking, potholes, upheaval, tripping hazards
2–1	Very Poor–Failed	Major damage, unusable, full reconstruction needed
Always highlight images rated 3 or below as critical.
3. Defect Detection and Severity Scoring (0–10)

Assign scores using the following rubrics:

A. Line Cracking (0–10)
•	Focus on visible straight cracks, either transverse or diagonal.
•	Ignore faint hairline marks; score only meaningful cracks.
•	0 = none; 5 = some moderate cracking; 10 = extensive, deep cracks.

B. Longitudinal Cracking (0–10)
•	Cracks running parallel to the direction of travel.
•	Prioritize ones that appear continuous, deep, or cause uneven surfaces.
•	0 = none; 10 = multiple deep or wide cracks with continuity.

C. Raveling (0–10)
•	Areas where the asphalt has degraded into loose gravel or has visibly rough surface texture.
•	Score based on spread and visual severity.
•	0 = smooth surface; 10 = widespread loose material and disintegration.

D. Upheaval (0–10)
•	Caused by root damage or other vertical displacement.
•	Prioritize changes that create trip hazards or uneven transitions.
•	0 = flat surface; 10 = clear raised sections that affect safety.
 
4. Detection Confidence

For each defect (if detected), provide:
•	Presence: Yes/No
•	Confidence Score: 0.0–1.0

Use >0.7 for obvious cases. Below 0.3 = ambiguous → recommend follow-up.
 
5. Reporting Template (per frame)

Example output:
{
  "PASER_rating": 3,
  "line_cracking": 6,
  "longitudinal_cracking": 8,
  "raveling": 5,
  "upheaval": 7,
  "summary": "Significant longitudinal cracking and root-related upheaval. This frame likely reflects poor condition overall. Recommend further review."
}
6. Final Notes
•	Always consider safety and long-term performance in your ratings.
•	Be conservative with PASER 8–10. Most images should fall in 4–7 unless pristine or severely damaged.
•	Match expert methodology: combine visual assessment, safety awareness, and material understanding.
•	When unsure, recommend flagging the frame for human review.
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

greenway_user_message = "Please analyze these images and share your expert greenway condition analyses, adhering to the JSON schema provided."
greenway_response_format = {
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
                "description": "The OpenAI file ID or unique identifier of the analyzed image frame"
              },
              "PASER_rating": {
                "type": "integer",
                "description": "Estimated PASER rating between 1 and 10 (1 = failed, 10 = excellent)"
              },
              "line_cracking": {
                "type": "integer",
                "description": "Severity score for general line cracking ranging from 0 to 10 (0 = none, 10 = severe)"
              },
              "longitudinal_cracking": {
                "type": "integer",
                "description": "Severity score for longitudinal cracks  ranging from 0 to 10 (0 = none, 10 = severe)"
              },
              "raveling": {
                "type": "integer",
                "description": "Severity score for raveling  ranging from 0 to 10 (0 = none, 10 = severe)"
              },
              "upheaval": {
                "type": "integer",
                "description": "Severity score for pavement upheaval  ranging from 0 to 10 (0 = none, 10 = severe)"
              },
              "summary": {
                "type": "string",
                "description": "Brief natural language summary of observed conditions and key issues"
              }
            },
            "required": [
              "file_id",
              "PASER_rating",
              "line_cracking",
              "longitudinal_cracking",
              "raveling",
              "upheaval",
              "summary"
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

checker_user_message = ""
checker_response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "checker_response",
        "schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The OpenAI file ID or unique identifier of the analyzed image frame"
                },
                "approval": {
                    "type": "string",
                    "description": "A 'yes' or 'no' statement describing whether you agree with the detection reported by the detector AI. Only answer 'yes' or 'no'"
                },
                "confidence": {
                    "type": "number",
                }
            },
            "required": ["file_id", "approval", "confidence"],
            "additionalProperties": False
        },
        "strict": True
    }
}


assistant = 'asst_eU5BTCInSqddd4fsRiXwE8Dm'
gpt_4o_batch_assistant = 'asst_os1KrypxpdTlWtqm7eswVUg6'
gpt_41_mini_batch_assistant = 'asst_P9RpVzTUOk4zJRodAP2QKw9Y'
batch_assistant = 'asst_os1KrypxpdTlWtqm7eswVUg6'
greenway_assistant = 'asst_1lJD0RtJ2eMEaZxiyoZ9Mzcn'

checker_assistant = ''

unprocessed_videos_path = 'unprocessed_videos'


"""
BOX FOLDER STRUCTURE
Root Folder (0)
Road Health (309237796489)
- Videos (303832684570)
    - Archived Videos (308058834229)
- Images (308059149587)
    - Archived Images (308059844499)
    - Work Order Images (308058285408)
"""
box_road_health_folder_id = '309237796489'
box_videos_folder_id = '303832684570'
box_archived_videos_folder_id = '308058834229'
box_images_folder_id = '308059149587'
box_archived_images_folder_id = '316117482557'
box_work_order_images_folder_id = '308058285408'

def log_event(message):
    print(f"[LOG] {message}")

def get_assistant():
    return assistant

def get_batch_assistant():
    return batch_assistant

def get_greenway_assistant():
    return greenway_assistant

def get_checker_assistant():
    return checker_assistant

def set_greenway_assistant(greenway_assistant_id):
    global greenway_assistant
    greenway_assistant = greenway_assistant_id

def set_batch_assistant(batch_assistant_id):
    global batch_assistant
    batch_assistant = batch_assistant_id

def set_checker_assistant(checker_assistant_id):
    global checker_assistant
    checker_assistant = checker_assistant_id

def read_config(file_path):
    pass