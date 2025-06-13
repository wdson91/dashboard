
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

import uuid
import os


SUPABASE_URL= os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
BUCKET_NAME = os.getenv("BUCKET_NAME")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)



def upload_image_to_supabase(file, filename=None):
    if not filename:
        filename = str(uuid.uuid4()) + "." + file.name.split('.')[-1]

    file_path = f"{filename}"

    file.seek(0)  # reposiciona o ponteiro para o início
    file_bytes = file.read()  # lê corretamente
    res = supabase.storage.from_(BUCKET_NAME).upload(file_path, file_bytes, {"content-type": file.content_type})
   
    
    if res.path is not None:
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)
        return public_url
    else:
        raise Exception(f"Erro ao fazer upload: {res.content}")
