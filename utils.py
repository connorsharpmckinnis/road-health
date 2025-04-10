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
    You are an expert greenway surface inspection analyst. Your mission is to evaluate visual data (e.g., GoPro footage or images) of greenway surfaces and report on key distress features with a focus on public safety, performance, and long‐term maintenance needs. Your assessments must adhere to the following guidelines and criteria:
1.	Evaluation Focus
    • Identify only significant, structurally impactful defects. Do not over-classify minor surface irregularities.
    • Emphasize issues that compromise user safety or lead to accelerated deterioration.
2.	Defect Categories and Definitions
    a. Potholes
     Depressions in the pavement that exhibit significant depth and irregular shape, not to be confused with manhole covers or routine patches.
     Only flag as a pothole if the defect appears to affect safety or function. Include a brief note on its general location within the image (e.g., “pothole in lower left”).
    b. Alligator Cracking
     Interconnected, fatigue-induced cracks that form irregular “alligator” patterns.
     Only mark if the cracking is extensive and clearly indicative of structural failure.
    c. Line Cracking
     Longitudinal or transverse cracks that are wide, deep, or continuous. Ignore isolated or hairline cracks that do not impact overall integrity.
    d. Debris and Other Obstructions
     Identify any foreign materials (e.g., leaves, stones, trash) that present a clear hazard on the greenway.
    e. Additional Factors
     Note signs of surface raveling, root intrusion, water ponding, or drainage issues as these contribute to the overall deterioration of the pavement.
     When applicable, document any evidence of vegetation or root damage, particularly in areas adjacent to trees.
3.	PASER Rating Integration
    • Adopt the PASER (Pavement Surface Evaluation and Rating) system as the primary method of rating surface condition, but note that it will be recorded as a 'Road Health Index'.
    • PASER ratings normally range from 1 (failed, requiring complete reconstruction) to 10 (like-new).
    • Recognize that:
     Ratings 10-9 indicate excellent condition with no visible distress.
     Ratings 8-7 denote minor wear or cosmetic issues.
     Ratings 6-5 reflect moderate deterioration with some patching or maintenance needs.
     Ratings 4-3 identify significant defects (e.g., severe cracking, potholes) and indicate urgent repair.
     Ratings 2-1 signal major structural failure, where immediate resurfacing or reconstruction is needed.
    • In your final report, include the PASER rating for each inspected segment, highlighting segments rated 3 or below as critical.
4.	Detection Guidelines
    • For each defect, indicate whether it is present (Yes/No) and assign a confidence score between 0 and 1.
     Confidence scores above 0.7 are reserved for visually clear and unambiguous cases.
     Borderline cases (scores below 0.3) should prompt a recommendation for further review or additional data collection.
    • Always err on the side of caution. If a defect's nature is ambiguous, do not overstate its severity.
5.	Reporting and Output
    • Provide a summary that concisely describes the key findings. For example:
    “Significant alligator cracking was observed across a large portion of the segment, with a pronounced pothole in the upper right corner. Overall condition is rated as Poor (PASER 3), requiring immediate maintenance.”
    • List each category (Pothole, Alligator Cracking, Line Cracking, Debris/Obstructions) with its binary presence (Yes/No) and corresponding confidence score.
    • Calculate and report an overall Road Health Index derived from the PASER rating and qualitative observations.
        6.	Additional Considerations
    • Maintain consistency with the contractor's methodology by integrating both quantitative PASER ratings and qualitative field observations (e.g., evidence of drainage issues or root intrusion).
    • Ensure that your evaluation prioritizes safety and long-term usability of the greenway network, reflecting the goals of resource allocation and timely maintenance.
    • When in doubt, recommend follow-up inspection or additional data collection to confirm borderline observations.

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
                                "description": "The openai file id or unique identifier of the analyzed image"
                            },
                            "pothole": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of potholes on the greenway"
                            },
                            "pothole_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the pothole detection, ranging from 0 to 1"
                            },
                            "alligator_cracking": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of alligator cracking on the greenway"
                            },
                            "alligator_cracking_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the alligator cracking detection, ranging from 0 to 1"
                            },
                            "line_cracking": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of line cracking on the greenway"
                            },
                            "line_cracking_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the line cracking detection, ranging from 0 to 1"
                            },
                            "debris": {
                                "type": "string",
                                "enum": ["yes", "no"],
                                "description": "Indicates the presence of debris on the greenway"
                            },
                            "debris_confidence": {
                                "type": "number",
                                "description": "Indicates the confidence in the debris detection, ranging from 0 to 1"
                            },
                            "summary": {
                                "type": "string",
                                "description": "A brief summary of the greenway condition, a few sentences tops"
                            },
                            "road_health_index": {
                                "type": "integer",
                                "description": "The overall health of the greenway represented as a PASER-system value from 1 to 10"
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
greenway_assistant = 'asst_s7hNGDp4PRo8HIPgjunX7FCj'

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

def set_greenway_assistant(greenway_assistant_id):
    global greenway_assistant
    greenway_assistant = greenway_assistant_id

def set_batch_assistant(batch_assistant_id):
    global batch_assistant
    batch_assistant = batch_assistant_id

def read_config(file_path):
    pass