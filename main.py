import uvicorn
import os

def is_development():
    return os.getenv("ENVIRONMENT", "development") != "production"

port = int(os.getenv("PORT", 5000))  


if __name__ == "__main__":
    try:
        uvicorn.run(
            "app:app",                     
            host="0.0.0.0",                
            port=port,                    
            reload=is_development(),      
            workers=1                     
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
