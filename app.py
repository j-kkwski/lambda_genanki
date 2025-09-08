import json
import boto3
import genanki
import random
import tempfile
import os

# Replace with your S3 bucket name
BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'YOUR_BUCKET_NAME')

s3 = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # Parse JSON input
        body = json.loads(event['body'])
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

        # Upload to S3
        key = f"{deck_name.replace(' ', '_')}_{deck_id}.apkg"
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
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }