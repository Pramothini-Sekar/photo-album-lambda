import boto3
import json
from botocore.vendored import requests
import logging

search_url = 'https://search-photos-jfgdev43lzfkaaimzmahecnipy.us-east-1.es.amazonaws.com/photos/_search'
s3_base_url = 'https://photo-album-storage.s3.amazonaws.com'
bot_id = 'CZAQDRKUTK'
bot_alias_id = 'TSTALIASID'
headers = {'Content-Type': 'application/json'}

def extract_search_string(event):
    print(event)
    if 'q' in event['queryStringParameters']:
        search_string = str(event["queryStringParameters"]['q'])
    else:
        search_string = 'ERROR: You have used incorrect query param. Please use /search?'
    
    return search_string

def get_lex_bot_response(search_string):
    lex_client = boto3.client('lexv2-runtime')
    lex_response = lex_client.recognize_text(botId = bot_id, 
                                            botAliasId = bot_alias_id, 
                                            sessionId="lex_session",
                                            localeId='en_US', text = search_string)
    sess_end_response = lex_client.delete_session(botId = bot_id, 
                                            botAliasId = bot_alias_id, 
                                            sessionId="lex_session",
                                            localeId='en_US')
    
    return lex_response

def extract_labels(lex_response):
    print()
    try:
        if lex_response['interpretations'][0]['intent']['slots'] != None:
            response_slots = lex_response['interpretations'][0]['intent']['slots']
    except:
        return None

    labels = list()
    for slot in response_slots:
        if response_slots[slot] != None:
            labels.append(response_slots[slot]['value']['originalValue'].capitalize())

    return labels

def get_image_responses(labels):
    image_responses = list()
    
    for label in labels:
        search_params = {
            "from": 0,
            "size": 12,
            "query": {
                "function_score": {
                    "query": {
                        "match": {
                            "labels": label
                        }
                    },
                    "random_score": {}
                }
            }
        }
        print("Search URL:", search_url)
        print("Search Params: ",search_params)

        es_response = requests.get(search_url, data = json.dumps(search_params), 
                                    headers = headers, auth=('photos_es', 'Ccbd@123'))
        print("es_response: ", es_response )
        im_response = json.loads(es_response.text)
        image_responses.append(im_response)

    return image_responses

def get_output_images(image_responses):
    output_images_data = set()
    print(output_images_data)
    for response in image_responses:
        if 'hits' in response:
            for hit in response['hits']['hits']:
                key = hit['_id']
                output_images_data.add(key)

    return list(output_images_data)

def lambda_handler(event, context):
    print(context)
    #print(event)
    search_string = extract_search_string(event)
    print(search_string)
    lex_response = get_lex_bot_response(search_string)
    labels = extract_labels(lex_response)
    print(labels)
    if labels is None:
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET'
            },
            'body': json.dumps({
                'search_string': search_string,
                's3_base_url': s3_base_url,
                'images': []
            })
        }
    
    image_responses = get_image_responses(labels)
    result = get_output_images(image_responses)

    return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET'
            },
            'body': json.dumps({
                'search_string': search_string,
                's3_base_url': s3_base_url,
                'images': result
            })
        }
