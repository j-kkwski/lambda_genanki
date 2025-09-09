import json
import boto3
import genanki
import random
import tempfile
import os
from botocore.config import Config

# Environment variables
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'YOUR_BUCKET_NAME')
REGION = os.environ.get('AWS_REGION', 'eu-north-1')

# Configure S3 client with v4 signing
s3 = boto3.client(
    's3',
    region_name=REGION,
    config=Config(signature_version='s3v4')
)

def lambda_handler(event, context):
    try:
        # Handle input body (can be str or dict)
        raw_body = event.get('body')
        if isinstance(raw_body, str):
            body = json.loads(raw_body)
        else:
            body = raw_body

        deck_name = body.get('deck_name', 'AI Flashcards')
        cards = body['cards']  # list of {"question": "...", "answer": "..."}

        # Create genanki model
        model_id = random.randint(1, 1 << 30)
        deck_id = random.randint(1, 1 << 30)
        model = genanki.Model(
            model_id,
            'AI Flashcard Model',
            fields=[{'name': 'Question'}, {'name': 'Answer'}],
            templates=[{
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
            }]
        )

        # Create deck
        deck = genanki.Deck(deck_id, deck_name)

        # Add notes
        for card in cards:
            note = genanki.Note(
                model=model,
                fields=[card['question'], card['answer']]
            )
            deck.add_note(note)

        # Save deck to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".apkg") as tmp:
            genanki.Package(deck).write_to_file(tmp.name)
            tmp_path = tmp.name

        # Define S3 key (safe: replace spaces with underscores)
        key = f"{deck_name.replace(' ', '_')}_{deck_id}.apkg"

        # Debug log
        print(f"DEBUG: Uploading to bucket={BUCKET_NAME}, key={key}")

        # Upload to S3
        s3.upload_file(tmp_path, BUCKET_NAME, key)

        # Generate presigned URL (valid 1 hour)
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': key},
            ExpiresIn=3600
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'download_url': url})
        }

    except Exception as e:
        print("ERROR:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }