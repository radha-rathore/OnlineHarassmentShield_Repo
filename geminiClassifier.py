import os
import time
import google.generativeai as genai
import requests
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import json
import ast

geminiApiKey = '**************' # Replace with your gemini API key
genai.configure(api_key=geminiApiKey)

## To overcome safety settings
safety_settings_Gemini={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

# Create the model
generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

gemini_model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

def wait_for_files_active(perpetrator_File):
  """Waits for the given files to be active.
  Some files uploaded to the Gemini API need to be processed before they can be used as prompt inputs. The status can be seen by querying the file's "state" field.
  This implementation uses a simple blocking polling loop. Production code should probably employ a more sophisticated approach.
  """
  print("Waiting for file processing...")
  while perpetrator_File.state.name == "PROCESSING":
    print(".", end="", flush=True)
    time.sleep(20)
    perpetrator_File = genai.get_file(perpetrator_File)
  if perpetrator_File.state.name != "ACTIVE":
      raise Exception(f"File {perpetrator_File.name} failed to process")
  print("File ready !")
  print()

def call_Gemini_To_Catgorize(input_Content):
  ''' 
  Creates the final prompt and call gemini to categorize.
  '''
    
  perpetrator_input = input_Content #Input message from perpetrator, could be text, image, audio, video

  prompt = f''' 
  Context : You are a classifier that classifies social media messages into harmful categories. This classification will help to protect receiver from harmful content online. The input message can be text, image, video or audio file.

  Categorize the content as one or more following categories, along with percentage for each category. Categories along with basic description are as follows:
  1. Verbal Abuse, Bullying and Mental Harassment - Includes Insults and name-calling, threatening language, Racist or sexist remarks, Cyberbullying, etc.
  2. Stalking and Doxing - Includes Tracking someone's online activity, Sharing someone's personal information, Creating fake profiles to harass someone, Harassing someone's friends and family, etc.
  3. Sexual Harassment - Sharing sexually explicit photos or videos or audio without the consent of the person involved, sharing private messages or conversations that contain intimate details, Threatening to share intimate images publicly if someone doesn't comply with demands, Facial expressions with sexually suggestive indications, etc.
  4. Hate Speech and Discrimination - Promoting hatred and discrimination against individuals or groups based on race, religion, gender, sexual orientation, or other protected characteristics, Using derogatory language and offensive imagery, Inciting violence or harassment against specific groups, etc.
  5. Online grooming - Adults using social media to contact minors with the intent of engaging in sexual activity, Pretending to be someone else to gain the trust of a child, Sending sexually explicit messages or images to minor.
  6. Instigating violence and self-harm - Messages like "you should kill yourself", "you don't deserve to live" that affect psychologically.

  Input Content/Message to be analyzed - {perpetrator_input}
  Output Format - Output should show category names along with percentage and rationale in dictionary format for easy extraction. Represent the output as list of dictionary. If the input content does not fit into any of above category, just give category as “Safe message” with 100% in output.
  Dictionary Keys - CategoryName, Percentage, Rationale
  '''
  # Make the LLM request -
  response = gemini_model.generate_content([prompt, input_Content], request_options={"timeout": 6000}, safety_settings=safety_settings_Gemini)
  # print(response.text)
  return response.text


def receiveMessageforGemini(inputContent=None, content_Type= None, file_path= None):
    ##Call gemini model to categorize input content
    if content_Type== 'text':
        geminiResponse = call_Gemini_To_Catgorize(inputContent)
    else:
        # print(file_path)
        perpetrator_Message = genai.upload_file(file_path)
        wait_for_files_active(perpetrator_Message) # Some files have a processing delay. Wait for them to be ready.
        geminiResponse = call_Gemini_To_Catgorize(perpetrator_Message)

    # print(geminiResponse)
    msg = geminiResponse.replace('json','').replace("```", '').strip() # Cleaning response
    catList = ast.literal_eval(msg)

    firstCategory = catList[0]['CategoryName']
    if firstCategory == "Safe message":
        return "", "Safe"
    else:
        inpMessage_CategoryList= []
        for cat in catList:
            inpMessage_CategoryList.append(f"{cat['CategoryName']}- {cat['Percentage']}%")
        return str(inpMessage_CategoryList), "malicious"
    
    return '', ''


