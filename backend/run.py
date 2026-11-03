import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ.get("AIOS_PORT", "8765")),
        log_level="warning",
        access_log=False,
    )
