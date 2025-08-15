from pydantic import BaseModel, Field

# Road Health
class RoadHealth(BaseModel):
    pothole: bool
    summary: str
    pcr: int
    
road_health = {
    "prompt": "You are a pavement conditions expert, and your task is to evaluate the pavement in the image. Be conservative about identifying a pothole, and only flag a pothole if it is substantial and warrants immediate repair. When estimating 'pcr', use the Pavement Condition Rating system and provide a score between 0 (worst) and 100 (perfect). Make sure your summary is succinct, clear, and an accurate analysis of the pavement in the image. It is okay for your summary to be as simple as 'Excellent, no defects'",
    "schema": RoadHealth,
    "mime_type": "image/jpeg"
}


# Rink Occupancy
class PeopleCounting(BaseModel):
    count: int

people_counting = {
    "prompt": "You are a people counter, and your task is to count the number of people in the image. Be conservative in your identification, and count a person ONLY if you are absolutely certain.",
    "schema": PeopleCounting,
    "mime_type": "image/jpeg"
}


# Audio Sentiment
class AudioSentiment(BaseModel):
    sentiment: int = Field(ge=-100, le=100)
    transcript: str
    
audio_sentiment = {
    "prompt": "You are a sentiment analyst, and your task is to transcribe and evaluate the sentiment of the provided content. Your response should be an integer between -100 and 100, with negative numbers reflecting negative sentiment and positive reflecting positive.",
    "schema": AudioSentiment,
    "mime_type": "audio/mp3"
}