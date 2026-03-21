import os
from dotenv import load_dotenv
import uvicorn
load_dotenv()
if __name__ == '__main__':
    uvicorn.run('admin_web.app:app', host=os.getenv('WEB_ADMIN_HOST', '0.0.0.0'), port=int(os.getenv('WEB_ADMIN_PORT', '8000')), reload=False)
