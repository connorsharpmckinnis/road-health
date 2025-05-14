import os
import json
from simple_salesforce import Salesforce
from math import radians, sin, cos, sqrt, atan2
from PIL import Image
import base64
from utils import *
from analysis import *
import dotenv
import logging
import io
import shutil
import re


dotenv.load_dotenv()

class WorkOrderCreator:
    def __init__(self, username: str=None, password: str=None, security_token: str=None, client_id: str=None, metadata_folder: str=None, telemetry_items: list=None, sandbox: bool=True):
        """
        Initialize the WorkOrderCreator class with Salesforce authentication.

        :param metadata_folder: Path to the folder containing metadata JSON files.
        :param username: Salesforce username.
        :param password: Salesforce password.
        :param security_token: Salesforce security token.
        :param client_id: Custom client ID for logging purposes.
        :param sandbox: Boolean indicating whether to use a Salesforce sandbox.
        """

        self.all_metadata = telemetry_items if telemetry_items else []

        

        username = username if username is not None else os.getenv('SALESFORCE_USERNAME')
        password = password if password is not None else os.getenv('SALESFORCE_PASSWORD')
        security_token = security_token if security_token is not None else os.getenv('SALESFORCE_SECURITY_TOKEN')
        client_id = client_id if client_id is not None else os.getenv('SALESFORCE_CONSUMER_KEY')
        
        domain = "test" if sandbox else "login"  # Use 'test' for sandbox, 'login' for production
        self.sf_domain = "--sahara.sandbox" if domain == "test" else ""

        self.metadata_folder = metadata_folder if metadata_folder is not None else 'frames'

        # Authenticate and initialize the Salesforce object
        self.sf = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            client_id=client_id,
            domain=domain
        )
        print(f"Authenticated successfully with Salesforce (sandbox={sandbox}).")

        self.coordinate_variance = 0.0002
        self.coordinate_variance_growth_factor = 0.001
        self.base_query = "SELECT Id, Name, Geolocation__latitude__s, Geolocation__longitude__s FROM Location__c"

    def process_metadata_files(self):
        """
        Process metadata files and create Work Orders for high-confidence potholes.
        Stores all metadata in a self.all_metadata list for future use.
        """
        self.all_metadata = []  # Initialize or reset the list to store all metadata

        for file_name in os.listdir(self.metadata_folder):
            if not file_name.endswith('.json'):
                continue

            file_path = os.path.join(self.metadata_folder, file_name)
            try:
                with open(file_path, 'r') as f:
                    metadata = json.load(f)
                    self.all_metadata.append(metadata)  # Add metadata to the list

            except Exception as e:
                print(f"Error processing file {file_name}: {e}")

        print(f"Processed {len(self.all_metadata)} metadata files. Stored in self.all_metadata.")
    
    async def work_order_engine(self, box_client, telemetry_objects:list=None):
        """
        Process all metadata items and create Work Orders and related Work Tasks for valid pothole detections.
        """
        try:
            logging.info("Starting Work Order Engine...")
            work_orders_created = 0
            
            for object in telemetry_objects:

                analysis_results = object.analysis_results
                pothole = analysis_results.get("pothole", "no")
                pothole_confidence = analysis_results.get("pothole_confidence", 0)
                if pothole == "yes" and pothole_confidence > 0.9:
                    logging.info(f"Processing metadata item: {object.filename}")
                    closest_location, closest_distance = self.get_closest_location(object.to_dict())

                    description = self.create_description_package(
                        object.to_dict(), closest_location, closest_distance
                    )

                    box_url = object.box_file_url
                    work_order_subject = f"Pothole Detected - Confidence {pothole_confidence*100:.1f}%"
                    work_order_id = self.create_work_order(object.to_dict(), work_order_subject, description, closest_location, box_file_url=box_url)

                    if work_order_id:
                        work_orders_created += 1
                        # Create a related Work Task
                        self.create_work_task(work_order_id)

                        # Send a work order card to the UI with the image
                        try:
                            # First convert the image to a base64 string
                            with open(object.filepath, "rb") as image_file:
                                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

                            # Break ai_analysis into separate strings for structuring into the card
                            ai_analysis_str = ""
                            for key, value in analysis_results.items():
                                ai_analysis_str += f"{key}: {value}\n"

                        except Exception as e:
                            logging.error(f"Error sending status update to UI: {e}")

                    else:
                        logging.error("Failed to create Work Order. Skipping further actions for this metadata item.")

            logging.info("Work Order Engine completed successfully.")
            return work_orders_created

        except Exception as e:
            logging.error(f"An error occurred in the Work Order Engine: {e}")
            return work_orders_created

    def get_nearby_street_segments(self, metadata_item): # Subprocess
        print(f"DEBUG: Running get_nearby_street_segments")
        # starts a get_street_segments() run to get records from SF where:
        #   latitude is within +- coordinate variance
        #   longitude is within +- coordinate variance
        # If no segments returned, expand the coordinate variance and try again
        # Returns list of street segments and their coordinates when any are returned
        segments = []
        while not segments: 
            results = self.get_street_segments(metadata_item)
            segments = results
            self.coordinate_variance += self.coordinate_variance_growth_factor

        simplified_locations = []
        for segment in segments: 
            location = {
                "Id": segment.get('Id'),
                "Name": segment.get('Name'),
                "Latitude": segment.get("Geolocation__Latitude__s"),
                "Longitude": segment.get("Geolocation__Longitude__s")
            }
            simplified_locations.append(location)
        
        return simplified_locations

    def get_street_segments(self, metadata_item): #Subprocesses
        print(f"DEBUG: Running get_street_segments")
        # Prep a query by adding the variance coordinates as +- conditions including WHERE
        # Run a query for street segments with the WHERE conditions added
        meta = metadata_item

        meta_lat_str = meta.get("lat", None)
        meta_lon_str = meta.get("lon", None)

        meta_lat = round(float(meta_lat_str), 4)
        meta_lon = round(float(meta_lon_str), 4)

        #Calculate lower and upper values for latitude and longitude searching
        lat_min = meta_lat - self.coordinate_variance
        lat_max = meta_lat + self.coordinate_variance
        lon_min = meta_lon - self.coordinate_variance
        lon_max = meta_lon + self.coordinate_variance
        conditions = f"WHERE (RecordTypeId = '0124u000000ciJTAAY' OR RecordTypeId = '0124u000000ciJSAAY') AND Geolocation__latitude__s >= {lat_min} AND Geolocation__latitude__s <= {lat_max} AND Geolocation__longitude__s >= {lon_min} AND Geolocation__longitude__s <= {lon_max}"

        
        results = self.sf.query(f"SELECT Id, Name, Geolocation__latitude__s, Geolocation__longitude__s FROM Location__c {conditions}")
        results = results['records']
        if len(results) == 0:
            results = None
        return results
    
    def expand_coordinate_variance(self):
        self.coordinate_variance += 0.0005

    def remove_timestamp(self, filename):
        return re.sub(r'^\d{8}_\d{2}_\d{2}_', '', filename)
    
    def get_closest_location(self, metadata_item): # Main Process
        locations = self.get_nearby_street_segments(metadata_item)
        closest_location = None
        min_distance = float('inf')
        for loc in locations:
            distance = self.calculate_distance(metadata_item, loc)
            if distance < min_distance:
                min_distance = distance
                closest_location = loc

        return closest_location, min_distance
            
    def create_work_order(self, metadata_item, subject, description, location_id=None, box_file_url='https://upload.wikimedia.org/wikipedia/commons/c/c7/Pothole_Big.jpg'):
        """
        Create a Work Order in Salesforce.

        :param subject: The subject of the Work Order.
        :param description: The description of the Work Order.
        :return: The Id of the created Work Order.
        """
        try:
            # Define the required fields for the Work Order
            lat_str = metadata_item.get('lat', 0)
            lon_str = metadata_item.get('lon', 0)

            lat = float(lat_str)
            lon = float(lon_str)

            location_id_string = location_id.get('Id')

            work_order = {
                'sm1a__Description__c': subject,
                'sm1a__Detailed_Comments__c': description,
                'Division__c': 'Operations',  # Hardcoded division for now
                'Location__c': location_id_string,
                'sm1a__Geolocation__Latitude__s': lat,
                'sm1a__Geolocation__Longitude__s': lon,
                'Subject_Image_URL__c': box_file_url
            }

            # Create the Work Order
            response = self.sf.sm1a__WorkOrder__c.create(work_order)
            work_order_id = response['id']
            print(f"Work Order created successfully: {work_order_id}")
            return work_order_id

        except Exception as e:
            print(f"Failed to create Work Order: {e}")
            return None
    
    def create_work_task(self, work_order_id):
        """
        Create a Work Task in Salesforce.

        :param work_order_id: The Id of the related Work Order.
        :return: The Id of the created Work Task.
        """
        try:
            # Define the required fields for the Work Task
            work_task = {
                'sm1a__Work_Order__c': work_order_id,  # Relates the Work Task to the Work Order
                'sm1a__Comments__c': 'Pothole Assessment',  # Placeholder subject
                'sm1a__Std_Task__c': 'aDI7X000000HKOtWAO'
            }

            # Create the Work Task
            response = self.sf.sm1a__WorkTask__c.create(work_task)
            work_task_id = response['id']
            print(f"Work Task created successfully: {work_task_id}")
            return work_task_id

        except Exception as e:
            print(f"Failed to create Work Task: {e}")
            return None

    def create_description_package(self, metadata_item, closest_sf_location, closest_sf_location_distance):
        """
        Create a description package formatted as a rich text field for Salesforce.

        :param metadata_item: Metadata for the detected pothole (includes telemetry and AI analysis).
        :param closest_sf_location: Closest Salesforce location object (contains Id, Name, Latitude, Longitude).
        :param closest_sf_location_distance: Distance from the pothole to the closest Salesforce location in km.
        :return: A formatted string for the Salesforce rich text field.


        {
        "filename": "frame_0001.jpg",
        "filepath": "frames/frame_0001.jpg",
        "timestamp": "2024-09-26T16:33:34Z",
        "lat": 35.756189,
        "lon": -78.7451761,
        "openai_file_id": "file-5JXkUvVhDCJq6BiW3Mw6Ny",
        "analysis_results": {
            "file_id": "frame_0001.jpg",
            "pothole": "no",
            "pothole_confidence": 0.85,
            "alligator_cracking": "yes",
            "alligator_cracking_confidence": 0.92,
            "line_cracking": "yes",
            "line_cracking_confidence": 0.89,
            "debris": "no",
            "debris_confidence": 0.95,
            "summary": "The road exhibits significant alligator cracking and extensive line cracking, indicating structural distress. Overall condition is Poor.",
            "road_health_index": 42
        }
    }



        """
        print(f"DEBUG: Running create_description_package")
        # Extract metadata details
        ai_analysis = metadata_item.get("analysis_results", {})
        analysis_summary = ai_analysis.get("summary", "No analysis summary provided.")
        pothole = ai_analysis.get("pothole", None)
        pothole_confidence = ai_analysis.get("pothole_confidence", None)
        line_cracking = ai_analysis.get("line_cracking", None)
        line_cracking_confidence = ai_analysis.get("line_cracking_confidence", None)
        alligator_cracking = ai_analysis.get("alligator_cracking", None)
        alligator_cracking_confidence = ai_analysis.get("alligator_cracking_confidence", None)
        debris = ai_analysis.get("debris", None)
        debris_confidence = ai_analysis.get("debris_confidence", None)
        lat = metadata_item.get("lat", "Unknown")
        lon = metadata_item.get("lon", "Unknown")
        box_url = metadata_item.get("box_file_url", "https://upload.wikimedia.org/wikipedia/commons/c/c7/Pothole_Big.jpg")

        # Construct assessment details
        assessment_details = []
        if pothole is not None:
            assessment_details.append(f"Pothole Presence: {'Yes' if pothole else 'No'} ({pothole_confidence * 100:.1f}%)")
        if line_cracking is not None:
            assessment_details.append(f"Line Cracking: {'Yes' if line_cracking else 'No'} ({line_cracking_confidence * 100:.1f}%)")
        if alligator_cracking is not None:
            assessment_details.append(f"Alligator Cracking: {'Yes' if alligator_cracking else 'No'} ({alligator_cracking_confidence * 100:.1f}%)")
        if debris is not None:
            assessment_details.append(f"Debris: {'Yes' if debris else 'No'} ({debris_confidence * 100:.1f}%)")

        # Construct the Google Maps URL
        maps_url = f"https://www.google.com/maps/place/{lat},{lon}"

        # Construct the Static Resource URL
        #static_resource_url = f"/resource/{static_resource_name}"

        # Format the description package
        description = (
            f"This Work Order was created by an automatic system due to a detected pothole near "
            f"{closest_sf_location.get('Name', 'Unknown Location')} (approximately "
            f"{closest_sf_location_distance:.2f} km away).\n\n"
            f"If this analysis is incorrect, or correction is not needed, please close this Work Order and do not act on it.\n\n"
            f"Analysis provided by the Road Health Analysis AI:\n"
            f"{analysis_summary}\n\n"
            f"Assessment Results:\n"
            + "\n".join(assessment_details) + "\n\n"
            f"To route to the best-estimated location of the pothole, click this link:\n"
            f"{maps_url}\n"
            f"{box_url}"
        )


        print(f'DEBUG: {description = }')
        return description

    def create_static_resource(self, image_file, quality=25):
        """
        Upload an image file as a Salesforce Static Resource and return its Id.

        :param image_file: File path to the image (jpg format).
        :return: Id of the created Static Resource.
        """
        try:
            # Check if file exists
            if not os.path.exists(image_file):
                raise FileNotFoundError(f"Image file '{image_file}' not found.")
            
            # Compress the image
            compressed_file = f"compressed_{os.path.basename(image_file)}"
            with Image.open(image_file) as img:
                img.save(compressed_file, "JPEG", quality=quality)

            # Read the image and encode it as base64
            with open(compressed_file, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            # Prepare the Static Resource name
            base_name = os.path.splitext(os.path.basename(image_file))[0]
            sanitized_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in base_name)
            resource_name = f"road_image_{sanitized_name}"

            # Construct the Static Resource payload
            print(f"DEBUG: {resource_name = }")
            static_resource = {
                "Name": resource_name,
                "ContentType": "image/jpeg",
                "Body": image_base64,
                "CacheControl": "Public",
            }

            # Create the Static Resource in Salesforce
            response = self.sf.StaticResource.create(static_resource)
            print(f"DEBUG: {response = }")
            return response['id'], resource_name

        except Exception as e:
            print(f"An error occurred while creating the Static Resource: {e}")
            return None

    def upload_file_to_salesforce(self, file_path, record_id):
        """
        Upload a file as a Salesforce File and relate it to a record.

        :param file_path: The path to the file to upload.
        :param record_id: The Salesforce record Id to relate the file to.
        :return: The Id of the created ContentDocument.
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File '{file_path}' not found.")
            
            # Compress the image in memory
            with Image.open(file_path) as img:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=25)
                img_byte_arr = img_byte_arr.getvalue()

            # Encode the image as base64
            file_data = base64.b64encode(img_byte_arr).decode("utf-8")

            # Get the file name from the path
            file_name = os.path.basename(file_path)

            # Create the ContentVersion record
            content_version = {
                "Title": file_name,
                "PathOnClient": file_name,
                "VersionData": file_data,
                "FirstPublishLocationId": record_id
            }

            # Make the API call to create the ContentVersion
            response = self.sf.ContentVersion.create(content_version)

            # Retrieve the ContentDocumentId from the created ContentVersion
            content_version_id = response["id"]
            query = f"SELECT ContentDocumentId, Id FROM ContentVersion WHERE Id = '{content_version_id}'"
            result = self.sf.query(query)

            content_document_id = result["records"][0]["ContentDocumentId"]
            content_version_id = result["records"][0]["Id"]
            print(f"File uploaded successfully: ContentDocumentId = {content_document_id}")

            return content_document_id, content_version_id

        except Exception as e:
            print(f"An error occurred while uploading the file: {e}")
            return None

    def calculate_distance(self, metadata_item, location): # Subprocess, returns est distance in km
        print(f"DEBUG: Running calculate_distance...")
        print(f"DEBUG: {location = }")
        meta = metadata_item

        meta_lat_str = meta.get("lat", None)
        meta_lon_str = meta.get("lon", None)

        meta_lat = round(float(meta_lat_str), 4)
        meta_lon = round(float(meta_lon_str), 4)
        
        loc_lat = location['Latitude']
        loc_lon = location['Longitude']

        print(f"DEBUG: {loc_lat = }")
        print(f"DEBUG: {loc_lon = }")

        lat_diff = loc_lat - meta_lat
        lon_diff = loc_lon - meta_lon
        return round(((lat_diff**2 + lon_diff**2)**0.5)*110, 3)

    def post_image_to_chatter(self, work_order_id, image_content_document_id, message=None):
        chatter_post_id = None
        #Need to create a Chatter post with the salesforce api, relate the post to the work order record, and attach the content document id as a FeedAttachment junction object
        try: 
            response = self.sf.FeedItem.create({
                'ParentId': work_order_id,
                'Body': message,
                'RelatedRecordId': image_content_document_id,
                'Type': 'ContentPost'
            })
            print(f"{response = }")
            chatter_post_id = response['id']
            print(f"{chatter_post_id = }")
        except Exception as e:
            print(f"Failed to post image to Chatter: {e}")
        return chatter_post_id

if __name__ == '__main__':
    print('starting')
    
    username = os.getenv('SALESFORCE_USERNAME')
    password = os.getenv('SALESFORCE_PASSWORD')
    security_token = os.getenv('SALESFORCE_SECURITY_TOKEN')
    client_id = os.getenv('SALESFORCE_CONSUMER_KEY')
    is_sandbox = True

    w_o_creator = WorkOrderCreator(username=username, password=password, security_token=security_token, client_id=client_id, sandbox=is_sandbox)
